"""환경 변수 기반 설정 (LEDGER_ 접두사).

값이 바뀔 수 있는 항목(DB 경로, 세션 기간, 잠금 정책, 임계치, CORS 출처)은 코드에 두지 않고
이 클래스로 외부화합니다. 비밀 값은 기본값을 두지 않습니다.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEDGER_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./ledger.db"

    # NFR-03: 세션 유효 기간 (미사용 시 만료, 사용할 때마다 연장)
    session_ttl_days: int = Field(default=14, ge=1, le=90)
    session_cookie_name: str = "ledger_session"
    # NFR-02: 배포 환경에서는 true. 로컬 HTTP 개발에서만 false
    session_cookie_secure: bool = True

    # FR-02: 실패 횟수 잠금 정책
    login_max_failures: int = Field(default=5, ge=1)
    login_failure_window_minutes: int = Field(default=10, ge=1)
    login_lock_minutes: int = Field(default=15, ge=1)

    # FR-20, FR-21: 예산 임계치 (Q-09), 설정으로 단계 추가 가능
    budget_alert_thresholds: list[int] = Field(default=[80, 100])

    cors_origins: list[str] = Field(default=["http://localhost:5173"])
    # NFR-08: HTTPS 배포에서만 HSTS 헤더를 내보냅니다
    hsts_enabled: bool = False
    # 개발 중 /docs(Swagger UI)를 켭니다. 기본은 끔 (CSP와 충돌하고 API 구조를 노출하지 않기 위함)
    docs_enabled: bool = False

    @field_validator("budget_alert_thresholds")
    @classmethod
    def _validate_thresholds(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("임계치는 하나 이상이어야 합니다.")
        if any(t < 1 or t > 100 for t in value):
            raise ValueError("임계치는 1~100 사이여야 합니다.")
        return sorted(set(value))


@lru_cache
def get_settings() -> Settings:
    return Settings()
