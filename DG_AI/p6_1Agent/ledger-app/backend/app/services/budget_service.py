"""예산 서비스: 설정, 조회, 사용률 계산, 임계치 판정과 알림 생성 요청 (FR-18~FR-21).

거래 서비스가 저장, 수정, 삭제 직후 evaluate()를 호출합니다 (흐름 1, 흐름 3, A-10 동기 처리).
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.lib.dates import month_bounds, year_month_of
from app.lib.messages import budget_alert_message
from app.lib.money import budget_status, reached_thresholds, usage_percent
from app.models import Budget, Category
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.common import commit_or_conflict, owned_category

# (년월, 카테고리 ID 또는 None). None은 전체 지출 예산을 뜻합니다.
Scope = tuple[str, int | None]

DUPLICATE_BUDGET_MESSAGE = "같은 대상과 월의 예산이 이미 있습니다. 금액을 수정해 주세요."


def expense_scopes(transaction_type: str, category_id: int, occurred_on: date) -> list[Scope]:
    """거래가 영향을 주는 예산 범위. 지출만 예산에 영향을 줍니다 (A-07)."""
    if transaction_type != "EXPENSE":
        return []
    year_month = year_month_of(occurred_on)
    return [(year_month, None), (year_month, category_id)]


@dataclass(frozen=True)
class BudgetView:
    id: int
    year_month: str
    category_id: int | None
    category_name: str | None
    amount: int
    spent: int
    usage_percent: float
    status: str


@dataclass(frozen=True)
class BudgetStatus:
    budget_id: int
    category_id: int | None
    year_month: str
    spent: int
    amount: int
    usage_percent: float
    new_thresholds: list[int]


@dataclass(frozen=True)
class _MonthSpending:
    total: int
    by_category: dict[int, int]

    def spent_for(self, category_id: int | None) -> int:
        return self.total if category_id is None else self.by_category.get(category_id, 0)


class BudgetService:
    def __init__(self, db: Session, clock: Clock, settings: Settings) -> None:
        self._db = db
        self._clock = clock
        self._thresholds = settings.budget_alert_thresholds
        self._budgets = BudgetRepository(db)
        self._categories = CategoryRepository(db)
        self._transactions = TransactionRepository(db)
        self._notifications = NotificationRepository(db)

    def list_for_month(self, user_id: int, year_month: str) -> list[BudgetView]:
        spending = self._month_spending(user_id, year_month)
        return [self._view(budget, spending) for budget in self._budgets.list_for_month(user_id, year_month)]

    def create(self, user_id: int, year_month: str, amount: int, category_id: int | None) -> BudgetView:
        category: Category | None = None
        if category_id is not None:
            category = owned_category(self._categories, user_id, category_id)
            if category.type != "EXPENSE":
                raise ValidationFailed(
                    "지출 카테고리에만 예산을 설정할 수 있습니다.",
                    {"category_id": "지출 카테고리에만 예산을 설정할 수 있습니다."},
                )
        if self._budgets.find(user_id, year_month, category_id) is not None:
            raise ConflictError(DUPLICATE_BUDGET_MESSAGE, {"year_month": DUPLICATE_BUDGET_MESSAGE})

        now = self._clock.now()
        budget = Budget(
            user_id=user_id,
            category=category,
            year_month=year_month,
            amount=amount,
            created_at=now,
            updated_at=now,
        )
        self._budgets.add(budget)
        commit_or_conflict(self._db, DUPLICATE_BUDGET_MESSAGE, {"year_month": DUPLICATE_BUDGET_MESSAGE})
        return self._view(budget, self._month_spending(user_id, year_month))

    def update_amount(self, user_id: int, budget_id: int, amount: int) -> BudgetView:
        budget = self._owned_budget(user_id, budget_id)
        budget.amount = amount
        budget.updated_at = self._clock.now()
        self._db.commit()
        return self._view(budget, self._month_spending(user_id, budget.year_month))

    def delete(self, user_id: int, budget_id: int) -> None:
        budget = self._owned_budget(user_id, budget_id)
        self._notifications.delete_by_budget_ids(user_id, [budget.id])
        self._budgets.delete(budget)
        self._db.commit()

    def evaluate(self, user_id: int, scopes: list[Scope]) -> list[BudgetStatus]:
        """영향받은 예산의 사용률을 계산하고, 새로 넘은 임계치마다 알림을 만듭니다 (FR-20, FR-21).

        알림 저장은 호출자의 트랜잭션 안에서 이뤄지며, 커밋은 호출자가 합니다.
        같은 (예산, 월, 임계치) 알림이 이미 있으면 만들지 않습니다.
        """
        if not scopes:
            return []

        scope_keys = set(scopes)
        year_months = {year_month for year_month, _ in scopes}
        category_ids = {category_id for _, category_id in scopes if category_id is not None}
        candidates = self._budgets.list_for_scopes(user_id, year_months, category_ids)

        now = self._clock.now()
        spending_cache: dict[str, _MonthSpending] = {}
        results: list[BudgetStatus] = []
        for budget in candidates:
            if (budget.year_month, budget.category_id) not in scope_keys:
                continue
            if budget.year_month not in spending_cache:
                spending_cache[budget.year_month] = self._month_spending(user_id, budget.year_month)
            spent = spending_cache[budget.year_month].spent_for(budget.category_id)
            percent = usage_percent(spent, budget.amount)

            new_thresholds: list[int] = []
            for threshold in reached_thresholds(percent, self._thresholds):
                message = budget_alert_message(
                    budget.year_month,
                    _budget_label(budget),
                    threshold,
                    spent,
                    budget.amount,
                )
                inserted = self._notifications.insert_if_absent(
                    {
                        "user_id": user_id,
                        "budget_id": budget.id,
                        "year_month": budget.year_month,
                        "threshold_percent": threshold,
                        "message": message,
                        "is_read": False,
                        "created_at": now,
                    }
                )
                if inserted:
                    new_thresholds.append(threshold)

            results.append(
                BudgetStatus(
                    budget_id=budget.id,
                    category_id=budget.category_id,
                    year_month=budget.year_month,
                    spent=spent,
                    amount=budget.amount,
                    usage_percent=percent,
                    new_thresholds=new_thresholds,
                )
            )
        return results

    def _owned_budget(self, user_id: int, budget_id: int) -> Budget:
        budget = self._budgets.get(user_id, budget_id)
        if budget is None:
            raise NotFoundError("예산을 찾을 수 없습니다.")
        return budget

    def _month_spending(self, user_id: int, year_month: str) -> _MonthSpending:
        first, last = month_bounds(year_month)
        totals = self._transactions.sum_by_type(user_id, first, last)
        by_category = {
            row.category_id: row.amount
            for row in self._transactions.expense_by_category(user_id, first, last)
        }
        return _MonthSpending(total=totals.get("EXPENSE", 0), by_category=by_category)

    def _view(self, budget: Budget, spending: _MonthSpending) -> BudgetView:
        spent = spending.spent_for(budget.category_id)
        percent = usage_percent(spent, budget.amount)
        return BudgetView(
            id=budget.id,
            year_month=budget.year_month,
            category_id=budget.category_id,
            category_name=budget.category_name,
            amount=budget.amount,
            spent=spent,
            usage_percent=percent,
            status=budget_status(percent),
        )


def _budget_label(budget: Budget) -> str:
    return "전체 예산" if budget.category_id is None else f"{budget.category_name} 예산"
