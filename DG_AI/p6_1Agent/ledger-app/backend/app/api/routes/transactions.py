from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import CsrfUserId, CurrentUserId, TransactionServiceDep, rate_limit
from app.constants import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX
from app.repositories.transaction_repository import TransactionFilter
from app.schemas.transaction import (
    BudgetStatusOut,
    TransactionCreate,
    TransactionDeletedOut,
    TransactionMutationOut,
    TransactionOut,
    TransactionPageOut,
    TransactionUpdate,
)
from app.services.budget_service import BudgetStatus

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _status_out(statuses: list[BudgetStatus]) -> list[BudgetStatusOut]:
    return [BudgetStatusOut.model_validate(s) for s in statuses]


@router.get("", response_model=TransactionPageOut)
def list_transactions(
    user_id: CurrentUserId,
    service: TransactionServiceDep,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    category_id: list[int] | None = Query(default=None),
    type_: Literal["INCOME", "EXPENSE"] | None = Query(default=None, alias="type"),
    sort: Literal["date_desc", "amount_desc", "amount_asc"] = "date_desc",
    page: int = Query(default=1, ge=1),
    size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAX),
) -> TransactionPageOut:
    """FR-11. category_id는 여러 번 보내 다중 선택할 수 있습니다."""
    flt = TransactionFilter(
        date_from=date_from,
        date_to=date_to,
        category_ids=category_id,
        transaction_type=type_,
    )
    result = service.list_transactions(user_id, flt, sort=sort, page=page, size=size)
    return TransactionPageOut(
        items=[TransactionOut.model_validate(t) for t in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
    )


@router.post(
    "",
    status_code=201,
    response_model=TransactionMutationOut,
    dependencies=[Depends(rate_limit("write"))],
)
def create_transaction(
    body: TransactionCreate,
    user_id: CsrfUserId,
    service: TransactionServiceDep,
) -> TransactionMutationOut:
    """FR-10: 저장 후 예산 판정과 알림 생성까지 한 요청에서 처리합니다 (흐름 1)."""
    result = service.create(user_id, body)
    return TransactionMutationOut(
        transaction=TransactionOut.model_validate(result.transaction),
        budget_status=_status_out(result.budget_status),
    )


@router.patch(
    "/{transaction_id}",
    response_model=TransactionMutationOut,
    dependencies=[Depends(rate_limit("write"))],
)
def update_transaction(
    transaction_id: int,
    body: TransactionUpdate,
    user_id: CsrfUserId,
    service: TransactionServiceDep,
) -> TransactionMutationOut:
    """FR-12."""
    result = service.update(user_id, transaction_id, body)
    return TransactionMutationOut(
        transaction=TransactionOut.model_validate(result.transaction),
        budget_status=_status_out(result.budget_status),
    )


@router.delete(
    "/{transaction_id}",
    response_model=TransactionDeletedOut,
    dependencies=[Depends(rate_limit("write"))],
)
def delete_transaction(
    transaction_id: int,
    user_id: CsrfUserId,
    service: TransactionServiceDep,
) -> TransactionDeletedOut:
    """FR-13: 영구 삭제 (Q-05)."""
    statuses = service.delete(user_id, transaction_id)
    return TransactionDeletedOut(budget_status=_status_out(statuses))
