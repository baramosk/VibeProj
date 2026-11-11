"""제품 규칙 상수 (기획서 FR 근거). 운영 중 바뀔 수 있는 값은 core/config.py의 Settings를 씁니다."""

from typing import Final

# FR-10: 금액은 원 단위 정수 1 ~ 999,999,999
AMOUNT_MIN: Final = 1
AMOUNT_MAX: Final = 999_999_999

# FR-10: 메모 최대 200자
MEMO_MAX_LENGTH: Final = 200

# FR-07: 카테고리 이름 1~20자
CATEGORY_NAME_MAX_LENGTH: Final = 20

# FR-01: 닉네임 (기획서에 길이 규칙이 없어 가정 값 1~20자로 둡니다)
NICKNAME_MAX_LENGTH: Final = 20

# FR-01: 비밀번호 8자 이상, 영문과 숫자 포함 (권장안), 최대 길이는 DoS 방지용 상한
PASSWORD_MIN_LENGTH: Final = 8
PASSWORD_MAX_LENGTH: Final = 128

# RFC 5321 기준 이메일 최대 길이
EMAIL_MAX_LENGTH: Final = 254

# FR-07: 카테고리 색상 팔레트 (선택 항목). 기본 카테고리 색상도 이 팔레트 안에서 정합니다.
CATEGORY_COLOR_PALETTE: Final = (
    "#ef4444",
    "#f97316",
    "#f59e0b",
    "#eab308",
    "#84cc16",
    "#22c55e",
    "#14b8a6",
    "#06b6d4",
    "#3b82f6",
    "#6366f1",
    "#a855f7",
    "#ec4899",
    "#64748b",
)
DEFAULT_CATEGORY_COLOR: Final = "#64748b"

# FR-06: 가입 시 복사되는 기본 카테고리 (이름, 유형, 색상)
DEFAULT_CATEGORIES: Final = (
    ("식비", "EXPENSE", "#f59e0b"),
    ("카페/간식", "EXPENSE", "#f97316"),
    ("교통", "EXPENSE", "#3b82f6"),
    ("주거/관리비", "EXPENSE", "#6366f1"),
    ("통신", "EXPENSE", "#06b6d4"),
    ("쇼핑", "EXPENSE", "#ec4899"),
    ("문화/여가", "EXPENSE", "#a855f7"),
    ("의료/건강", "EXPENSE", "#22c55e"),
    ("교육", "EXPENSE", "#14b8a6"),
    ("경조사", "EXPENSE", "#ef4444"),
    ("기타 지출", "EXPENSE", "#64748b"),
    ("급여", "INCOME", "#22c55e"),
    ("부수입", "INCOME", "#84cc16"),
    ("용돈", "INCOME", "#eab308"),
    ("기타 수입", "INCOME", "#64748b"),
)

# FR-14, FR-17: 추이 그래프 조회 기간 (개월)
TREND_MONTHS_ALLOWED: Final = (6, 12)
TREND_MONTHS_DEFAULT: Final = 12

# FR-11: 거래 목록 페이지 크기
PAGE_SIZE_DEFAULT: Final = 20
PAGE_SIZE_MAX: Final = 100

# 세션 쿠키의 CSRF 헤더 이름 (NFR-05, api-contract 공통 규칙)
CSRF_HEADER_NAME: Final = "X-CSRF-Token"

# 로그인 실패 메시지 (FR-02): 계정 존재 여부를 드러내지 않는 고정 문구
LOGIN_FAILED_MESSAGE: Final = "이메일 또는 비밀번호가 올바르지 않습니다."
