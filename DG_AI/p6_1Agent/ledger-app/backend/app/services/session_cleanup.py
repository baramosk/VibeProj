"""만료 세션 정리 작업 (NFR-03, Q-F).

- 앱 시작 시 한 번 정리하고, 이후 session_cleanup_interval_seconds마다 정리합니다.
- 실패해도 앱은 계속 실행합니다. 오류 로그에는 예외 종류만 남기고 메시지는 남기지 않습니다 (NFR-25).
"""

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import sessionmaker

from app.core.clock import Clock
from app.core.config import Settings
from app.services.auth_service import AuthService

logger = logging.getLogger("ledger.session_cleanup")


def purge_expired_sessions_once(
    session_factory: sessionmaker,
    clock: Clock,
    settings: Settings,
) -> int:
    db = session_factory()
    try:
        removed = AuthService(db, clock, settings).purge_expired_sessions()
    finally:
        db.close()
    logger.info("expired sessions removed: %d", removed)
    return removed


def run_safely(task: Callable[[], int]) -> None:
    try:
        task()
    except Exception as exc:  # 정리 실패가 앱 실행을 막으면 안 됩니다.
        logger.error("session cleanup failed (%s)", type(exc).__name__)


async def run_periodically(task: Callable[[], None], interval_seconds: int) -> None:
    """interval_seconds마다 task를 실행합니다. 취소될 때까지 반복합니다."""
    while True:
        await asyncio.sleep(interval_seconds)
        await asyncio.to_thread(run_safely, task)
