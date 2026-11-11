from collections.abc import Iterable
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models import Notification


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def insert_if_absent(self, values: dict[str, Any]) -> bool:
        """같은 (예산, 월, 임계치) 알림이 없을 때만 저장합니다. 저장되면 True.

        INSERT ... ON CONFLICT DO NOTHING으로 조회와 저장 사이의 경쟁 조건도 막습니다 (R-04).
        PostgreSQL로 옮기면 이 메서드의 dialect 삽입 구문만 바꾸면 됩니다.
        """
        stmt = (
            sqlite_insert(Notification)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["budget_id", "year_month", "threshold_percent"])
        )
        result = self._db.execute(stmt)
        return (result.rowcount or 0) == 1

    def get(self, user_id: int, notification_id: int) -> Notification | None:
        return self._db.scalar(
            select(Notification).where(Notification.user_id == user_id, Notification.id == notification_id)
        )

    def list_for_user(self, user_id: int, *, unread_only: bool) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
        return list(self._db.scalars(stmt).all())

    def unread_count(self, user_id: int) -> int:
        return int(
            self._db.scalar(
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            )
            or 0
        )

    def mark_all_read(self, user_id: int) -> None:
        self._db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
            .execution_options(synchronize_session=False)
        )

    def delete_by_budget_ids(self, user_id: int, budget_ids: Iterable[int]) -> None:
        ids = list(budget_ids)
        if ids:
            self._db.execute(
                delete(Notification).where(Notification.user_id == user_id, Notification.budget_id.in_(ids))
            )

    def delete_all_for_user(self, user_id: int) -> None:
        self._db.execute(delete(Notification).where(Notification.user_id == user_id))
