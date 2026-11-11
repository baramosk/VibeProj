from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # 같은 예산, 같은 월, 같은 임계치 알림은 한 번만 (FR-21, R-04)
        UniqueConstraint(
            "budget_id",
            "year_month",
            "threshold_percent",
            name="uq_notifications_budget_month_threshold",
        ),
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    budget_id: Mapped[int] = mapped_column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"))
    year_month: Mapped[str] = mapped_column(String(7))
    threshold_percent: Mapped[int] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(String(200))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)
