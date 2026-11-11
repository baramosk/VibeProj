"""인증 서비스: 가입, 로그인, 세션 인증, 로그아웃, 탈퇴 (FR-01~04, NFR-02, NFR-03, NFR-05)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.constants import LOGIN_FAILED_MESSAGE
from app.core.clock import Clock
from app.core.config import Settings
from app.core.errors import AccountLockedError, ConflictError, UnauthorizedError, ValidationFailed
from app.core.security import (
    burn_password_check,
    generate_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.models import AuthSession, User
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.category_service import build_default_categories
from app.services.common import commit_or_conflict
from app.services.login_guard import LoginGuard

ACCOUNT_LOCKED_MESSAGE = "로그인 실패가 반복되어 계정이 잠겼습니다. 잠시 후 다시 시도해 주세요."
SESSION_EXPIRED_MESSAGE = "세션이 만료되었습니다. 다시 로그인해 주세요."
LOGIN_REQUIRED_MESSAGE = "로그인이 필요합니다."
EMAIL_TAKEN_MESSAGE = "이미 가입된 이메일입니다."


@dataclass(frozen=True)
class IssuedSession:
    user: User
    raw_token: str
    csrf_token: str


@dataclass(frozen=True)
class SessionContext:
    user_id: int
    csrf_token: str
    token_hash: str


class AuthService:
    def __init__(self, db: Session, clock: Clock, settings: Settings) -> None:
        self._db = db
        self._clock = clock
        self._session_ttl = timedelta(days=settings.session_ttl_days)
        self._guard = LoginGuard(settings)
        self._users = UserRepository(db)
        self._sessions = SessionRepository(db)
        self._categories = CategoryRepository(db)
        self._transactions = TransactionRepository(db)
        self._budgets = BudgetRepository(db)
        self._notifications = NotificationRepository(db)

    def signup(self, email: str, password: str, nickname: str) -> IssuedSession:
        now = self._clock.now()
        if self._users.get_by_email(email) is not None:
            raise ConflictError(EMAIL_TAKEN_MESSAGE, {"email": EMAIL_TAKEN_MESSAGE})

        user = User(
            email=email,
            password_hash=hash_password(password),
            nickname=nickname,
            failed_login_count=0,
            created_at=now,
            updated_at=now,
        )
        self._users.add(user)
        self._db.flush()
        for category in build_default_categories(user.id, now):
            self._categories.add(category)

        issued = self._issue_session(user, now)
        commit_or_conflict(self._db, EMAIL_TAKEN_MESSAGE, {"email": EMAIL_TAKEN_MESSAGE})
        return issued

    def login(self, email: str, password: str) -> IssuedSession:
        now = self._clock.now()
        user = self._users.get_by_email(email)
        if user is None:
            # 존재하지 않는 계정도 같은 시간만큼 해시를 계산해 응답 시간으로 계정 존재를 알 수 없게 합니다.
            burn_password_check(password)
            raise UnauthorizedError(LOGIN_FAILED_MESSAGE)

        remaining = self._guard.remaining_lock_seconds(user, now)
        if remaining is not None:
            raise AccountLockedError(ACCOUNT_LOCKED_MESSAGE, {"retry_after_seconds": remaining})

        if not verify_password(user.password_hash, password):
            locked_now = self._guard.record_failure(user, now)
            self._db.commit()
            if locked_now:
                raise AccountLockedError(
                    ACCOUNT_LOCKED_MESSAGE, {"retry_after_seconds": self._guard.lock_seconds}
                )
            raise UnauthorizedError(LOGIN_FAILED_MESSAGE)

        self._guard.reset(user)
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)
        issued = self._issue_session(user, now)
        self._db.commit()
        return issued

    def authenticate(self, raw_token: str | None) -> SessionContext:
        """쿠키의 원본 토큰을 검증합니다. 사용할 때마다 만료 시각을 연장합니다 (미사용 시 만료, NFR-03)."""
        if not raw_token:
            raise UnauthorizedError(LOGIN_REQUIRED_MESSAGE)

        now = self._clock.now()
        token_hash = hash_token(raw_token)
        row = self._sessions.get(token_hash)
        if row is None:
            raise UnauthorizedError(LOGIN_REQUIRED_MESSAGE)
        if row.expires_at <= now:
            self._sessions.delete(token_hash)
            self._db.commit()
            raise UnauthorizedError(SESSION_EXPIRED_MESSAGE)

        row.expires_at = now + self._session_ttl
        self._db.commit()
        return SessionContext(user_id=row.user_id, csrf_token=row.csrf_token, token_hash=token_hash)

    def get_user(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError(LOGIN_REQUIRED_MESSAGE)
        return user

    def logout(self, token_hash: str) -> None:
        self._sessions.delete(token_hash)
        self._db.commit()

    def delete_account(self, user_id: int, password: str) -> None:
        """FR-04, 흐름 5: 비밀번호 확인 후 사용자 데이터 전부를 하나의 트랜잭션으로 삭제합니다."""
        user = self.get_user(user_id)
        if not verify_password(user.password_hash, password):
            raise ValidationFailed(
                "비밀번호가 올바르지 않습니다.", {"password": "비밀번호가 올바르지 않습니다."}
            )
        try:
            self._notifications.delete_all_for_user(user_id)
            self._budgets.delete_all_for_user(user_id)
            self._transactions.delete_all_for_user(user_id)
            self._categories.delete_all_for_user(user_id)
            self._sessions.delete_for_user(user_id)
            self._users.delete(user_id)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def _issue_session(self, user: User, now: datetime) -> IssuedSession:
        raw_token = generate_token()
        csrf_token = generate_token()
        self._sessions.add(
            AuthSession(
                token_hash=hash_token(raw_token),
                user_id=user.id,
                csrf_token=csrf_token,
                created_at=now,
                expires_at=now + self._session_ttl,
            )
        )
        return IssuedSession(user=user, raw_token=raw_token, csrf_token=csrf_token)
