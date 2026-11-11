"""금액, 사용률, 날짜 순수 함수 단위 테스트 (FR-14, FR-17, FR-19, NFR-24, R-05, SC-04)."""

from datetime import UTC, date, datetime

import pytest

from app.lib.dates import (
    current_year_month_kst,
    month_bounds,
    months_ending_at,
    parse_year_month,
    shift_month,
    today_kst,
)
from app.lib.messages import budget_alert_message
from app.lib.money import (
    STATUS_EXCEEDED,
    STATUS_NORMAL,
    STATUS_WARNING,
    budget_status,
    format_won,
    percent_of,
    reached_thresholds,
    usage_percent,
)


# FR-19, SC-04: 79.4%는 정상, 80%는 주의, 100%는 초과
@pytest.mark.parametrize(
    ("spent", "amount", "expected_percent", "expected_status"),
    [
        (794, 1000, 79.4, STATUS_NORMAL),
        (799, 1000, 79.9, STATUS_NORMAL),
        (7995, 10000, 80.0, STATUS_WARNING),  # 79.95 -> 반올림 80.0 (ROUND_HALF_UP)
        (800, 1000, 80.0, STATUS_WARNING),
        (999, 1000, 99.9, STATUS_WARNING),
        (1000, 1000, 100.0, STATUS_EXCEEDED),
        (1001, 1000, 100.1, STATUS_EXCEEDED),
    ],
)
def test_FR19_usage_percent_and_status_boundaries(spent, amount, expected_percent, expected_status):
    percent = usage_percent(spent, amount)
    assert percent == expected_percent
    assert budget_status(percent) == expected_status


def test_FR19_usage_percent_rounds_half_up_to_one_decimal():
    assert percent_of(1, 3) == 33.3
    assert percent_of(2, 3) == 66.7
    assert percent_of(0, 500) == 0.0


def test_FR19_usage_percent_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        usage_percent(100, 0)


# FR-20: 임계치 도달 판정은 '이상'
def test_FR20_reached_thresholds_are_inclusive_and_sorted():
    assert reached_thresholds(79.9, [80, 100]) == []
    assert reached_thresholds(80.0, [80, 100]) == [80]
    assert reached_thresholds(100.0, [100, 80]) == [80, 100]


# NFR-24: 원 단위 표시
def test_NFR24_format_won_uses_thousand_separator_without_decimals():
    assert format_won(400000) == "400,000원"
    assert format_won(1) == "1원"


# FR-21 예시 문구와 일치하는지 확인
def test_FR21_budget_alert_message_matches_spec_example():
    message = budget_alert_message("2026-10", "전체 예산", 80, 400000, 500000)
    assert message == "10월 전체 예산의 80%를 사용했습니다 (400,000원 / 500,000원)."


def test_FR21_budget_alert_message_for_hundred_percent():
    message = budget_alert_message("2026-10", "식비 예산", 100, 500000, 500000)
    assert message == "10월 식비 예산의 100%에 도달했습니다 (500,000원 / 500,000원)."


# FR-14: 월 경계 (2월 말일, 윤년, 12월 31일)
@pytest.mark.parametrize(
    ("year_month", "first", "last"),
    [
        ("2028-02", date(2028, 2, 1), date(2028, 2, 29)),  # 윤년
        ("2027-02", date(2027, 2, 1), date(2027, 2, 28)),
        ("2026-12", date(2026, 12, 1), date(2026, 12, 31)),
    ],
)
def test_FR14_month_bounds_include_last_day(year_month, first, last):
    assert month_bounds(year_month) == (first, last)


def test_FR14_shift_and_trend_months_cross_year_boundary():
    assert shift_month("2027-01", -1) == "2026-12"
    assert shift_month("2026-12", 1) == "2027-01"
    assert months_ending_at("2027-02", 6) == [
        "2026-09",
        "2026-10",
        "2026-11",
        "2026-12",
        "2027-01",
        "2027-02",
    ]


# R-05: UTC와 KST 차이로 날짜가 바뀌는 경계
def test_R05_kst_today_uses_asia_seoul_not_utc():
    utc_now = datetime(2026, 12, 31, 15, 30)  # KST 2027-01-01 00:30
    assert today_kst(utc_now) == date(2027, 1, 1)
    assert current_year_month_kst(utc_now) == "2027-01"


def test_R05_utc_naive_input_is_treated_as_utc():
    utc_aware = datetime(2026, 12, 31, 14, 59, tzinfo=UTC)
    assert today_kst(utc_aware.replace(tzinfo=None)) == date(2026, 12, 31)


@pytest.mark.parametrize("value", ["2026-13", "2026-00", "2026-1", "26-11", "2026/11", ""])
def test_FR14_parse_year_month_rejects_invalid_format(value):
    with pytest.raises(ValueError):
        parse_year_month(value)
