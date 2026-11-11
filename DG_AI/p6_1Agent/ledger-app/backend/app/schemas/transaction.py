from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common import Amount, Memo, PositiveId, UtcDateTime

TransactionType = Literal["INCOME", "EXPENSE"]


class TransactionCreate(BaseModel):
    type: TransactionType
    amount: Amount
    category_id: PositiveId
    # 기본값은 오늘 (Asia/Seoul). 미래 날짜는 서비스에서 거부합니다 (FR-10).
    occurred_on: date | None = None
    memo: Memo = None


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    amount: Amount | None = None
    category_id: PositiveId | None = None
    occurred_on: date | None = None
    # 메모는 명시적으로 null을 보내 지울 수 있습니다.
    memo: Memo = None

    @model_validator(mode="after")
    def _reject_explicit_null(self) -> "TransactionUpdate":
        for field_name in ("type", "amount", "category_id", "occurred_on"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError("이 항목은 비워 둘 수 없습니다.")
        return self


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: TransactionType
    amount: int
    category_id: int
    category_name: str
    occurred_on: date
    memo: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class BudgetStatusOut(BaseModel):
    """거래 저장 후 영향받은 예산의 상태 (api-contract 3장, 흐름 1)."""

    model_config = ConfigDict(from_attributes=True)

    budget_id: int
    category_id: int | None
    year_month: str
    spent: int
    amount: int
    usage_percent: float
    new_thresholds: list[int]


class TransactionMutationOut(BaseModel):
    transaction: TransactionOut
    budget_status: list[BudgetStatusOut]


class TransactionDeletedOut(BaseModel):
    budget_status: list[BudgetStatusOut]


class TransactionPageOut(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    size: int


TransactionSort = Literal["date_desc", "amount_desc", "amount_asc"]
