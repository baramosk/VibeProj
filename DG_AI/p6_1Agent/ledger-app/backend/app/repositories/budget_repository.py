from collections.abc import Iterable

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models import Budget, Category


class BudgetRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: int, budget_id: int) -> Budget | None:
        return self._db.scalar(select(Budget).where(Budget.user_id == user_id, Budget.id == budget_id))

    def find(self, user_id: int, year_month: str, category_id: int | None) -> Budget | None:
        category_condition = (
            Budget.category_id.is_(None) if category_id is None else Budget.category_id == category_id
        )
        return self._db.scalar(
            select(Budget).where(
                Budget.user_id == user_id,
                Budget.year_month == year_month,
                category_condition,
            )
        )

    def list_for_month(self, user_id: int, year_month: str) -> list[Budget]:
        stmt = (
            select(Budget)
            .outerjoin(Category, Budget.category_id == Category.id)
            .where(Budget.user_id == user_id, Budget.year_month == year_month)
            .order_by(Budget.category_id.is_not(None), Category.name, Budget.id)
        )
        return list(self._db.scalars(stmt).all())

    def list_for_scopes(
        self, user_id: int, year_months: Iterable[str], category_ids: Iterable[int]
    ) -> list[Budget]:
        """거래가 영향을 주는 예산 후보 조회.

        전체 예산 (category_id NULL)과 해당 카테고리 예산을 포함합니다.
        """
        month_list = list(year_months)
        category_list = list(category_ids)
        if not month_list:
            return []
        category_condition = Budget.category_id.is_(None)
        if category_list:
            category_condition = or_(category_condition, Budget.category_id.in_(category_list))
        stmt = select(Budget).where(
            Budget.user_id == user_id,
            Budget.year_month.in_(month_list),
            category_condition,
        )
        return list(self._db.scalars(stmt).all())

    def list_ids_for_category(self, user_id: int, category_id: int) -> list[int]:
        return list(
            self._db.scalars(
                select(Budget.id).where(Budget.user_id == user_id, Budget.category_id == category_id)
            ).all()
        )

    def add(self, budget: Budget) -> None:
        self._db.add(budget)

    def delete(self, budget: Budget) -> None:
        self._db.delete(budget)

    def delete_by_ids(self, user_id: int, budget_ids: Iterable[int]) -> None:
        ids = list(budget_ids)
        if ids:
            self._db.execute(delete(Budget).where(Budget.user_id == user_id, Budget.id.in_(ids)))

    def delete_all_for_user(self, user_id: int) -> None:
        self._db.execute(delete(Budget).where(Budget.user_id == user_id))
