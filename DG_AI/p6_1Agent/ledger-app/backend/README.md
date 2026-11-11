# 가계부 백엔드 (FastAPI)

기획서 `docs/planning/2026-11-06-가계부-앱.md`와 API 계약 `docs/api-contract.md`를 따릅니다.

## 구성

- 계층: `app/api`(라우터, 의존성, 쿠키) → `app/services`(규칙) → `app/repositories`(DB 접근) → `app/models`
- 순수 함수: `app/lib` (사용률, 월 범위, 알림 문구). 프레임워크에 의존하지 않습니다.
- 스키마: `app/schemas` (Pydantic v2, 입력 검증과 응답 형식)
- 마이그레이션: `migrations/` (Alembic). 스키마 변경은 여기서만 합니다 (NFR-23).

## 실행 준비

Python 3.13 기준으로 확인했습니다.

```powershell
cd ledger-app\backend
uv venv .venv --python 3.13
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
copy .env.example .env   # 필요한 값만 조정
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- 설정은 모두 `LEDGER_` 접두사 환경 변수입니다. 목록과 설명은 `.env.example`을 봅니다.
- 로컬 HTTP에서 세션 쿠키를 주고받으려면 `LEDGER_SESSION_COOKIE_SECURE=false`가 필요합니다. 운영에서는 `true`를 유지합니다.
- `alembic.ini`에는 한글 주석을 넣지 않습니다. Alembic이 Windows에서 cp949로 읽어 실패하기 때문입니다.

## 테스트

```powershell
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check app tests
.venv\Scripts\python.exe -m ruff format --check app tests
```

테스트 이름에는 기획서 FR, NFR, SC ID를 붙였습니다 (예: `test_FR02_five_failures_within_window_lock_the_account`).
시계는 `FakeClock`으로 바꿔 잠금 해제와 세션 만료를 검증합니다.

## 보안 요점

- 비밀번호: Argon2id (argon2-cffi 기본 파라미터). 로그인 실패는 항상 같은 문구로 응답합니다.
- 세션: 무작위 토큰을 HttpOnly 쿠키로 보내고, DB에는 SHA-256 해시만 저장합니다. 사용할 때마다 14일을 연장합니다.
- CSRF: POST, PUT, PATCH, DELETE는 `X-CSRF-Token` 헤더가 세션 토큰과 일치해야 합니다. 로그인과 가입은 세션 전이므로 JSON 본문만 받아 교차 사이트 폼 전송을 막습니다.
- 소유 격리: 모든 리포지토리 조회에 `user_id` 조건이 있고, 타인 리소스는 404입니다.
- 로그에는 요청 본문, 비밀번호, 세션 토큰, 거래 금액과 메모를 남기지 않습니다.
