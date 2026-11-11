"""도메인 오류 타입.

서비스 계층은 이 예외만 던지고, HTTP 응답 형식(api-contract 오류 형식)으로의 변환은
exception_handlers.py가 담당합니다. 사용자에게 보여줄 메시지(message)와 필드별 상세(details)만
담으며, 거래 금액이나 메모, 비밀번호 같은 내용은 넣지 않습니다 (NFR-10, NFR-25).
"""

from typing import Any


class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class ValidationFailed(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class AccountLockedError(AppError):
    status_code = 423
    code = "ACCOUNT_LOCKED"
