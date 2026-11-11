from fastapi import APIRouter, Query

from app.api.deps import CurrentUserId, ReportServiceDep, query_year_month
from app.constants import TREND_MONTHS_DEFAULT
from app.schemas.report import MonthlyReportOut, TrendItemOut, TrendOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/monthly", response_model=MonthlyReportOut)
def monthly_report(
    user_id: CurrentUserId,
    service: ReportServiceDep,
    year_month: str = Query(...),
) -> MonthlyReportOut:
    """FR-14~FR-16: 월 요약과 카테고리별 지출. 미래 월은 400입니다."""
    report = service.monthly(user_id, query_year_month(year_month))
    return MonthlyReportOut.model_validate(report)


@router.get("/trend", response_model=TrendOut)
def trend_report(
    user_id: CurrentUserId,
    service: ReportServiceDep,
    end: str | None = Query(default=None),
    months: int = Query(default=TREND_MONTHS_DEFAULT),
) -> TrendOut:
    """FR-17: 기준 월(end)을 포함한 최근 6 또는 12개월의 월별 지출."""
    end_year_month = query_year_month(end) if end is not None else None
    points = service.trend(user_id, end_year_month, months)
    return TrendOut(items=[TrendItemOut.model_validate(p) for p in points])
