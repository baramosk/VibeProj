"""금액과 비율 순수 함수 (FR-16, FR-19, FR-20, SC-04).

금액 합계는 정수로만 다루고, 비율 계산에만 Decimal을 씁니다 (R-06).
비율은 소수점 첫째 자리에서 반올림한 값을 기준으로 상태와 임계치를 판정합니다.
화면의 표시 값(정수 %)과 판정 값이 어긋나지 않게 하기 위함입니다.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Final

STATUS_NORMAL: Final = "NORMAL"
STATUS_WARNING: Final = "WARNING"
STATUS_EXCEEDED: Final = "EXCEEDED"

WARNING_PERCENT: Final = 80
EXCEEDED_PERCENT: Final = 100


def percent_of(part: int, whole: int) -> float:
    """part / whole × 100, 소수점 첫째 자리 반올림 (ROUND_HALF_UP). whole은 1 이상이어야 합니다."""
    if whole <= 0:
        raise ValueError("전체 금액은 1원 이상이어야 합니다.")
    ratio = Decimal(part) * 100 / Decimal(whole)
    return float(ratio.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def usage_percent(spent: int, amount: int) -> float:
    """예산 사용률 (%). 예산 금액 기준 percent_of."""
    return percent_of(spent, amount)


def budget_status(percent: float) -> str:
    if percent >= EXCEEDED_PERCENT:
        return STATUS_EXCEEDED
    if percent >= WARNING_PERCENT:
        return STATUS_WARNING
    return STATUS_NORMAL


def reached_thresholds(percent: float, thresholds: list[int]) -> list[int]:
    """사용률이 도달한 임계치 목록 (오름차순). 도달 여부는 '이상'으로 판정합니다."""
    return [threshold for threshold in sorted(thresholds) if percent >= threshold]


def format_won(amount: int) -> str:
    """예: 400000 -> "400,000원" (NFR-24: 원 단위, 소수점 없음)."""
    return f"{amount:,}원"
