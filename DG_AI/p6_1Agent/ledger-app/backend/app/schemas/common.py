"""공통 입력 검증 타입 (NFR-06: 서버에서 모든 입력을 다시 검증).

검증 메시지는 사용자에게 그대로 보여줄 한국어 문장입니다. 입력 값은 메시지에 넣지 않습니다.
"""

import re
from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    PlainSerializer,
    StrictInt,
)

from app.constants import (
    AMOUNT_MAX,
    AMOUNT_MIN,
    CATEGORY_COLOR_PALETTE,
    CATEGORY_NAME_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    MEMO_MAX_LENGTH,
    NICKNAME_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
)
from app.lib.dates import parse_year_month

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _strip_text(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > EMAIL_MAX_LENGTH or not _EMAIL_PATTERN.match(normalized):
        raise ValueError("올바른 이메일 형식이 아닙니다.")
    return normalized


def _check_password_policy(value: str) -> str:
    # FR-01 권장안: 영문과 숫자를 모두 포함
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("비밀번호에 영문과 숫자를 모두 포함해 주세요.")
    return value


def _check_year_month(value: str) -> str:
    try:
        return parse_year_month(value)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _clean_memo(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > MEMO_MAX_LENGTH:
        raise ValueError(f"메모는 {MEMO_MAX_LENGTH}자 이하로 입력해 주세요.")
    return stripped


def _check_color(value: str) -> str:
    if value not in CATEGORY_COLOR_PALETTE:
        raise ValueError("팔레트에 있는 색상을 선택해 주세요.")
    return value


def _to_utc_iso(value: datetime) -> str:
    return value.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")


# 이메일: 소문자 정규화 후 형식 검사 (FR-01)
NormalizedEmail = Annotated[str, Field(max_length=EMAIL_MAX_LENGTH), AfterValidator(_normalize_email)]

# 가입 비밀번호: 길이와 영문, 숫자 규칙 (FR-01). 로그인 입력에는 정책을 적용하지 않습니다.
SignupPassword = Annotated[
    str,
    Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH),
    AfterValidator(_check_password_policy),
]
LoginPassword = Annotated[str, Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)]

Nickname = Annotated[
    str,
    BeforeValidator(_strip_text),
    Field(min_length=1, max_length=NICKNAME_MAX_LENGTH),
]

CategoryName = Annotated[
    str,
    BeforeValidator(_strip_text),
    Field(min_length=1, max_length=CATEGORY_NAME_MAX_LENGTH),
]

CategoryColor = Annotated[str, AfterValidator(_check_color)]

# FR-10: 원 단위 정수만 허용. StrictInt로 소수점, 문자열 숫자, true/false를 거부합니다.
Amount = Annotated[StrictInt, Field(ge=AMOUNT_MIN, le=AMOUNT_MAX)]

PositiveId = Annotated[StrictInt, Field(ge=1)]

Memo = Annotated[str | None, BeforeValidator(_clean_memo)]

YearMonth = Annotated[str, AfterValidator(_check_year_month)]

UtcDateTime = Annotated[datetime, PlainSerializer(_to_utc_iso, return_type=str, when_used="json")]
