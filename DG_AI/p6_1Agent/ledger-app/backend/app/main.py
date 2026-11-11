"""FastAPI 앱 팩토리.

- create_app은 설정, 시계, 엔진을 인자로 받아 테스트에서 교체할 수 있게 합니다.
- 운영 실행: `uvicorn app.main:app` (환경 변수는 LEDGER_ 접두사, 예: .env.example 참고)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from app.api.routes import auth, budgets, categories, notifications, reports, transactions
from app.constants import CSRF_HEADER_NAME
from app.core.clock import Clock, SystemClock
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import register_security_headers
from app.db.session import make_engine, make_session_factory


def create_app(
    settings: Settings | None = None,
    *,
    clock: Clock | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = engine or make_engine(settings.database_url)

    app = FastAPI(
        title="가계부 API",
        version="0.1.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.state.clock = clock or SystemClock()
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)

    register_exception_handlers(app)
    register_security_headers(app, hsts_enabled=settings.hsts_enabled)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", CSRF_HEADER_NAME],
    )

    for router in (
        auth.router,
        categories.router,
        transactions.router,
        budgets.router,
        reports.router,
        notifications.router,
    ):
        app.include_router(router)
    return app


app = create_app()
