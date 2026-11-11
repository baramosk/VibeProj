from fastapi import APIRouter, Query, Response

from app.api.deps import CsrfUserId, CurrentUserId, NotificationServiceDep
from app.schemas.notification import NotificationListOut, NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def list_notifications(
    user_id: CurrentUserId,
    service: NotificationServiceDep,
    unread_only: bool = Query(default=False),
) -> NotificationListOut:
    """FR-22: 최신순 목록과 읽지 않은 개수."""
    result = service.list_notifications(user_id, unread_only=unread_only)
    return NotificationListOut(
        items=[NotificationOut.model_validate(n) for n in result.items],
        unread_count=result.unread_count,
    )


@router.post("/read-all", status_code=204, response_class=Response)
def mark_all_read(user_id: CsrfUserId, service: NotificationServiceDep) -> Response:
    """FR-22 '모두 읽음'. 계약에 없던 엔드포인트라 계약 문서 반영이 필요합니다 (보고 참고)."""
    service.mark_all_read(user_id)
    return Response(status_code=204)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user_id: CsrfUserId, service: NotificationServiceDep) -> NotificationOut:
    return NotificationOut.model_validate(service.mark_read(user_id, notification_id))
