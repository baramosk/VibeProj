"""비밀번호 해시, 세션 토큰, 로그인 잠금 정책 단위 테스트 (NFR-01, NFR-03, FR-02)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.core.config import Settings
from app.core.security import (
    generate_token,
    hash_password,
    hash_token,
    tokens_match,
    verify_password,
)
from app.services.login_guard import LoginGuard

T0 = datetime(2026, 11, 6, 3, 0)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite:///:memory:",
        login_max_failures=5,
        login_failure_window_minutes=10,
        login_lock_minutes=15,
    )


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        failed_login_count=0,
        failed_login_window_started_at=None,
        locked_until=None,
    )


def test_NFR01_password_is_hashed_with_argon2_and_verifiable():
    hashed = hash_password("abcd1234")
    assert hashed.startswith("$argon2id$")
    assert "abcd1234" not in hashed
    assert verify_password(hashed, "abcd1234") is True
    assert verify_password(hashed, "wrong-pass1") is False


def test_NFR03_session_token_is_stored_only_as_hash():
    raw = generate_token()
    stored = hash_token(raw)
    assert stored != raw
    assert len(stored) == 64
    assert stored == hash_token(raw)


def test_NFR05_csrf_token_comparison_is_exact():
    token = generate_token()
    assert tokens_match(token, token) is True
    assert tokens_match(token, token + "x") is False
    assert tokens_match(token, "") is False


def test_FR02_five_failures_within_window_lock_the_account():
    guard = LoginGuard(_settings())
    user = _user()
    for minute in range(4):
        assert guard.record_failure(user, T0 + timedelta(minutes=minute)) is False
    assert guard.record_failure(user, T0 + timedelta(minutes=4)) is True
    # 다섯 번째 실패는 4분 시점이므로 잠금 해제는 19분 시점입니다. 5분 시점 남은 시간은 14분.
    assert guard.remaining_lock_seconds(user, T0 + timedelta(minutes=5)) == 14 * 60


def test_FR02_failures_spread_beyond_window_do_not_lock():
    guard = LoginGuard(_settings())
    user = _user()
    for index in range(10):
        # 실패 사이 간격이 10분 이상이면 창이 새로 시작되어 잠기지 않습니다.
        assert guard.record_failure(user, T0 + timedelta(minutes=11 * index)) is False
    assert guard.remaining_lock_seconds(user, T0 + timedelta(minutes=110)) is None


def test_FR02_lock_expires_after_fifteen_minutes():
    guard = LoginGuard(_settings())
    user = _user()
    for _ in range(5):
        guard.record_failure(user, T0)
    assert guard.remaining_lock_seconds(user, T0 + timedelta(minutes=14, seconds=59)) == 1
    assert guard.remaining_lock_seconds(user, T0 + timedelta(minutes=15)) is None


def test_FR02_reset_clears_failure_state():
    guard = LoginGuard(_settings())
    user = _user()
    guard.record_failure(user, T0)
    guard.reset(user)
    assert user.failed_login_count == 0
    assert user.failed_login_window_started_at is None
    assert user.locked_until is None
