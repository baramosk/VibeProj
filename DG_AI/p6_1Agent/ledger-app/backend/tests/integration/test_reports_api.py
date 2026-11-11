"""리포트 API 통합 테스트 (FR-14~FR-17)."""

from datetime import datetime

from fastapi.testclient import TestClient

from tests.conftest import FakeClock
from tests.helpers import category_id, create_transaction, signup


# FR-14 월 선택 (미래 월 불가)
def test_FR14_future_month_is_rejected(client: TestClient):
    signup(client)

    response = client.get("/api/reports/monthly?year_month=2026-12")

    assert response.status_code == 400
    assert "year_month" in response.json()["error"]["details"]


def test_FR14_invalid_month_format_is_rejected(client: TestClient):
    signup(client)

    response = client.get("/api/reports/monthly?year_month=2026-13")

    assert response.status_code == 400


def test_FR14_month_boundary_leap_day_and_new_year_are_counted_in_correct_month(
    client: TestClient, clock: FakeClock
):
    # 2028년 윤년 2월 말일과 12월 31일을 확인하기 위해 시계를 2029년 초로 옮깁니다.
    clock.set(datetime(2029, 1, 10, 3, 0))
    token = signup(client)
    food = category_id(client, token, "식비")
    create_transaction(client, token, category=food, amount=100, occurred_on="2028-02-29")
    create_transaction(client, token, category=food, amount=200, occurred_on="2028-03-01")
    create_transaction(client, token, category=food, amount=300, occurred_on="2028-12-31")
    create_transaction(client, token, category=food, amount=400, occurred_on="2029-01-01")

    feb = client.get("/api/reports/monthly?year_month=2028-02").json()
    dec = client.get("/api/reports/monthly?year_month=2028-12").json()
    jan = client.get("/api/reports/monthly?year_month=2029-01").json()

    assert feb["expense_total"] == 100
    assert dec["expense_total"] == 300
    assert jan["expense_total"] == 400


def test_FR14_kst_month_boundary_uses_seoul_date(client: TestClient, clock: FakeClock):
    # UTC 2026-12-31 15:30 은 KST 2027-01-01 00:30 입니다. 오늘이 2027-01-01로 판정되어야 합니다.
    clock.set(datetime(2026, 12, 31, 15, 30))
    token = signup(client)
    food = category_id(client, token, "식비")

    response = client.post(
        "/api/transactions",
        json={"type": "EXPENSE", "amount": 1000, "category_id": food, "occurred_on": "2027-01-01"},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 201
    assert client.get("/api/reports/monthly?year_month=2027-01").json()["expense_total"] == 1000


# FR-15 월 요약
def test_FR15_summary_with_no_transactions_is_all_zero(client: TestClient):
    signup(client)

    body = client.get("/api/reports/monthly?year_month=2026-11").json()

    assert body == {
        "year_month": "2026-11",
        "income_total": 0,
        "expense_total": 0,
        "balance": 0,
        "by_category": [],
    }


def test_FR15_summary_computes_income_expense_and_balance(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    salary = category_id(client, token, "급여", "INCOME")
    create_transaction(client, token, category=salary, amount=3_000_000, transaction_type="INCOME")
    create_transaction(client, token, category=food, amount=1_200_000)

    body = client.get("/api/reports/monthly?year_month=2026-11").json()

    assert body["income_total"] == 3_000_000
    assert body["expense_total"] == 1_200_000
    assert body["balance"] == 1_800_000


# FR-16 카테고리별 지출
def test_FR16_category_breakdown_is_sorted_desc_excludes_zero_and_income(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    transport = category_id(client, token, "교통")
    shopping = category_id(client, token, "쇼핑")
    salary = category_id(client, token, "급여", "INCOME")
    create_transaction(client, token, category=transport, amount=100_000)
    create_transaction(client, token, category=food, amount=300_000)
    create_transaction(client, token, category=food, amount=100_000)
    create_transaction(client, token, category=salary, amount=9_000_000, transaction_type="INCOME")

    body = client.get("/api/reports/monthly?year_month=2026-11").json()

    names = [item["name"] for item in body["by_category"]]
    assert names == ["식비", "교통"]  # 쇼핑은 거래가 없어서 제외, 급여는 수입이라 제외
    assert body["by_category"][0]["amount"] == 400_000
    assert body["by_category"][0]["ratio"] == 80.0
    assert body["by_category"][1]["ratio"] == 20.0
    assert "쇼핑" not in names and shopping not in [i["category_id"] for i in body["by_category"]]
    assert "color" in body["by_category"][0]


def test_FR16_ratio_is_rounded_to_one_decimal(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    transport = category_id(client, token, "교통")
    create_transaction(client, token, category=food, amount=1)
    create_transaction(client, token, category=transport, amount=2)

    body = client.get("/api/reports/monthly?year_month=2026-11").json()

    assert [item["ratio"] for item in body["by_category"]] == [66.7, 33.3]


# FR-17 월별 추이
def test_FR17_trend_defaults_to_twelve_months_ending_this_month_with_zero_fill(client: TestClient):
    token = signup(client)
    food = category_id(client, token, "식비")
    create_transaction(client, token, category=food, amount=5000, occurred_on="2026-03-10")
    create_transaction(client, token, category=food, amount=7000, occurred_on="2026-11-01")

    body = client.get("/api/reports/trend").json()

    items = body["items"]
    assert len(items) == 12
    assert items[0]["year_month"] == "2025-12"
    assert items[-1]["year_month"] == "2026-11"
    by_month = {i["year_month"]: i["expense"] for i in items}
    assert by_month["2026-03"] == 5000
    assert by_month["2026-11"] == 7000
    assert by_month["2025-12"] == 0


def test_FR17_trend_supports_six_months_and_custom_end(client: TestClient):
    signup(client)

    body = client.get("/api/reports/trend?end=2026-06&months=6").json()

    assert [i["year_month"] for i in body["items"]] == [
        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
    ]


def test_FR17_trend_rejects_future_end_and_unsupported_months(client: TestClient):
    signup(client)

    assert client.get("/api/reports/trend?end=2026-12").status_code == 400
    assert client.get("/api/reports/trend?months=7").status_code == 400
