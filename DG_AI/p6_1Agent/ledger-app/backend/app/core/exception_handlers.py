"""모든 오류를 api-contract의 오류 형식 { error: { code, message, details } }으로 통일합니다.

- 도메인 오류(AppError): 상태 코드와 코드는 예외 클래스가 정합니다.
- 입력 검증 오류: 필드별 한국어 메시지를 details에 담습니다. 입력 값 자체는 응답에 되돌려 보내지 않습니다.
- 처리되지 않은 오류: 응답에는 일반 메시지만 보내고, 로그에는 예외 종류와 위치만 남깁니다.
  예외 메시지에는 SQL 파라미터(거래 금액, 메모 등)가 섞일 수 있어 메시지는 기록하지 않습니다 (NFR-10, NFR-25).
"""

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError

logger = logging.getLogger("ledger.api")

_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}

_ERROR_TYPE_MESSAGES = {
    "missing": "필수 항목입니다.",
    "int_type": "정수로 입력해 주세요.",
    "int_parsing": "정수로 입력해 주세요.",
    "string_type": "문자열로 입력해 주세요.",
    "bool_type": "true 또는 false로 입력해 주세요.",
    "date_type": "날짜 형식은 YYYY-MM-DD입니다.",
    "date_parsing": "날짜 형식은 YYYY-MM-DD입니다.",
    "date_from_datetime_parsing": "날짜 형식은 YYYY-MM-DD입니다.",
    "literal_error": "허용되지 않은 값입니다.",
    "json_invalid": "JSON 형식이 올바르지 않습니다.",
    "model_type": "요청 본문 형식이 올바르지 않습니다.",
}


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}


def _field_name(loc: tuple[Any, ...]) -> str:
    for part in loc:
        if isinstance(part, str) and part not in _LOCATION_PREFIXES:
            return part
    return "body"


def _field_message(error: dict[str, Any]) -> str:
    error_type = error.get("type", "")
    if error_type == "value_error":
        # 스키마 검증기의 ValueError 메시지를 그대로 씁니다 (Pydantic이 "Value error, " 접두사를 붙임)
        return str(error.get("msg", "")).removeprefix("Value error, ")
    if error_type in _ERROR_TYPE_MESSAGES:
        return _ERROR_TYPE_MESSAGES[error_type]
    ctx = error.get("ctx", {})
    if error_type in ("greater_than_equal", "greater_than"):
        return f"{ctx.get('ge', ctx.get('gt'))} 이상이어야 합니다."
    if error_type in ("less_than_equal", "less_than"):
        return f"{ctx.get('le', ctx.get('lt'))} 이하여야 합니다."
    if error_type == "string_too_long":
        return f"{ctx.get('max_length')}자 이하로 입력해 주세요."
    if error_type == "string_too_short":
        return f"{ctx.get('min_length')}자 이상 입력해 주세요."
    return "입력값이 올바르지 않습니다."


def _validation_details(errors: list[dict[str, Any]]) -> dict[str, str]:
    details: dict[str, str] = {}
    for error in errors:
        name = _field_name(tuple(error.get("loc", ())))
        details.setdefault(name, _field_message(error))
    return details


def _log_unhandled(request: Request, exc: Exception) -> None:
    # 예외 메시지(str(exc))는 SQL 파라미터 등 민감 값을 포함할 수 있어 기록하지 않습니다.
    frames = "".join(traceback.format_tb(exc.__traceback__)).strip()
    logger.error(
        "unhandled error: %s %s (%s)\n%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        frames,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_error_body(
                "VALIDATION_ERROR",
                "입력값을 확인해 주세요.",
                _validation_details(exc.errors()),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            400: "VALIDATION_ERROR",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
        }.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "요청을 처리할 수 없습니다."
        return JSONResponse(status_code=exc.status_code, content=_error_body(code, message))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        _log_unhandled(request, exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."),
        )
