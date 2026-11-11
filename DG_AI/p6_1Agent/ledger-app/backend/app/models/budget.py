from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Budget(Base):
    """월 예산. category_id가 NULL이면 전체 지출 예산입니다 (A-08).

    NULL은 일반 UNIQUE 제약에서 서로 다른 값으로 취급되므로, 두 개의 부분 유일 인덱스로 중복을 막습니다.
    """

    __tablename__ = "budgets"
    __table_args__ = (
        Index(
            "uq_budgets_user_id_year_month_total",
            "user_id",
            "year_month",
            unique=True,
            sqlite_where=text("category_id IS NULL"),
            postgresql_where=text("category_id IS NULL"),
        ),
        Index(
            "uq_budgets_user_id_category_id_year_month",
            "user_id",
            "category_id",
            "year_month",
            unique=True,
            sqlite_where=text("category_id IS NOT NULL"),
            postgresql_where=text("category_id IS NOT NULL"),
        ),
        CheckConstraint("amount BETWEEN 1 AND 999999999", name="amount_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
    )
    year_month: Mapped[str] = mapped_column(String(7))
    amount: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    category = relationship("Category", lazy="joined")

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category is not None else None
