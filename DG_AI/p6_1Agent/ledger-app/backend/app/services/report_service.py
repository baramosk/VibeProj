"""리포트 서비스: 월 요약, 카테고리별 지출, 월별 추이 (FR-14~FR-17).

기간 계산은 Asia/Seoul 기준 월 경계를 씁니다 (lib/dates.py).
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.constants import TREND_MONTHS_ALLOWED, TREND_MONTHS_DEFAULT
from app.core.clock import Clock
from app.core.errors import ValidationFailed
from app.lib.dates import current_year_month_kst, month_bounds, months_ending_at, year_month_of
from app.lib.money import percent_of
from app.repositories.transaction_repository import TransactionRepository


@dataclass(frozen=True)
class CategoryBreakdown:
    category_id: int
    name: str
    color: str
    amount: int
    ratio: float


@dataclass(frozen=True)
class MonthlyReport:
    year_month: str
    income_total: int
    expense_total: int
    balance: int
    by_category: list[CategoryBreakdown]


@dataclass(frozen=True)
class TrendPoint:
    year_month: str
    expense: int


class ReportService:
    def __init__(self, db: Session, clock: Clock) -> None:
        self._clock = clock
        self._transactions = TransactionRepository(db)

    def monthly(self, user_id: int, year_month: str) -> MonthlyReport:
        self._ensure_not_future(year_month)
        first, last = month_bounds(year_month)

        totals = self._transactions.sum_by_type(user_id, first, last)
        income = totals.get("INCOME", 0)
        expense = totals.get("EXPENSE", 0)

        breakdown = [
            CategoryBreakdown(
                category_id=row.category_id,
                name=row.name,
                color=row.color,
                amount=row.amount,
                ratio=percent_of(row.amount, expense),
            )
            for row in self._transactions.expense_by_category(user_id, first, last)
            if row.amount > 0
        ]
        return MonthlyReport(
            year_month=year_month,
            income_total=income,
            expense_total=expense,
            balance=income - expense,
            by_category=breakdown,
        )

    def trend(self, user_id: int, end_year_month: str | None, months: int | None) -> list[TrendPoint]:
        """FR-17: 기준 월을 포함한 최근 N개월의 지출 합계. 거래가 없는 월은 0원입니다."""
        months = TREND_MONTHS_DEFAULT if months is None else months
        if months not in TREND_MONTHS_ALLOWED:
            raise ValidationFailed(
                "기간은 6 또는 12개월만 선택할 수 있습니다.",
                {"months": "6 또는 12만 입력해 주세요."},
            )

        end = end_year_month or current_year_month_kst(self._clock.now())
        self._ensure_not_future(end)

        period = months_ending_at(end, months)
        first: date = month_bounds(period[0])[0]
        last: date = month_bounds(end)[1]

        totals = {year_month: 0 for year_month in period}
        for occurred_on, amount in self._transactions.expense_by_day(user_id, first, last):
            key = year_month_of(occurred_on)
            if key in totals:
                totals[key] += amount
        return [TrendPoint(year_month=year_month, expense=totals[year_month]) for year_month in period]

    def _ensure_not_future(self, year_month: str) -> None:
        if year_month > current_year_month_kst(self._clock.now()):
            raise ValidationFailed(
                "미래 월은 조회할 수 없습니다.", {"year_month": "미래 월은 조회할 수 없습니다."}
            )
