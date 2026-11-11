"""현재 시각 주입 지점.

저장되는 모든 일시는 UTC 기준 naive datetime으로 다룹니다 (SQLite는 시간대 정보를 보존하지 않음).
날짜 계산(월 경계, 오늘 판정)은 Asia/Seoul 기준으로 lib/dates.py에서 수행합니다.
테스트에서는 FakeClock으로 교체해 잠금 해제, 세션 만료를 검증합니다.
"""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """현재 UTC 시각을 tzinfo 없이 반환합니다."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)
