"""속도 제한 단위 테스트 (NFR-07, Q-E)."""

from app.core.rate_limit import RateLimiter


class _Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_allows_up_to_limit_then_blocks():
    limiter = RateLimiter(now=_Clock())
    results = [limiter.hit("k", limit=3, window_seconds=60).allowed for _ in range(4)]
    assert results == [True, True, True, False]


def test_blocked_response_reports_retry_after_within_window():
    clock = _Clock()
    limiter = RateLimiter(now=clock)
    for _ in range(2):
        limiter.hit("k", limit=2, window_seconds=60)
    clock.t = 20.0
    decision = limiter.hit("k", limit=2, window_seconds=60)
    assert decision.allowed is False
    assert 1 <= decision.retry_after_seconds <= 60


def test_window_resets_after_it_elapses():
    clock = _Clock()
    limiter = RateLimiter(now=clock)
    limiter.hit("k", limit=1, window_seconds=60)
    assert limiter.hit("k", limit=1, window_seconds=60).allowed is False
    clock.t = 60.0
    assert limiter.hit("k", limit=1, window_seconds=60).allowed is True


def test_keys_are_independent():
    limiter = RateLimiter(now=_Clock())
    assert limiter.hit("a", limit=1, window_seconds=60).allowed is True
    assert limiter.hit("b", limit=1, window_seconds=60).allowed is True
    assert limiter.hit("a", limit=1, window_seconds=60).allowed is False
