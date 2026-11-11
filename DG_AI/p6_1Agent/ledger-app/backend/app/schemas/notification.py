from pydantic import BaseModel, ConfigDict

from app.schemas.common import UtcDateTime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    budget_id: int
    year_month: str
    threshold_percent: int
    message: str
    is_read: bool
    created_at: UtcDateTime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    unread_count: int
