from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import Category, Transaction


@dataclass(frozen=True)
class CategoryTotal:
    category_id: int
    name: str
    color: str
    amount: int


@dataclass(frozen=True)
class TransactionFilter:
    date_from: date | None = None
    date_to: date | None = None
    category_ids: list[int] | None = None
    transaction_type: str | None = None


class TransactionRepository:
    """거래 데이터 접근. 모든 메서드는 user_id 조건을 포함합니다 (NFR-04)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int, transaction_id: int) -> Transaction | None:
        return self._db.scalar(
            select(Transaction).where(Transaction.user_id == user_id, Transaction.id == transaction_id)
        )

    def add(self, transaction: Transaction) -> None:
        self._db.add(transaction)

    def delete(self, transaction: Transaction) -> None:
        self._db.delete(transaction)

    def list_page(
        self,
        user_id: int,
        flt: TransactionFilter,
        *,
        sort: str,
        page: int,
        size: int,
    ) -> tuple[list[Transaction], int]:
        conditions = self._conditions(user_id, flt)
        total = self._db.scalar(select(func.count()).select_from(Transaction).where(*conditions)) or 0

        if sort == "amount_desc":
            order = (
                Transaction.amount.desc(),
                Transaction.occurred_on.desc(),
                Transaction.id.desc(),
            )
        elif sort == "amount_asc":
            order = (
                Transaction.amount.asc(),
                Transaction.occurred_on.desc(),
                Transaction.id.desc(),
            )
        else:
            order = (Transaction.occurred_on.desc(), Transaction.id.desc())

        stmt = select(Transaction).where(*conditions).order_by(*order).offset((page - 1) * size).limit(size)
        return list(self._db.scalars(stmt).all()), total

    def sum_by_type(self, user_id: int, date_from: date, date_to: date) -> dict[str, int]:
        rows = self._db.execute(
            select(Transaction.type, func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.occurred_on >= date_from,
                Transaction.occurred_on <= date_to,
            )
            .group_by(Transaction.type)
        ).all()
        return {row[0]: int(row[1]) for row in rows}

    def expense_by_category(self, user_id: int, date_from: date, date_to: date) -> list[CategoryTotal]:
        rows = self._db.execute(
            select(Category.id, Category.name, Category.color, func.sum(Transaction.amount))
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Category.user_id == user_id,
                Transaction.type == "EXPENSE",
                Transaction.occurred_on >= date_from,
                Transaction.occurred_on <= date_to,
            )
            .group_by(Category.id, Category.name, Category.color)
            .order_by(func.sum(Transaction.amount).desc(), Category.id)
        ).all()
        return [CategoryTotal(row[0], row[1], row[2], int(row[3])) for row in rows]

    def expense_by_day(self, user_id: int, date_from: date, date_to: date) -> list[tuple[date, int]]:
        rows = self._db.execute(
            select(Transaction.occurred_on, func.sum(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.type == "EXPENSE",
                Transaction.occurred_on >= date_from,
                Transaction.occurred_on <= date_to,
            )
            .group_by(Transaction.occurred_on)
        ).all()
        return [(row[0], int(row[1])) for row in rows]

    def move_category(self, user_id: int, from_category_id: int, to_category_id: int) -> int:
        result = self._db.execute(
            update(Transaction)
            .where(Transaction.user_id == user_id, Transaction.category_id == from_category_id)
            .values(category_id=to_category_id)
            .execution_options(synchronize_session=False)
        )
        return int(result.rowcount or 0)

    def delete_all_for_user(self, user_id: int) -> None:
        self._db.execute(delete(Transaction).where(Transaction.user_id == user_id))

    def count_by_category(self, user_id: int) -> dict[int, int]:
        """Q-C: 카테고리별 거래 수. 거래가 없는 카테고리는 결과에 없습니다."""
        rows = self._db.execute(
            select(Transaction.category_id, func.count())
            .where(Transaction.user_id == user_id)
            .group_by(Transaction.category_id)
        ).all()
        return {int(row[0]): int(row[1]) for row in rows}

    def count_for_category(self, user_id: int, category_id: int) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(Transaction)
                .where(Transaction.user_id == user_id, Transaction.category_id == category_id)
            )
            or 0
        )

    @staticmethod
    def _conditions(user_id: int, flt: TransactionFilter) -> list:
        conditions = [Transaction.user_id == user_id]
        if flt.date_from is not None:
            conditions.append(Transaction.occurred_on >= flt.date_from)
        if flt.date_to is not None:
            conditions.append(Transaction.occurred_on <= flt.date_to)
        if flt.category_ids:
            conditions.append(Transaction.category_id.in_(flt.category_ids))
        if flt.transaction_type is not None:
            conditions.append(Transaction.type == flt.transaction_type)
        return conditions
