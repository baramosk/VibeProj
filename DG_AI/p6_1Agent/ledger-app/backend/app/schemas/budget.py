from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Amount, PositiveId, YearMonth

BudgetStatus = Literal["NORMAL", "WARNING", "EXCEEDED"]


class BudgetCreate(BaseModel):
    year_month: YearMonth
    amount: Amount
    # 없으면 전체 지출 예산 (A-08)
    category_id: PositiveId | None = None


class BudgetUpdate(BaseModel):
    amount: Amount


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year_month: str
    category_id: int | None
    category_name: str | None
    amount: int
    spent: int
    usage_percent: float
    status: BudgetStatus
