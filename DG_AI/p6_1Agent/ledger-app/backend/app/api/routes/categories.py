from typing import Literal

from fastapi import APIRouter, Query, Response

from app.api.deps import CategoryServiceDep, CsrfUserId, CurrentUserId
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    user_id: CurrentUserId,
    service: CategoryServiceDep,
    type_: Literal["INCOME", "EXPENSE"] | None = Query(default=None, alias="type"),
) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in service.list_categories(user_id, type_)]


@router.post("", status_code=201, response_model=CategoryOut)
def create_category(body: CategoryCreate, user_id: CsrfUserId, service: CategoryServiceDep) -> CategoryOut:
    """FR-07."""
    return CategoryOut.model_validate(service.create(user_id, body))


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    body: CategoryUpdate,
    user_id: CsrfUserId,
    service: CategoryServiceDep,
) -> CategoryOut:
    """FR-08: 이름과 색상만 바꿉니다. 유형 변경은 계약에 없어 지원하지 않습니다."""
    return CategoryOut.model_validate(service.update(user_id, category_id, body))


@router.delete("/{category_id}", status_code=204, response_class=Response)
def delete_category(
    category_id: int,
    user_id: CsrfUserId,
    service: CategoryServiceDep,
    replacement_id: int | None = Query(default=None),
) -> Response:
    """FR-09: replacement_id로 거래를 옮긴 뒤 삭제합니다. 같은 유형만 가능합니다."""
    service.delete(user_id, category_id, replacement_id)
    return Response(status_code=204)
