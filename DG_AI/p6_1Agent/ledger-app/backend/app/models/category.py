from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        # 같은 사용자, 같은 유형 안에서 이름 중복 금지 (10.4, FR-07)
        UniqueConstraint("user_id", "type", "name", name="uq_categories_user_id_type_name"),
        CheckConstraint("type IN ('INCOME', 'EXPENSE')", name="type_values"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(10))
    color: Mapped[str] = mapped_column(String(7))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime)
