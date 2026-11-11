"""카테고리 API 통합 테스트 (FR-06~FR-09)."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.repositories.budget_repository import BudgetRepository
from tests.conftest import FakeClock
from tests.helpers import (
    category_id,
    create_budget,
    create_category,
    create_transaction,
    csrf,
    error_code,
    list_categories,
    signup,
)


# FR-06 기본 카테고리
def test_FR06_signup_creates_default_expense_and_income_categories(client: TestClient):
    token = signup(client)

    categories = list_categories(client, token)

    expense = sorted(c["name"] for c in categories if c["type"] == "EXPENSE")
    income = sorted(c["name"] for c in categories if c["type"] == "INCOME")
    assert expense == sorted(
        [
            "식비",
            "카페/간식",
            "교통",
            "주거/관리비",
            "통신",
            "쇼핑",
            "문화/여가",
            "의료/건강",
            "교육",
            "경조사",
            "기타 지출",
        ]
    )
    assert income == sorted(["급여", "부수입", "용돈", "기타 수입"])
    assert all(c["is_default"] is True for c in categories)
    assert all(c["color"].startswith("#") for c in categories)


def test_FR06_default_categories_are_filtered_by_type(client: TestClient):
    token = signup(client)

    income = list_categories(client, token, "INCOME")

    assert {c["type"] for c in income} == {"INCOME"}
    assert len(income) == 4


# FR-07 카테고리 추가
def test_FR07_create_category_returns_201_and_appears_in_list(client: TestClient):
    token = signup(client)

    created = create_category(client, token, "  반려동물  ", "EXPENSE", color="#22c55e")

    assert created["name"] == "반려동물"
    assert created["is_default"] is False
    assert created["color"] == "#22c55e"
    assert "반려동물" in {c["name"] for c in list_categories(client, token, "EXPENSE")}


def test_FR07_duplicate_name_in_same_type_is_conflict(client: TestClient):
    token = signup(client)

    response = client.post("/api/categories", json={"name": "식비", "type": "EXPENSE"}, headers=csrf(token))

    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"
    assert "name" in response.json()["error"]["details"]


def test_FR07_same_name_is_allowed_for_the_other_type(client: TestClient):
    token = signup(client)

    response = client.post("/api/categories", json={"name": "급여", "type": "EXPENSE"}, headers=csrf(token))

    assert response.status_code == 201


def test_FR07_name_longer_than_twenty_characters_is_rejected(client: TestClient):
    token = signup(client)

    response = client.post(
        "/api/categories", json={"name": "가" * 21, "type": "EXPENSE"}, headers=csrf(token)
    )

    assert response.status_code == 400
    assert "name" in response.json()["error"]["details"]


def test_FR07_color_outside_palette_is_rejected(client: TestClient):
    token = signup(client)

    response = client.post(
        "/api/categories",
        json={"name": "새", "type": "EXPENSE", "color": "#000001"},
        headers=csrf(token),
    )

    assert response.status_code == 400
    assert "color" in response.json()["error"]["details"]


# FR-08 카테고리 수정
def test_FR08_rename_and_recolor_category(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.patch(
        f"/api/categories/{food}", json={"name": "외식", "color": "#3b82f6"}, headers=csrf(token)
    )

    assert response.status_code == 200
    assert response.json()["name"] == "외식"
    assert response.json()["color"] == "#3b82f6"


def test_FR08_rename_to_existing_name_is_conflict(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.patch(f"/api/categories/{food}", json={"name": "교통"}, headers=csrf(token))

    assert response.status_code == 409


def test_FR08_renaming_to_same_name_is_not_a_conflict(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.patch(f"/api/categories/{food}", json={"name": "식비"}, headers=csrf(token))

    assert response.status_code == 200


# FR-09 카테고리 삭제 (거래 이동)
def test_FR09_delete_moves_transactions_and_removes_category_budgets(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    shopping = category_id(client, token, "쇼핑")
    create_transaction(client, token, category=food, amount=10_000)
    create_transaction(client, token, category=food, amount=20_000)
    create_transaction(client, token, category=shopping, amount=30_000)
    create_budget(client, token, amount=100_000, category=food)
    create_budget(client, token, amount=500_000)  # 전체 예산은 유지됩니다

    response = client.delete(f"/api/categories/{food}?replacement_id={shopping}", headers=csrf(token))

    assert response.status_code == 204
    shopping_items = client.get(f"/api/transactions?category_id={shopping}").json()
    assert shopping_items["total"] == 3
    assert "식비" not in {c["name"] for c in list_categories(client, token)}
    budgets = client.get("/api/budgets?year_month=2026-11").json()
    assert [b["category_id"] for b in budgets] == [None]


def test_FR09_replacement_is_required(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.delete(f"/api/categories/{food}", headers=csrf(token))

    assert response.status_code == 400
    assert "replacement_id" in response.json()["error"]["details"]


def test_FR09_replacement_must_be_same_type(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    salary = category_id(client, token, "급여", "INCOME")

    response = client.delete(f"/api/categories/{food}?replacement_id={salary}", headers=csrf(token))

    assert response.status_code == 400
    assert "replacement_id" in response.json()["error"]["details"]


def test_FR09_replacement_cannot_be_the_deleted_category(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.delete(f"/api/categories/{food}?replacement_id={food}", headers=csrf(token))

    assert response.status_code == 400


def test_FR09_failure_in_the_middle_rolls_back_every_step(
    settings: Settings, clock: FakeClock, engine, monkeypatch
):
    app = create_app(settings, clock=clock, engine=engine)
    client = TestClient(app, raise_server_exceptions=False)
    token = signup(client)
    food = category_id(client, token, "식비")
    shopping = category_id(client, token, "쇼핑")
    create_transaction(client, token, category=food, amount=10_000)
    create_budget(client, token, amount=100_000, category=food)

    def _fail(*_args, **_kwargs):
        raise RuntimeError("의도적인 중간 실패")

    monkeypatch.setattr(BudgetRepository, "delete_by_ids", _fail)
    response = client.delete(f"/api/categories/{food}?replacement_id={shopping}", headers=csrf(token))

    assert response.status_code == 500
    assert error_code(response) == "INTERNAL_ERROR"
    # 거래 이동과 예산 삭제가 모두 되돌아가야 합니다
    assert "식비" in {c["name"] for c in list_categories(client, token)}
    assert client.get(f"/api/transactions?category_id={food}").json()["total"] == 1
    assert len(client.get("/api/budgets?year_month=2026-11").json()) == 1


def test_FR09_deleting_unknown_category_returns_404(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.delete(f"/api/categories/999999?replacement_id={food}", headers=csrf(token))

    assert response.status_code == 404
