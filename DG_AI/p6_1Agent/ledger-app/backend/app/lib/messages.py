"""사용자에게 보여줄 알림 문구 생성 (FR-21). 순수 함수입니다."""

from app.lib.money import format_won

EXAMPLE_FORMAT = "{month}월 {label}의 {threshold}%를 사용했습니다 ({spent} / {amount})."


def budget_alert_message(
    year_month: str,
    budget_label: str,
    threshold: int,
    spent: int,
    amount: int,
) -> str:
    """예: "10월 전체 예산의 80%를 사용했습니다 (400,000원 / 500,000원)." (기획서 FR-21 예시)"""
    month = int(year_month.split("-")[1])
    spent_text = format_won(spent)
    amount_text = format_won(amount)
    if threshold >= 100:
        return f"{month}월 {budget_label}의 {threshold}%에 도달했습니다 ({spent_text} / {amount_text})."
    return f"{month}월 {budget_label}의 {threshold}%를 사용했습니다 ({spent_text} / {amount_text})."
