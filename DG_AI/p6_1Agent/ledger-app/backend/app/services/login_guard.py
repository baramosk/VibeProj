"""로그인 실패 잠금 정책 (FR-02, NFR-07).

- window 분 안에 max_failures 회 실패하면 lock 분 동안 잠급니다.
- 잠금 중에는 비밀번호를 검사하지 않고 거부합니다.
- 잠금 상태는 사용자 행에 저장합니다. 시각은 주입된 Clock으로 판단합니다.
"""

import math
from datetime import datetime, timedelta

from app.core.config import Settings
from app.models import User


class LoginGuard:
    def __init__(self, settings: Settings) -> None:
        self._max_failures = settings.login_max_failures
        self._window = timedelta(minutes=settings.login_failure_window_minutes)
        self._lock_duration = timedelta(minutes=settings.login_lock_minutes)

    @property
    def lock_seconds(self) -> int:
        return int(self._lock_duration.total_seconds())

    def remaining_lock_seconds(self, user: User, now: datetime) -> int | None:
        """잠금 중이면 남은 초, 아니면 None."""
        if user.locked_until is not None and user.locked_until > now:
            return math.ceil((user.locked_until - now).total_seconds())
        return None

    def record_failure(self, user: User, now: datetime) -> bool:
        """실패를 기록합니다. 이번 실패로 잠겼으면 True."""
        if user.locked_until is not None and user.locked_until <= now:
            self.reset(user)

        window_start = user.failed_login_window_started_at
        if window_start is None or now - window_start >= self._window:
            window_start = now
            count = 0
        else:
            count = user.failed_login_count or 0

        count += 1
        if count >= self._max_failures:
            user.locked_until = now + self._lock_duration
            user.failed_login_count = 0
            user.failed_login_window_started_at = None
            return True

        user.failed_login_count = count
        user.failed_login_window_started_at = window_start
        return False

    @staticmethod
    def reset(user: User) -> None:
        user.failed_login_count = 0
        user.failed_login_window_started_at = None
        user.locked_until = None
