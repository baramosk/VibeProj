"""서비스 공통 헬퍼. 소유 확인과 커밋 시 유일 제약 충돌 변환을 한 곳에 둡니다."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Category
from app.repositories.category_repository import CategoryRepository


def commit_or_conflict(db: Session, message: str, details: dict[str, str] | None = None) -> None:
    """커밋 중 유일 제약 위반이 나면 롤백 후 409로 바꿉니다. 다른 오류는 그대로 올립니다."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(message, details) from exc


def owned_category(categories: CategoryRepository, user_id: int, category_id: int) -> Category:
    category = categories.get(user_id, category_id)
    if category is None:
        raise NotFoundError("카테고리를 찾을 수 없습니다.")
    return category
