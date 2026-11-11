"""FastAPI 의존성 주입. 서비스 생성과 인증, CSRF 검사를 여기서 연결합니다.

- 인증: 쿠키의 세션 토큰을 AuthService.authenticate로 검증 (없거나 만료되면 401).
- CSRF (NFR-05): 상태 변경 요청은 X-CSRF-Token 헤더가 세션의 CSRF 토큰과 같아야 합니다 (없거나 다르면 403).
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.cookies import set_session_cookie
from app.constants import CSRF_HEADER_NAME
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import ForbiddenError, ValidationFailed
from app.core.security import tokens_match
from app.lib.dates import parse_year_month
from app.services.auth_service import AuthService, SessionContext
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.services.transaction_service import TransactionService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_db(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(get_settings)]
ClockDep = Annotated[Clock, Depends(get_clock)]
DbDep = Annotated[Session, Depends(get_db)]


def get_auth_service(db: DbDep, clock: ClockDep, settings: SettingsDep) -> AuthService:
    return AuthService(db, clock, settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_session_context(request: Request, response: Response, auth: AuthServiceDep) -> SessionContext:
    """세션을 검증하고, 서버에서 연장된 만료 기간에 맞춰 쿠키 Max-Age도 갱신합니다.

    서버 세션만 연장하고 쿠키를 그대로 두면 로그인 후 14일이 지나 브라우저가 쿠키를 버리므로 함께 갱신합니다.
    """
    settings = request.app.state.settings
    raw_token = request.cookies.get(settings.session_cookie_name)
    session = auth.authenticate(raw_token)
    set_session_cookie(response, raw_token, settings)
    return session


SessionDep = Annotated[SessionContext, Depends(get_session_context)]


def get_current_user_id(session: SessionDep) -> int:
    return session.user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]


def get_csrf_session(request: Request, session: SessionDep) -> SessionContext:
    provided = request.headers.get(CSRF_HEADER_NAME)
    if not provided or not tokens_match(session.csrf_token, provided):
        raise ForbiddenError("요청을 확인할 수 없습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
    return session


CsrfSessionDep = Annotated[SessionContext, Depends(get_csrf_session)]


def get_csrf_user_id(session: CsrfSessionDep) -> int:
    return session.user_id


CsrfUserId = Annotated[int, Depends(get_csrf_user_id)]


def require_json_body(request: Request) -> None:
    """로그인 전 요청은 CSRF 토큰이 없으므로, JSON 본문만 받아 교차 사이트 폼 전송을 막습니다."""
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        raise ForbiddenError("JSON 형식의 요청만 허용됩니다.")


def get_category_service(db: DbDep, clock: ClockDep) -> CategoryService:
    return CategoryService(db, clock)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


def get_budget_service(db: DbDep, clock: ClockDep, settings: SettingsDep) -> BudgetService:
    return BudgetService(db, clock, settings)


BudgetServiceDep = Annotated[BudgetService, Depends(get_budget_service)]


def get_transaction_service(
    db: DbDep, clock: ClockDep, budget_service: BudgetServiceDep
) -> TransactionService:
    return TransactionService(db, clock, budget_service)


TransactionServiceDep = Annotated[TransactionService, Depends(get_transaction_service)]


def get_report_service(db: DbDep, clock: ClockDep) -> ReportService:
    return ReportService(db, clock)


ReportServiceDep = Annotated[ReportService, Depends(get_report_service)]


def get_notification_service(db: DbDep) -> NotificationService:
    return NotificationService(db)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


def query_year_month(value: str) -> str:
    """쿼리 파라미터의 년월을 검증합니다. 형식이 틀리면 400."""
    try:
        return parse_year_month(value)
    except ValueError as exc:
        raise ValidationFailed(str(exc), {"year_month": str(exc)}) from exc
