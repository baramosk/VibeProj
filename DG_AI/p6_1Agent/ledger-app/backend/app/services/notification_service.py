"""알림 서비스: 목록 조회, 읽음 처리 (FR-22). 알림 생성은 budget_service.evaluate가 담당합니다."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Notification
from app.repositories.notification_repository import NotificationRepository


@dataclass(frozen=True)
class NotificationList:
    items: list[Notification]
    unread_count: int


class NotificationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._notifications = NotificationRepository(db)

    def list_notifications(self, user_id: int, *, unread_only: bool) -> NotificationList:
        items = self._notifications.list_for_user(user_id, unread_only=unread_only)
        return NotificationList(items=items, unread_count=self._notifications.unread_count(user_id))

    def mark_read(self, user_id: int, notification_id: int) -> Notification:
        notification = self._notifications.get(user_id, notification_id)
        if notification is None:
            raise NotFoundError("알림을 찾을 수 없습니다.")
        notification.is_read = True
        self._db.commit()
        return notification

    def mark_all_read(self, user_id: int) -> None:
        self._notifications.mark_all_read(user_id)
        self._db.commit()
