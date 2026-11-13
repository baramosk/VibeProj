"""만료 세션 정리 테스트 (NFR-03, Q-F)."""

from fastapi.testclient import TestClient

from app.services.session_cleanup import purge_expired_sessions_once
from tests.conftest import FakeClock
from tests.helpers import signup


def test_purge_removes_only_expired_sessions(app, clock: FakeClock, settings, make_client):
    old_client: TestClient = make_client()
    signup(old_client, email="old@example.com")

    clock.advance(days=10)
    new_client: TestClient = make_client()
    signup(new_client, email="new@example.com")

    # 첫 세션은 가입 후 14일이 지나 만료되고, 두 번째 세션은 아직 유효합니다.
    clock.advance(days=5)
    removed = purge_expired_sessions_once(app.state.session_factory, clock, settings)

    assert removed == 1
    assert new_client.get("/api/auth/me").status_code == 200
    # 같은 쿠키를 다시 쓰면 세션은 이미 없어져 로그인 필요 상태입니다.
    assert old_client.get("/api/auth/me").status_code == 401


def test_purge_is_noop_when_nothing_expired(app, clock: FakeClock, settings, make_client):
    client = make_client()
    signup(client)
    clock.advance(days=1)

    assert purge_expired_sessions_once(app.state.session_factory, clock, settings) == 0
    assert client.get("/api/auth/me").status_code == 200


def test_authenticate_renews_expiry_so_active_session_survives(app, clock: FakeClock, settings, make_client):
    client = make_client()
    signup(client)
    for _ in range(3):
        clock.advance(days=10)
        assert client.get("/api/auth/me").status_code == 200

    # 마지막 사용 후 10일이 지났으므로 아직 만료되지 않아야 합니다.
    assert purge_expired_sessions_once(app.state.session_factory, clock, settings) == 0
    clock.advance(days=15)
    assert purge_expired_sessions_once(app.state.session_factory, clock, settings) == 1
