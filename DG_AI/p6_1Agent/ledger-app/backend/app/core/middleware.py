"""보안 응답 헤더 (NFR-08).

API 응답은 HTML을 렌더링하지 않으므로 CSP는 가장 엄격한 값을 씁니다.
민감 데이터를 담으므로 캐시를 금지합니다. HSTS는 HTTPS 배포 설정에서만 켭니다.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response


def register_security_headers(app: FastAPI, *, hsts_enabled: bool) -> None:
    @app.middleware("http")
    async def _security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "no-referrer"
        headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        headers["Cache-Control"] = "no-store"
        if hsts_enabled:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
