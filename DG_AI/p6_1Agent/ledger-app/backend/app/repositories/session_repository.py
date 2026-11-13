from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import AuthSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, token_hash: str) -> AuthSession | None:
        return self._db.get(AuthSession, token_hash)

    def add(self, session_row: AuthSession) -> None:
        self._db.add(session_row)

    def delete(self, token_hash: str) -> None:
        self._db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))

    def delete_for_user(self, user_id: int) -> None:
        self._db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))

    def delete_expired(self, now: datetime) -> int:
        """NFR-03 (Q-F): 만료된 세션을 지우고 지운 개수를 돌려줍니다."""
        result = self._db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
        return int(result.rowcount or 0)
