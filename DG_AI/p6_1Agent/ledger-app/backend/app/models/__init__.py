"""모든 모델을 import해 Base.metadata에 등록합니다 (Alembic 자동 생성과 create_all에 필요)."""

from app.models.auth_session import AuthSession
from app.models.budget import Budget
from app.models.category import Category
from app.models.notification import Notification
from app.models.transaction import Transaction
from app.models.user import User

__all__ = ["AuthSession", "Budget", "Category", "Notification", "Transaction", "User"]
