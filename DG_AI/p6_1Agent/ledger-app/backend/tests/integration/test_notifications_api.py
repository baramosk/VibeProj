"""알림 API 통합 테스트 (FR-22)."""

from fastapi.testclient import TestClient

from tests.helpers import category_id, create_budget, create_transaction, csrf, signup


def _make_two_alerts(client: TestClient, token: str) -> None:
    food = category_id(client, token, "식비")
    create_budget(client, token, amount=10_000, category=food)
    create_transaction(client, token, category=food, amount=8_000)  # 80% 알림
    create_transaction(client, token, category=food, amount=2_000)  # 100% 알림


def test_FR22_list_is_newest_first_with_unread_count(client: TestClient):
    token = signup(client)
    _make_two_alerts(client, token)

    body = client.get("/api/notifications").json()

    assert body["unread_count"] == 2
    thresholds = [n["threshold_percent"] for n in body["items"]]
    assert thresholds == [100, 80]  # 최신순
    first = body["items"][0]
    assert first["is_read"] is False
    assert first["year_month"] == "2026-11"
    assert first["budget_id"]
    assert "식비 예산" in first["message"]


def test_FR22_mark_one_as_read_updates_unread_count(client: TestClient):
    token = signup(client)
    _make_two_alerts(client, token)
    target = client.get("/api/notifications").json()["items"][0]

    response = client.post(f"/api/notifications/{target['id']}/read", headers=csrf(token))

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    body = client.get("/api/notifications").json()
    assert body["unread_count"] == 1


def test_FR22_unread_only_filter(client: TestClient):
    token = signup(client)
    _make_two_alerts(client, token)
    target = client.get("/api/notifications").json()["items"][0]
    client.post(f"/api/notifications/{target['id']}/read", headers=csrf(token))

    body = client.get("/api/notifications?unread_only=true").json()

    assert len(body["items"]) == 1
    assert body["items"][0]["threshold_percent"] == 80
    assert body["unread_count"] == 1


def test_FR22_mark_all_read_clears_unread_count(client: TestClient):
    token = signup(client)
    _make_two_alerts(client, token)

    response = client.post("/api/notifications/read-all", headers=csrf(token))

    assert response.status_code == 204
    assert client.get("/api/notifications").json()["unread_count"] == 0


def test_FR22_mark_read_of_unknown_notification_returns_404(client: TestClient):
    token = signup(client)

    response = client.post("/api/notifications/9999/read", headers=csrf(token))

    assert response.status_code == 404


def test_FR22_empty_list_when_no_alerts(client: TestClient):
    signup(client)

    assert client.get("/api/notifications").json() == {"items": [], "unread_count": 0}
