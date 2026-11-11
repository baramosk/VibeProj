"""세션 쿠키 설정 (NFR-02: HttpOnly, Secure, SameSite=Lax)."""

from fastapi import Response

from app.core.config import Settings

SECONDS_PER_DAY = 24 * 60 * 60


def set_session_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_days * SECONDS_PER_DAY,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
