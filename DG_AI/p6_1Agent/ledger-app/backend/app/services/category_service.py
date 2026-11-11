"""카테고리 서비스: 기본 카테고리 생성, 추가, 수정, 삭제 (FR-06~FR-09)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.constants import DEFAULT_CATEGORIES, DEFAULT_CATEGORY_COLOR
from app.core.clock import Clock
from app.core.errors import ConflictError, NotFoundError, ValidationFailed
from app.models import Category
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.common import commit_or_conflict, owned_category

NAME_TAKEN_MESSAGE = "같은 유형에 같은 이름의 카테고리가 있습니다."


def build_default_categories(user_id: int, now: datetime) -> list[Category]:
    """FR-06: 가입 시 사용자 계정에 복사할 기본 카테고리 목록."""
    return [
        Category(
            user_id=user_id,
            name=name,
            type=category_type,
            color=color,
            is_default=True,
            created_at=now,
        )
        for name, category_type, color in DEFAULT_CATEGORIES
    ]


@dataclass(frozen=True)
class CategoryDeleteResult:
    moved_transaction_count: int
    deleted_budget_count: int


class CategoryService:
    def __init__(self, db: Session, clock: Clock) -> None:
        self._db = db
        self._clock = clock
        self._categories = CategoryRepository(db)
        self._transactions = TransactionRepository(db)
        self._budgets = BudgetRepository(db)
        self._notifications = NotificationRepository(db)

    def list_categories(self, user_id: int, category_type: str | None = None) -> list[Category]:
        return self._categories.list_by_user(user_id, category_type)

    def create(self, user_id: int, data: CategoryCreate) -> Category:
        if self._categories.find_by_name(user_id, data.type, data.name) is not None:
            raise ConflictError(NAME_TAKEN_MESSAGE, {"name": "이미 사용 중인 이름입니다."})

        category = Category(
            user_id=user_id,
            name=data.name,
            type=data.type,
            color=data.color or DEFAULT_CATEGORY_COLOR,
            is_default=False,
            created_at=self._clock.now(),
        )
        self._categories.add(category)
        commit_or_conflict(self._db, NAME_TAKEN_MESSAGE, {"name": "이미 사용 중인 이름입니다."})
        return category

    def update(self, user_id: int, category_id: int, data: CategoryUpdate) -> Category:
        category = owned_category(self._categories, user_id, category_id)
        if data.name is not None and data.name != category.name:
            duplicate = self._categories.find_by_name(
                user_id, category.type, data.name, exclude_id=category.id
            )
            if duplicate is not None:
                raise ConflictError(NAME_TAKEN_MESSAGE, {"name": "이미 사용 중인 이름입니다."})
            category.name = data.name
        if data.color is not None:
            category.color = data.color

        commit_or_conflict(self._db, NAME_TAKEN_MESSAGE, {"name": "이미 사용 중인 이름입니다."})
        return category

    def delete(self, user_id: int, category_id: int, replacement_id: int | None) -> CategoryDeleteResult:
        """FR-09, 흐름 4: 거래를 대체 카테고리로 옮기고 예산을 지운 뒤 카테고리를 삭제합니다.

        모두 한 트랜잭션에서 처리합니다.
        """
        category = owned_category(self._categories, user_id, category_id)
        if replacement_id is None:
            raise ValidationFailed("대체 카테고리를 선택해 주세요.", {"replacement_id": "필수 항목입니다."})
        if replacement_id == category_id:
            raise ValidationFailed(
                "삭제할 카테고리와 다른 카테고리를 선택해 주세요.",
                {"replacement_id": "삭제할 카테고리와 다른 카테고리를 선택해 주세요."},
            )
        replacement = self._categories.get(user_id, replacement_id)
        if replacement is None:
            raise NotFoundError("대체 카테고리를 찾을 수 없습니다.")
        if replacement.type != category.type:
            raise ValidationFailed(
                "같은 유형의 카테고리로만 옮길 수 있습니다.",
                {"replacement_id": "같은 유형의 카테고리로만 옮길 수 있습니다."},
            )

        try:
            moved = self._transactions.move_category(user_id, category_id, replacement_id)
            budget_ids = self._budgets.list_ids_for_category(user_id, category_id)
            self._notifications.delete_by_budget_ids(user_id, budget_ids)
            self._budgets.delete_by_ids(user_id, budget_ids)
            self._categories.delete(user_id, category_id)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return CategoryDeleteResult(moved_transaction_count=moved, deleted_budget_count=len(budget_ids))
