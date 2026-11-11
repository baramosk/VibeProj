from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Category


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: int, category_type: str | None = None) -> list[Category]:
        stmt = select(Category).where(Category.user_id == user_id)
        if category_type is not None:
            stmt = stmt.where(Category.type == category_type)
        return list(self._db.scalars(stmt.order_by(Category.id)).all())

    def get(self, user_id: int, category_id: int) -> Category | None:
        return self._db.scalar(
            select(Category).where(Category.user_id == user_id, Category.id == category_id)
        )

    def find_by_name(
        self, user_id: int, category_type: str, name: str, exclude_id: int | None = None
    ) -> Category | None:
        stmt = select(Category).where(
            Category.user_id == user_id,
            Category.type == category_type,
            Category.name == name,
        )
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        return self._db.scalar(stmt)

    def add(self, category: Category) -> None:
        self._db.add(category)

    def delete(self, user_id: int, category_id: int) -> None:
        self._db.execute(delete(Category).where(Category.user_id == user_id, Category.id == category_id))

    def delete_all_for_user(self, user_id: int) -> None:
        self._db.execute(delete(Category).where(Category.user_id == user_id))
