from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self._db.scalar(select(User).where(User.email == email))

    def add(self, user: User) -> None:
        self._db.add(user)

    def delete(self, user_id: int) -> None:
        self._db.execute(delete(User).where(User.id == user_id))
