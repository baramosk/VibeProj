from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # 월별 조회와 집계 성능 (10.4, NFR-13)
        Index("ix_transactions_user_id_occurred_on", "user_id", "occurred_on"),
        CheckConstraint("type IN ('INCOME', 'EXPENSE')", name="type_values"),
        CheckConstraint("amount BETWEEN 1 AND 999999999", name="amount_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    # 카테고리 삭제는 서비스가 거래를 먼저 옮깁니다 (FR-09). DB에서도 고아 거래를 막습니다.
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"))
    type: Mapped[str] = mapped_column(String(10))
    amount: Mapped[int] = mapped_column(Integer)
    occurred_on: Mapped[date] = mapped_column(Date)
    memo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    category = relationship("Category", lazy="joined")

    @property
    def category_name(self) -> str:
        return self.category.name
