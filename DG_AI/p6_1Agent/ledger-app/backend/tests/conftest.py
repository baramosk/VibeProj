"""공통 테스트 fixture.

- 각 테스트는 임시 SQLite 파일 DB를 새로 만듭니다.
- 시계는 FakeClock으로 주입해 잠금 해제, 세션 만료를 시간 이동으로 검증합니다.
- 쿠키 Secure 속성은 HTTP 테스트 클라이언트에서 전송되도록 테스트에서만 끕니다 (운영 기본값은 true).
"""

from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.config import Settings
from app.db.base import Base
from app.db.session import make_engine
from app.main import create_app


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now += timedelta(**kwargs)

    def set(self, now: datetime) -> None:
        self._now = now


# 2026-11-06 03:00 UTC = 2026-11-06 12:00 KST
START_UTC = datetime(2026, 11, 6, 3, 0)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START_UTC)


@pytest.fixture
def settings(tmp_path) -> Settings:
    db_path = (tmp_path / "test.db").as_posix()
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{db_path}",
        session_cookie_secure=False,
        session_ttl_days=14,
        login_max_failures=5,
        login_failure_window_minutes=10,
        login_lock_minutes=15,
        budget_alert_thresholds=[80, 100],
        cors_origins=["http://localhost:5173"],
        hsts_enabled=False,
        docs_enabled=False,
        # 속도 제한은 전용 테스트에서만 켭니다 (NFR-07). 일반 테스트는 많은 요청을 보냅니다.
        rate_limit_enabled=False,
        session_cleanup_interval_seconds=86_400,
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    db_engine = make_engine(settings.database_url)
    Base.metadata.create_all(db_engine)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def app(settings: Settings, clock: FakeClock, engine: Engine) -> FastAPI:
    return create_app(settings, clock=clock, engine=engine)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def make_client(app: FastAPI):
    """사용자마다 별도 쿠키 저장소를 가진 클라이언트를 만듭니다 (다중 사용자 테스트용)."""

    def _make() -> TestClient:
        return TestClient(app)

    return _make
