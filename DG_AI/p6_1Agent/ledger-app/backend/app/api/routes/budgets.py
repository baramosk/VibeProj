from fastapi import APIRouter, Query, Response

from app.api.deps import BudgetServiceDep, CsrfUserId, CurrentUserId, query_year_month
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetOut])
def list_budgets(
    user_id: CurrentUserId,
    service: BudgetServiceDep,
    year_month: str = Query(...),
) -> list[BudgetOut]:
    """FR-19: 월별 예산과 사용률."""
    views = service.list_for_month(user_id, query_year_month(year_month))
    return [BudgetOut.model_validate(v) for v in views]


@router.post("", status_code=201, response_model=BudgetOut)
def create_budget(body: BudgetCreate, user_id: CsrfUserId, service: BudgetServiceDep) -> BudgetOut:
    """FR-18. 같은 대상과 월의 예산이 있으면 409입니다 (덮어쓰기는 PUT으로)."""
    view = service.create(user_id, body.year_month, body.amount, body.category_id)
    return BudgetOut.model_validate(view)


@router.put("/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: int,
    body: BudgetUpdate,
    user_id: CsrfUserId,
    service: BudgetServiceDep,
) -> BudgetOut:
    view = service.update_amount(user_id, budget_id, body.amount)
    return BudgetOut.model_validate(view)


@router.delete("/{budget_id}", status_code=204, response_class=Response)
def delete_budget(budget_id: int, user_id: CsrfUserId, service: BudgetServiceDep) -> Response:
    service.delete(user_id, budget_id)
    return Response(status_code=204)
