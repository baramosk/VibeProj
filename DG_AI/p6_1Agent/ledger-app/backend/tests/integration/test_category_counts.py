"""카테고리 거래 수 (Q-C): 목록과 수정 응답에 transaction_count가 들어가는지 확인합니다."""

from fastapi.testclient import TestClient

from tests.helpers import (
    category_id,
    create_category,
    create_transaction,
    csrf,
    list_categories,
    signup,
)


def _count_of(items: list[dict], name: str) -> int:
    return next(item["transaction_count"] for item in items if item["name"] == name)


def test_list_reports_transaction_count_per_category(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    category_id(client, token, "교통")
    create_transaction(client, token, category=food)
    create_transaction(client, token, category=food)

    items = list_categories(client, token, "EXPENSE")

    assert _count_of(items, "식비") == 2
    assert _count_of(items, "교통") == 0


def test_new_category_starts_at_zero(client: TestClient):
    token = signup(client)
    created = create_category(client, token, "여행")
    assert created["transaction_count"] == 0


def test_update_response_includes_current_count(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_transaction(client, token, category=food)

    response = client.patch(
        f"/api/categories/{food}", json={"name": "외식"}, headers=csrf(token)
    )

    assert response.status_code == 200
    assert response.json()["transaction_count"] == 1
