"""요청 속도 제한 (NFR-07, Q-E).

- 고정 시간 창(fixed window) 방식입니다. 키 (예: "auth:203.0.113.5") 하나당 창 하나를 씁니다.
- 메모리에만 기록하므로 프로세스가 하나인 개인용 배포를 가정합니다.
  여러 프로세스로 운영하면 Redis 같은 공유 저장소가 필요합니다.
- 클라이언트 키는 직접 연결된 IP입니다.
  리버스 프록시 뒤에 둘 때는 프록시가 넘기는 IP를 신뢰하도록 따로 설정해야 합니다.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

# 메모리 보호: 기록된 키가 이 수를 넘으면 만료된 창을 정리합니다.
_PRUNE_THRESHOLD = 10_000


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class RateLimiter:
    def __init__(self, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._lock = threading.Lock()
        # key -> (창 시작 시각, 창 안의 요청 수)
        self._windows: dict[str, tuple[float, int]] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = self._now()
        with self._lock:
            if len(self._windows) > _PRUNE_THRESHOLD:
                self._prune(now, window_seconds)

            started, count = self._windows.get(key, (now, 0))
            if now - started >= window_seconds:
                started, count = now, 0

            if count >= limit:
                retry_after = max(1, int(window_seconds - (now - started)) + 1)
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

            self._windows[key] = (started, count + 1)
            return RateLimitDecision(allowed=True, retry_after_seconds=0)

    def _prune(self, now: float, window_seconds: int) -> None:
        expired = [key for key, (started, _) in self._windows.items() if now - started >= window_seconds]
        for key in expired:
            del self._windows[key]
