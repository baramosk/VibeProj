"""사용자 간 데이터 격리 테스트 (NFR-04, SC-05). 타인의 리소스는 모두 404입니다."""

from fastapi.testclient import TestClient

from tests.helpers import category_id, create_budget, create_transaction, csrf, signup


def _owner_data(client: TestClient) -> dict:
    """소유자(A)의 리소스를 만들고 ID를 돌려줍니다. 예산 초과 알림까지 만듭니다."""
    token = signup(client, email="owner@example.com")
    food = category_id(client, token, "식비")
    budget = create_budget(client, token, amount=10_000, category=food)
    transaction = create_transaction(client, token, category=food, amount=10_000)["transaction"]
    notification = client.get("/api/notifications").json()["items"][0]
    custom = client.post(
        "/api/categories", json={"name": "A전용", "type": "EXPENSE"}, headers=csrf(token)
    ).json()
    return {
        "token": token,
        "food": food,
        "budget": budget["id"],
        "transaction": transaction["id"],
        "notification": notification["id"],
        "custom": custom["id"],
    }


def test_SC05_other_user_cannot_read_or_change_transactions_budgets_notifications(
    client: TestClient, make_client
):
    owner = _owner_data(client)
    attacker = make_client()
    intruder_token = signup(attacker, email="intruder@example.com")

    assert (
        attacker.patch(
            f"/api/transactions/{owner['transaction']}", json={"amount": 1}, headers=csrf(intruder_token)
        ).status_code
        == 404
    )
    assert (
        attacker.delete(f"/api/transactions/{owner['transaction']}", headers=csrf(intruder_token)).status_code
        == 404
    )
    assert (
        attacker.put(
            f"/api/budgets/{owner['budget']}", json={"amount": 1}, headers=csrf(intruder_token)
        ).status_code
        == 404
    )
    assert attacker.delete(f"/api/budgets/{owner['budget']}", headers=csrf(intruder_token)).status_code == 404
    assert (
        attacker.post(
            f"/api/notifications/{owner['notification']}/read", headers=csrf(intruder_token)
        ).status_code
        == 404
    )


def test_SC05_other_user_cannot_modify_or_delete_categories(client: TestClient, make_client):
    owner = _owner_data(client)
    attacker = make_client()
    intruder_token = signup(attacker, email="intruder@example.com")

    assert (
        attacker.patch(
            f"/api/categories/{owner['custom']}", json={"name": "해킹"}, headers=csrf(intruder_token)
        ).status_code
        == 404
    )
    assert (
        attacker.delete(
            f"/api/categories/{owner['custom']}?replacement_id={owner['food']}",
            headers=csrf(intruder_token),
        ).status_code
        == 404
    )


def test_SC05_other_user_cannot_use_owner_category_as_replacement(client: TestClient, make_client):
    owner = _owner_data(client)
    attacker = make_client()
    intruder_token = signup(attacker, email="intruder@example.com")
    own_food = category_id(attacker, intruder_token, "식비")

    response = attacker.delete(
        f"/api/categories/{own_food}?replacement_id={owner['food']}", headers=csrf(intruder_token)
    )

    assert response.status_code == 404
    # 소유자의 거래와 카테고리가 그대로여야 합니다
    owner_items = client.get("/api/transactions").json()
    assert owner_items["total"] == 1


def test_SC05_other_user_cannot_create_records_with_owner_category_or_budget(client: TestClient, make_client):
    owner = _owner_data(client)
    attacker = make_client()
    intruder_token = signup(attacker, email="intruder@example.com")

    tx = attacker.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 1000, "category_id": owner["food"]},
        headers=csrf(intruder_token),
    )
    budget = attacker.post(
        "/api/budgets",
        json={"year_month": "2026-11", "amount": 1000, "category_id": owner["food"]},
        headers=csrf(intruder_token),
    )

    assert tx.status_code == 404
    assert budget.status_code == 404


def test_SC05_lists_contain_only_the_requesting_users_rows(client: TestClient, make_client):
    owner = _owner_data(client)
    attacker = make_client()
    intruder_token = signup(attacker, email="intruder@example.com")
    intruder_food = category_id(attacker, intruder_token, "식비")
    create_transaction(attacker, intruder_token, category=intruder_food, amount=500)

    assert attacker.get("/api/transactions").json()["total"] == 1
    assert attacker.get("/api/notifications").json() == {"items": [], "unread_count": 0}
    assert attacker.get("/api/budgets?year_month=2026-11").json() == []
    assert client.get("/api/transactions").json()["total"] == 1
    assert client.get("/api/notifications").json()["unread_count"] == 2  # 80%, 100% 두 건
    assert owner["transaction"] != intruder_food


def test_SC05_owner_data_is_untouched_by_failed_intrusion_attempts(client: TestClient, make_client):
    owner = _owner_data(client)
    attacker = make_client()
    intruder_token = signup(attacker, email="intruder@example.com")

    attacker.delete(f"/api/transactions/{owner['transaction']}", headers=csrf(intruder_token))
    attacker.patch(f"/api/categories/{owner['food']}", json={"name": "변조"}, headers=csrf(intruder_token))

    names = {c["name"] for c in client.get("/api/categories?type=EXPENSE").json()}
    assert "식비" in names and "변조" not in names
    assert client.get("/api/transactions").json()["total"] == 1
