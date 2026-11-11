"""API 통합 테스트용 헬퍼. 테스트 본문을 짧게 유지하기 위한 함수 모음입니다."""

from typing import Any

from fastapi.testclient import TestClient

from app.constants import CSRF_HEADER_NAME

PASSWORD = "abcd1234"


def signup(
    client: TestClient,
    email: str = "user@example.com",
    password: str = PASSWORD,
    nickname: str = "테스터",
) -> str:
    """가입하고 쿠키는 클라이언트에 남기며, CSRF 토큰을 돌려줍니다."""
    response = client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "nickname": nickname},
    )
    assert response.status_code == 201, response.text
    return response.json()["csrf_token"]


def csrf(token: str) -> dict[str, str]:
    return {CSRF_HEADER_NAME: token}


def list_categories(client: TestClient, token: str, category_type: str | None = None) -> list[dict]:
    params = {"type": category_type} if category_type else None
    response = client.get("/api/categories", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def category_id(client: TestClient, token: str, name: str, category_type: str = "EXPENSE") -> int:
    for item in list_categories(client, token, category_type):
        if item["name"] == name:
            return item["id"]
    raise AssertionError(f"기본 카테고리를 찾을 수 없습니다: {category_type} {name}")


def create_category(
    client: TestClient, token: str, name: str, category_type: str = "EXPENSE", color: str | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {"name": name, "type": category_type}
    if color is not None:
        body["color"] = color
    response = client.post("/api/categories", json=body, headers=csrf(token))
    assert response.status_code == 201, response.text
    return response.json()


def create_transaction(
    client: TestClient,
    token: str,
    *,
    category: int,
    amount: int = 10_000,
    transaction_type: str = "EXPENSE",
    occurred_on: str | None = "2026-11-06",
    memo: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": transaction_type,
        "amount": amount,
        "category_id": category,
        "occurred_on": occurred_on,
    }
    if memo is not None:
        body["memo"] = memo
    response = client.post("/api/transactions", json=body, headers=csrf(token))
    assert response.status_code == 201, response.text
    return response.json()


def create_budget(
    client: TestClient,
    token: str,
    *,
    year_month: str = "2026-11",
    amount: int,
    category: int | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"year_month": year_month, "amount": amount}
    if category is not None:
        body["category_id"] = category
    response = client.post("/api/budgets", json=body, headers=csrf(token))
    assert response.status_code == 201, response.text
    return response.json()


def error_code(response) -> str:
    return response.json()["error"]["code"]
