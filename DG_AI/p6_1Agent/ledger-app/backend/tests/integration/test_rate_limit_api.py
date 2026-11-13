"""속도 제한 API 테스트 (NFR-07, Q-E): 로그인과 가입, 거래 쓰기에 걸리는지 확인합니다."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.config import Settings
from app.core.rate_limit import RateLimiter
from app.main import create_app
from tests.conftest import FakeClock
from tests.helpers import PASSWORD, category_id, create_transaction, csrf, signup


def _limited_app(settings: Settings, clock: FakeClock, engine: Engine) -> FastAPI:
    limited = settings.model_copy(
        update={
            "rate_limit_enabled": True,
            "rate_limit_auth_per_window": 2,
            "rate_limit_write_per_window": 2,
            "rate_limit_window_seconds": 60,
        }
    )
    return create_app(limited, clock=clock, engine=engine)


def test_login_is_blocked_after_limit_with_retry_after(settings, clock, engine):
    client = TestClient(_limited_app(settings, clock, engine))
    body = {"email": "nobody@example.com", "password": PASSWORD}

    assert client.post("/api/auth/login", json=body).status_code == 401
    assert client.post("/api/auth/login", json=body).status_code == 401
    blocked = client.post("/api/auth/login", json=body)

    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.json()["error"]["details"]["retry_after_seconds"] >= 1


def test_transaction_writes_are_limited_but_reads_are_not(settings, clock, engine):
    client = TestClient(_limited_app(settings, clock, engine))
    token = signup(client)
    food = category_id(client, token, "식비")

    create_transaction(client, token, category=food)
    create_transaction(client, token, category=food)
    response = client.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 1000, "category_id": food, "occurred_on": "2026-11-06"},
        headers=csrf(token),
    )

    assert response.status_code == 429
    assert client.get("/api/transactions").status_code == 200


def test_limit_recovers_after_window(settings, clock, engine):
    app = _limited_app(settings, clock, engine)
    monotonic = {"t": 1_000.0}
    app.state.rate_limiter = RateLimiter(now=lambda: monotonic["t"])
    client = TestClient(app)
    body = {"email": "nobody@example.com", "password": PASSWORD}

    client.post("/api/auth/login", json=body)
    client.post("/api/auth/login", json=body)
    assert client.post("/api/auth/login", json=body).status_code == 429

    monotonic["t"] += 61
    assert client.post("/api/auth/login", json=body).status_code == 401
