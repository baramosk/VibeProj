from pydantic import BaseModel, ConfigDict


class CategoryBreakdownOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category_id: int
    name: str
    color: str
    amount: int
    ratio: float


class MonthlyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year_month: str
    income_total: int
    expense_total: int
    balance: int
    by_category: list[CategoryBreakdownOut]


class TrendItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    year_month: str
    expense: int


class TrendOut(BaseModel):
    items: list[TrendItemOut]
