"""예산, 초과 판정, 알림 생성 API 통합 테스트 (FR-18~FR-21, SC-04, A-09)."""

from fastapi.testclient import TestClient

from tests.helpers import (
    category_id,
    create_budget,
    create_transaction,
    csrf,
    error_code,
    list_categories,
    signup,
)


def _notifications(client: TestClient) -> list[dict]:
    return client.get("/api/notifications").json()["items"]


def _budget_by(budgets: list[dict], category: int | None) -> dict:
    return next(b for b in budgets if b["category_id"] == category)


# FR-18 예산 설정
def test_FR18_create_total_and_category_budgets_returns_201(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    total = create_budget(client, token, amount=500_000)
    food_budget = create_budget(client, token, amount=100_000, category=food)

    assert total["category_id"] is None and total["category_name"] is None
    assert total["spent"] == 0 and total["usage_percent"] == 0.0 and total["status"] == "NORMAL"
    assert food_budget["category_name"] == "식비"


def test_FR18_duplicate_budget_for_same_target_and_month_is_conflict(client: TestClient):
    token = signup(client)
    create_budget(client, token, amount=500_000)

    response = client.post(
        "/api/budgets", json={"year_month": "2026-11", "amount": 1000}, headers=csrf(token)
    )

    assert response.status_code == 409
    assert error_code(response) == "CONFLICT"


def test_FR18_same_category_in_another_month_is_allowed(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_budget(client, token, year_month="2026-10", amount=100_000, category=food)

    created = create_budget(client, token, year_month="2026-11", amount=100_000, category=food)

    assert created["year_month"] == "2026-11"


def test_FR18_income_category_cannot_have_budget(client: TestClient):
    token = signup(client)
    salary = category_id(client, token, "급여", "INCOME")

    response = client.post(
        "/api/budgets",
        json={"year_month": "2026-11", "amount": 1000, "category_id": salary},
        headers=csrf(token),
    )

    assert response.status_code == 400
    assert "category_id" in response.json()["error"]["details"]


def test_FR18_budget_amount_must_be_at_least_one_won(client: TestClient):
    token = signup(client)

    response = client.post("/api/budgets", json={"year_month": "2026-11", "amount": 0}, headers=csrf(token))

    assert response.status_code == 400


def test_FR18_update_amount_with_put(client: TestClient):
    token = signup(client)
    budget = create_budget(client, token, amount=500_000)

    response = client.put(f"/api/budgets/{budget['id']}", json={"amount": 700_000}, headers=csrf(token))

    assert response.status_code == 200
    assert response.json()["amount"] == 700_000


def test_FR18_delete_budget_returns_204(client: TestClient):
    token = signup(client)
    budget = create_budget(client, token, amount=500_000)

    response = client.delete(f"/api/budgets/{budget['id']}", headers=csrf(token))

    assert response.status_code == 204
    assert client.get("/api/budgets?year_month=2026-11").json() == []


def test_FR18_unknown_budget_returns_404(client: TestClient):
    token = signup(client)

    response = client.put("/api/budgets/9999", json={"amount": 1000}, headers=csrf(token))

    assert response.status_code == 404


# FR-19 사용률 표시
def test_FR19_list_shows_spent_usage_and_status_for_month(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_budget(client, token, amount=1000, category=food)
    create_transaction(client, token, category=food, amount=794)

    budgets = client.get("/api/budgets?year_month=2026-11").json()

    budget = _budget_by(budgets, food)
    assert budget["spent"] == 794
    assert budget["usage_percent"] == 79.4
    assert budget["status"] == "NORMAL"


def test_FR19_list_requires_year_month(client: TestClient):
    signup(client)

    response = client.get("/api/budgets")

    assert response.status_code == 400


# FR-20, FR-21 초과 판정과 알림 생성
def test_FR20_FR21_alerts_fire_once_per_threshold_and_follow_spec_message(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    shopping = category_id(client, token, "쇼핑")
    create_budget(client, token, amount=100_000)  # 전체 예산
    create_budget(client, token, amount=50_000, category=food)  # 식비 예산

    # 1) 식비 39,000원: 식비 78%, 전체 39% -> 알림 없음
    step1 = create_transaction(client, token, category=food, amount=39_000)
    assert all(s["new_thresholds"] == [] for s in step1["budget_status"])
    assert _notifications(client) == []

    # 2) 식비 1,000원 추가: 식비 80% -> 식비 80% 알림 1건
    step2 = create_transaction(client, token, category=food, amount=1_000)
    food_status = _budget_by(step2["budget_status"], food)
    assert food_status["usage_percent"] == 80.0
    assert food_status["new_thresholds"] == [80]
    notes = _notifications(client)
    assert len(notes) == 1
    assert notes[0]["threshold_percent"] == 80
    assert notes[0]["message"] == "11월 식비 예산의 80%를 사용했습니다 (40,000원 / 50,000원)."

    # 3) 식비 10,000원: 식비 100% -> 100% 알림 추가 (80%는 중복 생성 안 함)
    step3 = create_transaction(client, token, category=food, amount=10_000)
    assert _budget_by(step3["budget_status"], food)["new_thresholds"] == [100]
    assert sorted(n["threshold_percent"] for n in _notifications(client)) == [80, 100]

    # 4) 식비 1,000원 더: 102%, 새로 넘은 임계치 없음
    step4 = create_transaction(client, token, category=food, amount=1_000)
    assert _budget_by(step4["budget_status"], food)["new_thresholds"] == []
    assert len(_notifications(client)) == 2

    # 5) 쇼핑 50,000원: 전체 101% -> 전체 예산 80%, 100% 두 알림 (쇼핑 예산은 없음)
    step5 = create_transaction(client, token, category=shopping, amount=50_000)
    assert [s["category_id"] for s in step5["budget_status"]] == [None]
    total_status = step5["budget_status"][0]
    assert total_status["new_thresholds"] == [80, 100]
    assert len(_notifications(client)) == 4


def test_FR20_deleting_a_transaction_does_not_cancel_existing_alerts(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_budget(client, token, amount=10_000, category=food)
    created = create_transaction(client, token, category=food, amount=9_000)["transaction"]
    create_transaction(client, token, category=food, amount=1_000)  # 100% 도달
    assert len(_notifications(client)) == 2

    response = client.delete(f"/api/transactions/{created['id']}", headers=csrf(token))

    assert response.status_code == 200
    assert len(_notifications(client)) == 2  # A-09: 알림은 취소하지 않음
    budget = _budget_by(client.get("/api/budgets?year_month=2026-11").json(), food)
    assert budget["usage_percent"] == 10.0
    assert budget["status"] == "NORMAL"


def test_FR20_threshold_crossing_after_edit_creates_alert_once(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_budget(client, token, amount=10_000, category=food)
    small = create_transaction(client, token, category=food, amount=1_000)["transaction"]

    response = client.patch(f"/api/transactions/{small['id']}", json={"amount": 8_000}, headers=csrf(token))

    assert response.status_code == 200
    assert _budget_by(response.json()["budget_status"], food)["new_thresholds"] == [80]
    again = client.patch(f"/api/transactions/{small['id']}", json={"amount": 8_500}, headers=csrf(token))
    assert _budget_by(again.json()["budget_status"], food)["new_thresholds"] == []
    assert len(_notifications(client)) == 1


# SC-04: 경계값 79%, 80%, 100%, 100% 초과
def test_SC04_boundaries_79_4_normal_80_warning_100_exceeded_over_100(client: TestClient):
    token = signup(client)
    create_budget(client, token, amount=1000)

    create_transaction(client, token, category=category_id(client, token, "식비"), amount=794)
    assert _budget_by(client.get("/api/budgets?year_month=2026-11").json(), None)["status"] == "NORMAL"
    assert _notifications(client) == []

    create_transaction(client, token, category=category_id(client, token, "식비"), amount=6)
    total = _budget_by(client.get("/api/budgets?year_month=2026-11").json(), None)
    assert (total["usage_percent"], total["status"]) == (80.0, "WARNING")
    assert [n["threshold_percent"] for n in _notifications(client)] == [80]

    create_transaction(client, token, category=category_id(client, token, "식비"), amount=200)
    total = _budget_by(client.get("/api/budgets?year_month=2026-11").json(), None)
    assert (total["usage_percent"], total["status"]) == (100.0, "EXCEEDED")

    create_transaction(client, token, category=category_id(client, token, "식비"), amount=1)
    total = _budget_by(client.get("/api/budgets?year_month=2026-11").json(), None)
    assert (total["usage_percent"], total["status"]) == (100.1, "EXCEEDED")
    assert sorted(n["threshold_percent"] for n in _notifications(client)) == [80, 100]


def test_FR20_budget_creation_alone_does_not_create_alerts(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_transaction(client, token, category=food, amount=9_000)

    create_budget(client, token, amount=10_000, category=food)

    assert _notifications(client) == []


def test_FR20_category_list_is_available_for_budget_setup(client: TestClient):
    token = signup(client)

    expense = list_categories(client, token, "EXPENSE")

    assert all(c["type"] == "EXPENSE" for c in expense)
