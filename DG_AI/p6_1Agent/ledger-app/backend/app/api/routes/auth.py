from fastapi import APIRouter, Depends, Response

from app.api.cookies import clear_session_cookie, set_session_cookie
from app.api.deps import (
    AuthServiceDep,
    CsrfSessionDep,
    CsrfUserId,
    SessionDep,
    SettingsDep,
    rate_limit,
    require_json_body,
)
from app.schemas.auth import (
    AuthResponse,
    DeleteAccountRequest,
    LoginRequest,
    SignupRequest,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/signup",
    status_code=201,
    response_model=AuthResponse,
    dependencies=[Depends(require_json_body), Depends(rate_limit("auth"))],
)
def signup(
    body: SignupRequest,
    response: Response,
    auth: AuthServiceDep,
    settings: SettingsDep,
) -> AuthResponse:
    """FR-01: 가입과 동시에 로그인하고, 기본 카테고리를 만듭니다 (FR-06)."""
    issued = auth.signup(body.email, body.password, body.nickname)
    set_session_cookie(response, issued.raw_token, settings)
    return AuthResponse(user=UserOut.model_validate(issued.user), csrf_token=issued.csrf_token)


@router.post(
    "/login",
    response_model=AuthResponse,
    dependencies=[Depends(require_json_body), Depends(rate_limit("auth"))],
)
def login(
    body: LoginRequest,
    response: Response,
    auth: AuthServiceDep,
    settings: SettingsDep,
) -> AuthResponse:
    """FR-02: 실패 5회 시 잠금 (423)."""
    issued = auth.login(body.email, body.password)
    set_session_cookie(response, issued.raw_token, settings)
    return AuthResponse(user=UserOut.model_validate(issued.user), csrf_token=issued.csrf_token)


@router.post("/logout", status_code=204, response_class=Response)
def logout(session: CsrfSessionDep, auth: AuthServiceDep, settings: SettingsDep) -> Response:
    """FR-03: 서버 세션을 즉시 무효화하고 쿠키를 지웁니다 (NFR-03)."""
    auth.logout(session.token_hash)
    response = Response(status_code=204)
    clear_session_cookie(response, settings)
    return response


@router.get("/me", response_model=AuthResponse)
def me(session: SessionDep, auth: AuthServiceDep) -> AuthResponse:
    user = auth.get_user(session.user_id)
    return AuthResponse(user=UserOut.model_validate(user), csrf_token=session.csrf_token)


@router.delete("/account", status_code=204, response_class=Response)
def delete_account(
    body: DeleteAccountRequest,
    user_id: CsrfUserId,
    auth: AuthServiceDep,
    settings: SettingsDep,
) -> Response:
    """FR-04: 비밀번호 확인 후 계정과 모든 데이터를 삭제합니다."""
    auth.delete_account(user_id, body.password)
    response = Response(status_code=204)
    clear_session_cookie(response, settings)
    return response
