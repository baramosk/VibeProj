"""날짜와 월 계산 순수 함수 (FR-14, NFR-24, R-05).

모든 사용자 대면 날짜 판단은 Asia/Seoul 기준입니다. 입력은 UTC naive datetime (Clock 반환값)입니다.
"""

import calendar
import re
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

_YEAR_MONTH_PATTERN = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def today_kst(utc_now: datetime) -> date:
    return utc_now.replace(tzinfo=UTC).astimezone(KST).date()


def current_year_month_kst(utc_now: datetime) -> str:
    return year_month_of(today_kst(utc_now))


def year_month_of(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def parse_year_month(value: str) -> str:
    """YYYY-MM 형식을 검증해 그대로 돌려줍니다. 형식이 틀리면 ValueError."""
    if not _YEAR_MONTH_PATTERN.match(value):
        raise ValueError("년월은 YYYY-MM 형식으로 입력해 주세요.")
    return value


def month_bounds(year_month: str) -> tuple[date, date]:
    """해당 월의 첫날과 말일 (양끝 포함). 말일은 2월 윤년까지 반영합니다."""
    year, month = _split(year_month)
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def shift_month(year_month: str, delta: int) -> str:
    year, month = _split(year_month)
    index = year * 12 + (month - 1) + delta
    new_year, new_month_index = divmod(index, 12)
    return f"{new_year:04d}-{new_month_index + 1:02d}"


def months_ending_at(end_year_month: str, count: int) -> list[str]:
    """end를 포함한 최근 count개월을 오래된 순서로 반환합니다."""
    return [shift_month(end_year_month, offset) for offset in range(-(count - 1), 1)]


def _split(year_month: str) -> tuple[int, int]:
    match = _YEAR_MONTH_PATTERN.match(year_month)
    if not match:
        raise ValueError("년월은 YYYY-MM 형식으로 입력해 주세요.")
    return int(match.group(1)), int(match.group(2))
