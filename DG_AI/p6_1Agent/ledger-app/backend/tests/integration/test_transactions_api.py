"""거래 API 통합 테스트 (FR-10~FR-13)."""

from fastapi.testclient import TestClient

from tests.conftest import FakeClock
from tests.helpers import (
    category_id,
    create_budget,
    create_transaction,
    csrf,
    error_code,
    signup,
)


# FR-10 거래 기록
def test_FR10_create_expense_returns_201_with_transaction_and_budget_status(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    body = create_transaction(client, token, category=food, amount=12_000, memo="점심")

    assert body["transaction"]["amount"] == 12_000
    assert body["transaction"]["category_name"] == "식비"
    assert body["transaction"]["memo"] == "점심"
    assert body["transaction"]["occurred_on"] == "2026-11-06"
    assert body["budget_status"] == []  # 예산이 없으면 상태 목록도 비어 있습니다


def test_FR10_income_does_not_touch_budgets(client: TestClient):
    token = signup(client)
    salary = category_id(client, token, "급여", "INCOME")
    create_budget(client, token, amount=1_000)

    body = create_transaction(client, token, category=salary, amount=3_000_000, transaction_type="INCOME")

    assert body["transaction"]["type"] == "INCOME"
    assert body["budget_status"] == []


def test_FR10_occurred_on_defaults_to_today_in_seoul(client: TestClient, clock: FakeClock):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 1000, "category_id": food},
        headers=csrf(token),
    )

    assert response.status_code == 201
    assert response.json()["transaction"]["occurred_on"] == "2026-11-06"


def test_FR10_future_date_is_rejected(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 1000, "category_id": food, "occurred_on": "2026-11-07"},
        headers=csrf(token),
    )

    assert response.status_code == 400
    assert "occurred_on" in response.json()["error"]["details"]


def test_FR10_zero_amount_is_rejected(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 0, "category_id": food},
        headers=csrf(token),
    )

    assert response.status_code == 400
    assert "amount" in response.json()["error"]["details"]


def test_FR10_decimal_amount_is_rejected(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 1000.5, "category_id": food},
        headers=csrf(token),
    )

    assert response.status_code == 400


def test_FR10_category_must_match_transaction_type(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.post(
        "/api/transactions",
        json={"type": "INCOME", "amount": 1000, "category_id": food},
        headers=csrf(token),
    )

    assert response.status_code == 400
    assert "category_id" in response.json()["error"]["details"]


def test_FR10_memo_longer_than_200_is_rejected(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 1000, "category_id": food, "memo": "가" * 201},
        headers=csrf(token),
    )

    assert response.status_code == 400
    assert "memo" in response.json()["error"]["details"]


# FR-11 거래 목록
def test_FR11_list_is_newest_first_and_paginated(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    for day in range(1, 6):
        create_transaction(client, token, category=food, amount=1000 * day, occurred_on=f"2026-11-0{day}")

    first_page = client.get("/api/transactions?page=1&size=2").json()
    second_page = client.get("/api/transactions?page=2&size=2").json()

    assert first_page["total"] == 5
    assert first_page["page"] == 1 and first_page["size"] == 2
    assert [t["occurred_on"] for t in first_page["items"]] == ["2026-11-05", "2026-11-04"]
    assert [t["occurred_on"] for t in second_page["items"]] == ["2026-11-03", "2026-11-02"]


def test_FR11_default_page_size_is_twenty(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    for _ in range(21):
        create_transaction(client, token, category=food, amount=100)

    body = client.get("/api/transactions").json()

    assert body["size"] == 20
    assert len(body["items"]) == 20
    assert body["total"] == 21


def test_FR11_sort_by_amount_and_filter_by_type_and_category(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    shopping = category_id(client, token, "쇼핑")
    salary = category_id(client, token, "급여", "INCOME")
    create_transaction(client, token, category=food, amount=5000)
    create_transaction(client, token, category=shopping, amount=20000)
    create_transaction(client, token, category=salary, amount=3_000_000, transaction_type="INCOME")

    by_amount = client.get("/api/transactions?type=EXPENSE&sort=amount_desc").json()
    assert [t["amount"] for t in by_amount["items"]] == [20000, 5000]

    multi = client.get(f"/api/transactions?category_id={food}&category_id={shopping}").json()
    assert multi["total"] == 2

    income = client.get("/api/transactions?type=INCOME").json()
    assert income["total"] == 1


def test_FR11_date_range_filter(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_transaction(client, token, category=food, occurred_on="2026-10-31")
    create_transaction(client, token, category=food, occurred_on="2026-11-01")  # 하한 포함
    create_transaction(client, token, category=food, occurred_on="2026-11-05")  # 상한 포함
    create_transaction(client, token, category=food, occurred_on="2026-11-06")

    body = client.get("/api/transactions?from=2026-11-01&to=2026-11-05").json()

    assert body["total"] == 2
    assert {t["occurred_on"] for t in body["items"]} == {"2026-11-01", "2026-11-05"}


def test_FR11_empty_result_returns_zero_total(client: TestClient):
    signup(client)

    body = client.get("/api/transactions").json()

    assert body == {"items": [], "total": 0, "page": 1, "size": 20}


def test_FR11_reversed_date_range_is_rejected(client: TestClient):
    signup(client)

    response = client.get("/api/transactions?from=2026-11-10&to=2026-11-01")

    assert response.status_code == 400


# FR-12 거래 수정
def test_FR12_update_amount_and_memo_returns_updated_transaction(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    created = create_transaction(client, token, category=food, amount=1000)["transaction"]

    response = client.patch(
        f"/api/transactions/{created['id']}",
        json={"amount": 2500, "memo": "수정됨"},
        headers=csrf(token),
    )

    assert response.status_code == 200
    assert response.json()["transaction"]["amount"] == 2500
    assert response.json()["transaction"]["memo"] == "수정됨"


def test_FR12_moving_to_another_month_recalculates_both_months_budgets(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    created = create_transaction(client, token, category=food, amount=60_000, occurred_on="2026-10-15")[
        "transaction"
    ]
    create_budget(client, token, year_month="2026-10", amount=100_000, category=food)
    create_budget(client, token, year_month="2026-11", amount=100_000, category=food)

    response = client.patch(
        f"/api/transactions/{created['id']}",
        json={"occurred_on": "2026-11-02"},
        headers=csrf(token),
    )

    assert response.status_code == 200
    statuses = {s["year_month"]: s for s in response.json()["budget_status"]}
    assert statuses["2026-10"]["spent"] == 0
    assert statuses["2026-11"]["spent"] == 60_000


def test_FR12_changing_category_type_must_still_match(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    salary = category_id(client, token, "급여", "INCOME")
    created = create_transaction(client, token, category=food, amount=1000)["transaction"]

    response = client.patch(
        f"/api/transactions/{created['id']}",
        json={"category_id": salary},
        headers=csrf(token),
    )

    assert response.status_code == 400


def test_FR12_update_with_null_amount_is_rejected(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    created = create_transaction(client, token, category=food, amount=1000)["transaction"]

    response = client.patch(f"/api/transactions/{created['id']}", json={"amount": None}, headers=csrf(token))

    assert response.status_code == 400


def test_FR12_explicit_null_memo_clears_the_memo(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    created = create_transaction(client, token, category=food, memo="지우기 전")["transaction"]

    response = client.patch(f"/api/transactions/{created['id']}", json={"memo": None}, headers=csrf(token))

    assert response.status_code == 200
    assert response.json()["transaction"]["memo"] is None


def test_FR12_unknown_transaction_returns_404(client: TestClient):
    token = signup(client)

    response = client.patch("/api/transactions/9999", json={"amount": 1}, headers=csrf(token))

    assert response.status_code == 404
    assert error_code(response) == "NOT_FOUND"


# FR-13 거래 삭제
def test_FR13_delete_removes_transaction_and_returns_budget_status(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    created = create_transaction(client, token, category=food, amount=30_000)["transaction"]
    create_budget(client, token, amount=100_000, category=food)
    create_budget(client, token, amount=500_000)

    response = client.delete(f"/api/transactions/{created['id']}", headers=csrf(token))

    assert response.status_code == 200
    statuses = response.json()["budget_status"]
    assert len(statuses) == 2  # 전체 예산과 식비 예산
    assert all(s["spent"] == 0 for s in statuses)
    assert client.get("/api/transactions").json()["total"] == 0


def test_FR13_deleting_twice_returns_404(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    created = create_transaction(client, token, category=food)["transaction"]
    client.delete(f"/api/transactions/{created['id']}", headers=csrf(token))

    response = client.delete(f"/api/transactions/{created['id']}", headers=csrf(token))

    assert response.status_code == 404
