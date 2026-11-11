from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common import CategoryColor, CategoryName, UtcDateTime

CategoryType = Literal["INCOME", "EXPENSE"]


class CategoryCreate(BaseModel):
    name: CategoryName
    type: CategoryType
    color: CategoryColor | None = None


class CategoryUpdate(BaseModel):
    name: CategoryName | None = None
    color: CategoryColor | None = None

    @model_validator(mode="after")
    def _reject_explicit_null(self) -> "CategoryUpdate":
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("카테고리 이름을 비워 둘 수 없습니다.")
        if "color" in self.model_fields_set and self.color is None:
            raise ValueError("색상을 비워 둘 수 없습니다.")
        return self


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: CategoryType
    color: str
    is_default: bool
    created_at: UtcDateTime
