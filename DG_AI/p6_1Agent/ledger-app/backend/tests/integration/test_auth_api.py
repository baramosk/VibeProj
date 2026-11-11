"""인증 API 통합 테스트 (FR-01~FR-04, NFR-01~03, NFR-05, NFR-08, NFR-25)."""

import logging
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import LOGIN_FAILED_MESSAGE
from app.main import create_app
from app.models import AuthSession, Budget, Category, Notification, Transaction, User
from tests.conftest import FakeClock
from tests.helpers import PASSWORD, category_id, create_budget, create_transaction, csrf, error_code, signup

SESSION_COOKIE = "ledger_session"


def _login(client: TestClient, email: str = "user@example.com", password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# FR-01 회원가입
def test_FR01_signup_creates_user_logs_in_and_returns_csrf(client: TestClient):
    response = client.post(
        "/api/auth/signup",
        json={"email": "New@Example.com", "password": "abcd1234", "nickname": "닉네임"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["nickname"] == "닉네임"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert body["csrf_token"]
    assert f"{SESSION_COOKIE}=" in response.headers["set-cookie"]


def test_FR01_signup_duplicate_email_is_case_insensitive_conflict(client: TestClient):
    signup(client, email="dup@example.com")

    response = client.post(
        "/api/auth/signup",
        json={"email": "DUP@example.com", "password": "abcd1234", "nickname": "다른"},
    )

    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"
    assert "email" in response.json()["error"]["details"]


def test_FR01_signup_weak_password_returns_field_error(client: TestClient):
    response = client.post(
        "/api/auth/signup",
        json={"email": "weak@example.com", "password": "abcdefgh", "nickname": "닉"},
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "password" in error["details"]
    assert "abcdefgh" not in response.text  # 입력한 비밀번호를 응답에 되돌려 보내지 않습니다


def test_FR01_signup_invalid_email_returns_field_error(client: TestClient):
    response = client.post(
        "/api/auth/signup",
        json={"email": "not-an-email", "password": "abcd1234", "nickname": "닉"},
    )

    assert response.status_code == 400
    assert "email" in response.json()["error"]["details"]


def test_NFR02_session_cookie_is_httponly_samesite_lax_and_secure_in_production(
    settings, clock: FakeClock, engine
):
    secure_app = create_app(
        settings.model_copy(update={"session_cookie_secure": True}), clock=clock, engine=engine
    )
    response = TestClient(secure_app).post(
        "/api/auth/signup",
        json={"email": "cookie@example.com", "password": "abcd1234", "nickname": "닉"},
    )

    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "secure" in cookie_header
    assert "samesite=lax" in cookie_header
    assert "path=/" in cookie_header


def test_NFR08_responses_carry_security_headers(client: TestClient):
    response = client.get("/api/auth/me")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in response.headers


def test_NFR08_hsts_header_is_sent_only_when_enabled(settings, clock: FakeClock, engine):
    hsts_app = create_app(settings.model_copy(update={"hsts_enabled": True}), clock=clock, engine=engine)
    response = TestClient(hsts_app).get("/api/auth/me")

    assert "max-age=" in response.headers["Strict-Transport-Security"]


# FR-02 로그인
def test_FR02_login_success_returns_user_and_csrf_matching_me(client: TestClient, make_client):
    token = signup(client)
    other = make_client()

    response = _login(other)

    assert response.status_code == 200
    assert response.json()["csrf_token"] != token  # 로그인마다 새 세션과 CSRF 토큰
    me = other.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["csrf_token"] == response.json()["csrf_token"]


def test_FR02_wrong_password_and_unknown_email_return_same_generic_message(client: TestClient, make_client):
    signup(client)
    other = make_client()

    wrong_password = _login(other, password="wrong1234")
    unknown_email = _login(other, email="nobody@example.com")

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["error"]["message"] == LOGIN_FAILED_MESSAGE
    assert unknown_email.json()["error"]["message"] == LOGIN_FAILED_MESSAGE
    assert wrong_password.json() == unknown_email.json()


def test_FR02_five_failures_lock_account_even_for_correct_password_until_15_minutes_pass(
    client: TestClient, make_client, clock: FakeClock
):
    signup(client)
    attacker = make_client()

    for _ in range(4):
        assert _login(attacker, password="wrong1234").status_code == 401

    fifth = _login(attacker, password="wrong1234")
    assert fifth.status_code == 423
    assert error_code(fifth) == "ACCOUNT_LOCKED"
    assert fifth.json()["error"]["details"]["retry_after_seconds"] == 15 * 60

    # 잠금 중에는 올바른 비밀번호도 거부합니다
    assert _login(attacker).status_code == 423

    clock.advance(minutes=15)
    assert _login(attacker).status_code == 200


def test_FR02_failures_outside_ten_minute_window_do_not_lock(
    client: TestClient, make_client, clock: FakeClock
):
    signup(client)
    attacker = make_client()

    for _ in range(4):
        assert _login(attacker, password="wrong1234").status_code == 401
    clock.advance(minutes=11)
    assert _login(attacker, password="wrong1234").status_code == 401  # 새 창의 첫 실패
    assert _login(attacker).status_code == 200


def test_FR02_successful_login_resets_failure_count(client: TestClient, make_client):
    signup(client)
    user_client = make_client()

    for _ in range(4):
        _login(user_client, password="wrong1234")
    assert _login(user_client).status_code == 200
    for _ in range(4):
        assert _login(user_client, password="wrong1234").status_code == 401


# FR-03 로그아웃
def test_FR03_logout_invalidates_server_session_and_clears_cookie(client: TestClient):
    token = signup(client)
    old_cookie = client.cookies.get(SESSION_COOKIE)

    response = client.post("/api/auth/logout", headers=csrf(token))

    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    # 이전 쿠키 값을 다시 보내도 세션이 무효여야 합니다 (NFR-03 즉시 무효화)
    client.cookies.set(SESSION_COOKIE, old_cookie)
    assert client.get("/api/auth/me").status_code == 401


def test_FR03_protected_endpoints_require_login(make_client):
    anonymous = make_client()

    assert anonymous.get("/api/categories").status_code == 401
    assert anonymous.get("/api/auth/me").status_code == 401


# NFR-03 세션 유효 기간
def test_NFR03_session_expires_after_fourteen_days_without_use_and_slides_on_use(
    client: TestClient, clock: FakeClock
):
    signup(client)

    clock.advance(days=13)
    assert client.get("/api/auth/me").status_code == 200  # 사용하면 14일이 다시 시작
    clock.advance(days=13)
    assert client.get("/api/auth/me").status_code == 200

    clock.advance(days=14, seconds=1)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert error_code(response) == "UNAUTHORIZED"


def test_NFR03_cookie_lifetime_is_refreshed_when_session_is_used(client: TestClient, clock: FakeClock):
    signup(client)

    clock.advance(days=13)
    response = client.get("/api/auth/me")

    assert "max-age=1209600" in response.headers["set-cookie"].lower()  # 14일 (초 단위)


# FR-04 회원 탈퇴
def test_FR04_account_deletion_requires_password_then_removes_every_row(client: TestClient, engine):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_transaction(client, token, category=food, amount=60_000)
    create_budget(client, token, amount=50_000, category=food)  # 알림 1건이 생깁니다 (80% 초과)

    wrong = client.request("DELETE", "/api/auth/account", json={"password": "wrong1234"}, headers=csrf(token))
    assert wrong.status_code == 400
    assert "password" in wrong.json()["error"]["details"]

    response = client.request("DELETE", "/api/auth/account", json={"password": PASSWORD}, headers=csrf(token))
    assert response.status_code == 204
    assert SESSION_COOKIE not in client.cookies

    with Session(engine) as db:
        for model in (User, Category, Transaction, Budget, Notification, AuthSession):
            assert db.scalar(select(func.count()).select_from(model)) == 0, model.__tablename__

    # 삭제 후 같은 이메일로 재가입 가능 (FR-04)
    signup(client)


def test_FR04_account_deletion_requires_csrf_token(client: TestClient):
    signup(client)

    response = client.request("DELETE", "/api/auth/account", json={"password": PASSWORD})

    assert response.status_code == 403


# NFR-05 CSRF
def test_NFR05_state_changing_request_without_csrf_header_is_forbidden(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    no_header = client.post("/api/categories", json={"name": "새", "type": "EXPENSE"})
    assert no_header.status_code == 403
    assert error_code(no_header) == "FORBIDDEN"

    wrong_token = client.patch(
        f"/api/categories/{food}", json={"name": "변경"}, headers=csrf("not-the-token")
    )
    assert wrong_token.status_code == 403

    no_header_delete = client.delete(f"/api/categories/{food}?replacement_id={food}")
    assert no_header_delete.status_code == 403


def test_NFR05_csrf_check_runs_before_body_validation(client: TestClient):
    signup(client)

    response = client.post("/api/categories", json={"name": ""})

    assert response.status_code == 403


def test_NFR05_login_rejects_non_json_bodies_to_block_cross_site_form_posts(client: TestClient):
    signup(client)

    response = client.post(
        "/api/auth/login",
        content=f'{{"email": "user@example.com", "password": "{PASSWORD}"}}',
        headers={"content-type": "text/plain"},
    )

    assert response.status_code == 403


# NFR-01, NFR-25: 로그에 비밀번호와 세션 값이 남지 않음
def test_NFR01_passwords_and_session_tokens_never_appear_in_logs(client: TestClient, caplog):
    caplog.set_level(logging.DEBUG)
    secret = "Sup3rSecret9"

    client.post("/api/auth/signup", json={"email": "log@example.com", "password": secret, "nickname": "닉"})
    token = client.cookies.get(SESSION_COOKIE)
    client.post("/api/auth/login", json={"email": "log@example.com", "password": "Wrong0000"})
    client.get("/api/auth/me")

    assert secret not in caplog.text
    assert "Wrong0000" not in caplog.text
    assert token not in caplog.text


def test_FR01_signup_timestamps_are_utc_iso_strings(client: TestClient, clock: FakeClock):
    clock.set(datetime(2026, 11, 6, 3, 0))
    response = client.post(
        "/api/auth/signup",
        json={"email": "time@example.com", "password": "abcd1234", "nickname": "닉"},
    )

    assert response.json()["user"]["created_at"] == "2026-11-06T03:00:00Z"
