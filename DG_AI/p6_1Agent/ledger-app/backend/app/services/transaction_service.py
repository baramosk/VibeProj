"""거래 서비스: 기록, 목록, 수정, 삭제 (FR-10~FR-13).

저장, 수정, 삭제 직후 같은 트랜잭션 안에서 예산 판정을 호출합니다 (흐름 1, 흐름 3).
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.core.errors import NotFoundError, ValidationFailed
from app.lib.dates import today_kst
from app.models import Category, Transaction
from app.repositories.category_repository import CategoryRepository
from app.repositories.transaction_repository import TransactionFilter, TransactionRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.budget_service import BudgetService, BudgetStatus, Scope, expense_scopes
from app.services.common import owned_category


@dataclass(frozen=True)
class TransactionResult:
    transaction: Transaction
    budget_status: list[BudgetStatus]


@dataclass(frozen=True)
class TransactionPage:
    items: list[Transaction]
    total: int
    page: int
    size: int


class TransactionService:
    def __init__(self, db: Session, clock: Clock, budget_service: BudgetService) -> None:
        self._db = db
        self._clock = clock
        self._budget_service = budget_service
        self._transactions = TransactionRepository(db)
        self._categories = CategoryRepository(db)

    def list_transactions(
        self,
        user_id: int,
        flt: TransactionFilter,
        *,
        sort: str,
        page: int,
        size: int,
    ) -> TransactionPage:
        if flt.date_from is not None and flt.date_to is not None and flt.date_from > flt.date_to:
            raise ValidationFailed(
                "종료일은 시작일 이후여야 합니다.", {"to": "종료일은 시작일 이후여야 합니다."}
            )
        items, total = self._transactions.list_page(user_id, flt, sort=sort, page=page, size=size)
        return TransactionPage(items=items, total=total, page=page, size=size)

    def create(self, user_id: int, data: TransactionCreate) -> TransactionResult:
        now = self._clock.now()
        today = today_kst(now)
        occurred_on = data.occurred_on or today
        category = owned_category(self._categories, user_id, data.category_id)
        self._check_category_type(category, data.type)
        self._check_not_future(occurred_on, today)

        transaction = Transaction(
            user_id=user_id,
            category=category,
            type=data.type,
            amount=data.amount,
            occurred_on=occurred_on,
            memo=data.memo,
            created_at=now,
            updated_at=now,
        )
        self._transactions.add(transaction)
        self._db.flush()

        statuses = self._budget_service.evaluate(user_id, expense_scopes(data.type, category.id, occurred_on))
        self._db.commit()
        return TransactionResult(transaction=transaction, budget_status=statuses)

    def update(self, user_id: int, transaction_id: int, data: TransactionUpdate) -> TransactionResult:
        transaction = self._owned(user_id, transaction_id)
        today = today_kst(self._clock.now())

        old_scopes = expense_scopes(transaction.type, transaction.category_id, transaction.occurred_on)

        new_type = data.type if data.type is not None else transaction.type
        new_amount = data.amount if data.amount is not None else transaction.amount
        new_occurred_on = data.occurred_on or transaction.occurred_on
        if data.category_id is not None:
            new_category = owned_category(self._categories, user_id, data.category_id)
        else:
            new_category = transaction.category
        self._check_category_type(new_category, new_type)
        self._check_not_future(new_occurred_on, today)

        transaction.type = new_type
        transaction.amount = new_amount
        transaction.occurred_on = new_occurred_on
        transaction.category = new_category
        if "memo" in data.model_fields_set:
            transaction.memo = data.memo
        transaction.updated_at = self._clock.now()
        self._db.flush()

        # 이전 월, 이전 카테고리와 새 월, 새 카테고리의 예산을 모두 다시 판정합니다 (흐름 3)
        scopes = _unique(old_scopes + expense_scopes(new_type, new_category.id, new_occurred_on))
        statuses = self._budget_service.evaluate(user_id, scopes)
        self._db.commit()
        return TransactionResult(transaction=transaction, budget_status=statuses)

    def delete(self, user_id: int, transaction_id: int) -> list[BudgetStatus]:
        transaction = self._owned(user_id, transaction_id)
        scopes: list[Scope] = expense_scopes(
            transaction.type, transaction.category_id, transaction.occurred_on
        )
        self._transactions.delete(transaction)
        self._db.flush()
        statuses = self._budget_service.evaluate(user_id, scopes)
        self._db.commit()
        return statuses

    def _owned(self, user_id: int, transaction_id: int) -> Transaction:
        transaction = self._transactions.get(user_id, transaction_id)
        if transaction is None:
            raise NotFoundError("거래를 찾을 수 없습니다.")
        return transaction

    @staticmethod
    def _check_category_type(category: Category, transaction_type: str) -> None:
        if category.type != transaction_type:
            raise ValidationFailed(
                "거래 유형과 맞지 않는 카테고리입니다.",
                {"category_id": "거래 유형과 맞지 않는 카테고리입니다."},
            )

    @staticmethod
    def _check_not_future(occurred_on: date, today: date) -> None:
        if occurred_on > today:
            raise ValidationFailed(
                "미래 날짜는 입력할 수 없습니다.",
                {"occurred_on": "미래 날짜는 입력할 수 없습니다."},
            )


def _unique(scopes: list[Scope]) -> list[Scope]:
    return list(dict.fromkeys(scopes))
