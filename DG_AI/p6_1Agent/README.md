# 개인 가계부 앱

로그인한 개인이 수입과 지출을 기록하고, 카테고리로 분류하고, 월별 지출을 그래프로 보고, 예산을 초과하면 알림을 받는 개인용 가계부 웹 앱입니다.

- 기획서: [`docs/planning/2026-11-13-personal-ledger-app.md`](docs/planning/2026-11-13-personal-ledger-app.md) (요구 사항, 설계, 범위)
- 초기 기획서: [`docs/planning/2026-11-06-가계부-앱.md`](docs/planning/2026-11-06-가계부-앱.md)
- API 계약: [`docs/api-contract.md`](docs/api-contract.md)
- 데이터 흐름과 완성도: [`docs/data-flow.md`](docs/data-flow.md)
- 열린 질문 결정 기록: [`docs/decisions/2026-11-13-open-questions.md`](docs/decisions/2026-11-13-open-questions.md)

## 주요 기능

| 영역 | 기능 |
|---|---|
| 회원 | 가입, 로그인, 로그아웃, 회원 탈퇴 (비밀번호 확인 후 모든 데이터 삭제) |
| 거래 | 수입과 지출 기록, 목록 조회 (기간, 유형, 카테고리 필터, 정렬, 페이지), 수정, 삭제 |
| 카테고리 | 기본 카테고리 제공 (가입 시 복사), 추가, 이름과 색상 수정, 삭제 시 거래를 다른 카테고리로 이동 |
| 리포트 | 월 수입, 지출, 잔액 요약, 카테고리별 지출 도넛 차트, 최근 12개월 지출 추이 막대 차트 (차트마다 같은 내용의 표 제공) |
| 예산 | 전체 지출 또는 카테고리별 월 예산 설정, 사용률 표시 |
| 알림 | 예산 사용률 80%, 100% 도달 시 인앱 알림 생성 (월별 임계치당 1건), 읽음 처리, 모두 읽음 |

## 기술 스택

- **백엔드:** Python 3.13, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, SQLite, pytest, ruff
- **프런트엔드:** React 19, Vite 7, TypeScript, react-router 7, Recharts 3, vitest, msw, ESLint
- **인증:** 이메일과 비밀번호 (Argon2id 해시), HttpOnly 세션 쿠키, CSRF 헤더 (`X-CSRF-Token`)

## 폴더 구조

```text
p6_1Agent/
├─ README.md                       이 문서
├─ docs/
│  ├─ planning/                    기획서 (날짜별 파일)
│  ├─ decisions/                   설계 결정 기록
│  ├─ api-contract.md              백엔드와 프런트엔드 API 계약
│  └─ data-flow.md                 데이터 흐름과 완성도
├─ .claude/                        에이전트와 명령 정의 (개발 도구용)
└─ ledger-app/
   ├─ backend/
   │  ├─ app/
   │  │  ├─ main.py                앱 생성, 라우터 등록, 시작 시 세션 정리
   │  │  ├─ constants.py           기본 카테고리, 색상 팔레트, 페이지 크기 등 제품 상수
   │  │  ├─ api/                   라우터 (routes/), 의존성 (deps.py), 쿠키 설정
   │  │  ├─ core/                  설정, 보안 해시, 오류 형식, 보안 헤더, 속도 제한
   │  │  ├─ db/                    SQLAlchemy 베이스와 세션 팩토리
   │  │  ├─ models/                DB 모델 (사용자, 세션, 카테고리, 거래, 예산, 알림)
   │  │  ├─ schemas/               요청과 응답 스키마 (입력 검증 포함)
   │  │  ├─ repositories/          DB 접근 (모든 조회에 user_id 조건)
   │  │  ├─ services/              업무 규칙 (인증, 카테고리, 거래, 예산, 알림, 리포트, 세션 정리)
   │  │  └─ lib/                   순수 계산 함수 (금액과 사용률, 날짜와 월 범위, 알림 문구)
   │  ├─ migrations/               Alembic 마이그레이션 (스키마 변경은 여기서만)
   │  ├─ scripts/seed_perf.py      성능 측정용 거래 10,000건 생성 (개발 전용)
   │  ├─ tests/                    단위 테스트 (unit/), API 연동 테스트 (integration/)
   │  ├─ .env.example              환경 변수 예시
   │  ├─ alembic.ini, pyproject.toml, requirements.txt
   │  └─ README.md                 백엔드 세부 안내
   └─ frontend/
      ├─ src/
      │  ├─ api/                   HTTP 클라이언트, 엔드포인트, 응답 타입
      │  ├─ auth/                  로그인 상태 관리
      │  ├─ components/            공용 UI (ui/), 차트 (charts/), 레이아웃 (layout/)
      │  ├─ hooks/                 화면용 데이터 훅 (거래, 예산, 카테고리, 알림, 리포트)
      │  ├─ lib/                   금액, 날짜, 검증 등 순수 함수
      │  ├─ pages/                 화면 (대시보드, 거래, 예산, 카테고리, 알림, 설정, 로그인, 가입)
      │  ├─ styles/                디자인 토큰과 스타일
      │  └─ test/                  테스트 도구 (msw 목 서버, 픽스처)
      ├─ vite.config.ts            개발 서버와 /api 프록시
      └─ package.json
```

## 설치와 실행

요구 사항: Windows PowerShell 기준으로 확인했습니다. Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js (npm 포함)가 필요합니다.

### 1. 백엔드 (포트 8000)

```powershell
cd ledger-app\backend

# 최초 1회: 가상환경과 의존성
uv venv .venv --python 3.13
uv pip install --python .venv\Scripts\python.exe -r requirements.txt

# 최초 1회: 설정 파일 (필요한 값만 수정)
copy .env.example .env

# DB 스키마 적용 (최초 1회, 스키마가 바뀐 뒤에도 실행)
.venv\Scripts\python.exe -m alembic upgrade head

# 서버 실행
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

로컬 HTTP에서 로그인 쿠키가 동작하려면 `.env`에 `LEDGER_SESSION_COOKIE_SECURE=false`를 넣습니다. 기본값은 `true`(HTTPS 전용)입니다.

### 2. 프런트엔드 (포트 5173)

백엔드와 다른 터미널에서 실행합니다.

```powershell
cd ledger-app\frontend

# 최초 1회
npm install

# 개발 서버
npm run dev
```

브라우저에서 `http://localhost:5173`을 엽니다. `/api` 요청은 Vite가 `http://localhost:8000`으로 전달합니다. 백엔드 주소를 바꾸려면 `VITE_API_PROXY_TARGET` 환경 변수를 설정합니다.

### 3. 성능 측정 데이터 (선택)

거래 10,000건이 들어 있는 별도 DB를 만듭니다. 운영 DB(`ledger.db`)와 분리되며, 이 이름은 스크립트가 거부합니다.

```powershell
cd ledger-app\backend
.venv\Scripts\python.exe scripts\seed_perf.py --db perf.db --reset
```

계정은 `perf@example.com` / `perf-only-1234`입니다. 개발 전용 값이므로 운영에서 쓰지 마세요. 이 DB로 서버를 띄우려면 `LEDGER_DATABASE_URL=sqlite:///./perf.db`를 설정합니다.

## 사용 방법

1. **가입:** `/signup`에서 이메일, 비밀번호 (8자 이상, 영문과 숫자 포함), 닉네임을 입력합니다. 가입과 동시에 로그인되고 기본 카테고리가 만들어집니다.
2. **거래 기록:** `/transactions`에서 유형(수입/지출), 금액(원 단위 정수), 날짜, 카테고리, 메모를 입력합니다. 저장하면 해당 예산의 사용률이 갱신되고, 임계치를 넘으면 알림이 생깁니다.
3. **카테고리 관리:** `/categories`에서 추가, 이름과 색상 수정을 합니다. 삭제하면 거래를 같은 유형의 다른 카테고리로 옮긴 뒤 삭제하며, 확인 창에 옮겨질 거래 수가 표시됩니다.
4. **예산 설정:** `/budgets`에서 월과 대상(전체 지출 또는 지출 카테고리)을 고르고 금액을 입력합니다. 같은 월, 같은 대상의 예산은 하나만 만들 수 있습니다.
5. **월 리포트:** `/dashboard`에서 월을 옮기며 수입, 지출, 잔액, 카테고리별 비율, 12개월 추이를 봅니다.
6. **알림:** `/notifications`에서 예산 알림을 확인하고 읽음 처리합니다. 헤더 아이콘에 읽지 않은 개수가 표시됩니다.
7. **설정:** `/settings`에서 로그아웃하거나 회원 탈퇴를 합니다. 탈퇴하면 모든 데이터가 즉시 삭제되고 복구할 수 없습니다.

금액 규칙: 1원 이상 999,999,999원 이하의 정수만 입력할 수 있습니다. 날짜는 한국 시간(Asia/Seoul) 기준이며 미래 날짜는 입력할 수 없습니다.

## 배포

**배포 위치와 호스팅 서비스는 아직 정하지 않았습니다** (열린 질문 Q-J). 도입 직전에 요금과 무료 한도를 공식 문서로 확인한 뒤 결정합니다. 아래는 어떤 서비스를 고르든 필요한 절차입니다.

### 구성

- 프런트엔드는 정적 파일 (`npm run build` → `frontend/dist/`)입니다.
- 백엔드는 uvicorn으로 실행하는 FastAPI 서버입니다.
- 두 가지를 같은 도메인 아래에 두고, 리버스 프록시가 `/api/*`를 백엔드로, 나머지를 정적 파일로 보내는 구성을 권장합니다. 같은 출처라서 쿠키와 CSRF 설정이 단순해집니다.

### 빌드

```powershell
cd ledger-app\frontend
npm ci
npm run build          # 타입 검사 후 frontend\dist\ 생성

cd ..\backend
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe -m alembic upgrade head
```

### 운영 환경 변수 (`LEDGER_` 접두사)

| 변수 | 운영 값 | 설명 |
|---|---|---|
| `LEDGER_DATABASE_URL` | 영구 저장소 경로 | 기본은 `sqlite:///./ledger.db`. 백업 대상입니다 |
| `LEDGER_SESSION_COOKIE_SECURE` | `true` | HTTPS에서만 쿠키 전송 (NFR-02) |
| `LEDGER_HSTS_ENABLED` | `true` | HTTPS 배포에서만 HSTS 헤더 (NFR-08) |
| `LEDGER_CORS_ORIGINS` | 실제 프런트엔드 출처 | 같은 도메인 프록시를 쓰면 필요성이 줄어듭니다 |
| `LEDGER_DOCS_ENABLED` | `false` | Swagger 문서 비활성화 |
| `LEDGER_RATE_LIMIT_ENABLED` | `true` | 로그인, 가입, 거래 쓰기 속도 제한 (NFR-07) |
| `LEDGER_SESSION_TTL_DAYS` | `14` | 세션 미사용 만료 기간 |

전체 목록은 `ledger-app/backend/.env.example`에 있습니다. 실제 값이 든 `.env`는 커밋하지 않습니다.

### 실행

```bash
cd ledger-app/backend
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

- **워커는 1개로 유지합니다.** 속도 제한이 프로세스 메모리에 있어서, 워커가 여러 개면 제한이 나뉘어 동작합니다.
- 백엔드는 `127.0.0.1`에만 열고, 외부 접근은 리버스 프록시만 받도록 합니다.
- 리버스 프록시 뒤에서는 실제 클라이언트 IP를 전달받도록 설정해야 속도 제한이 사용자 단위로 동작합니다. 현재 코드는 직접 연결된 IP만 봅니다.

### 배포 전 체크리스트

- [ ] HTTPS 적용, `LEDGER_SESSION_COOKIE_SECURE=true`, `LEDGER_HSTS_ENABLED=true` (NFR-02, NFR-08)
- [ ] 보안 헤더 확인: CSP, `X-Frame-Options`, `Cache-Control: no-store` 응답 헤더 점검 (NFR-08)
- [ ] 개인정보 처리방침과 가입 동의 문구 준비 (NFR-12). 공개 배포 시 필수입니다
- [ ] SQLite 파일 일 1회 백업, 7일 보관 (NFR-21). 백업 보관 기간을 개인정보 정책에 명시 (NFR-11)
- [ ] 로그에 거래 금액, 메모, 비밀번호, 세션 토큰이 없는지 점검 (NFR-10, NFR-25)
- [ ] 리버스 프록시의 클라이언트 IP 설정 확인 (속도 제한)
- [ ] `/docs`, `/openapi.json` 비활성화 확인
- [ ] Argon2 파라미터 리뷰 (NFR-01)
- [ ] 배포 후 가입, 거래, 알림, 탈퇴 흐름을 실제 도메인에서 한 번 확인

## 개발과 테스트

```powershell
# 백엔드
cd ledger-app\backend
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check app tests scripts

# 프런트엔드
cd ledger-app\frontend
npm run typecheck
npm run lint
npm test
```

- 백엔드 테스트 이름에는 기획서 ID(FR, NFR, SC)를 붙였습니다.
- 시계는 `FakeClock`으로 바꿔 잠금 해제와 세션 만료를 검증합니다.
- 프런트엔드 화면 테스트는 msw로 API 응답을 흉내 냅니다.

## 알려진 제한

- **화면 클릭 확인 미수행:** 가입부터 탈퇴까지의 흐름은 Vite 프록시를 거친 API 수준에서만 확인했습니다. 브라우저에서 화면을 직접 누르는 확인은 아직 하지 않았습니다.
- **속도 제한은 메모리 기반:** 프로세스가 여러 개이거나 재시작되면 제한 카운트가 공유되거나 초기화됩니다.
- **계정 존재 노출:** 잠금 응답(423)과 중복 가입 응답(409)으로 계정 존재 여부가 드러납니다. 개인용 MVP에서 허용한 트레이드오프입니다 (Q-G).
- **SQLite 동시 쓰기:** 여러 사용자가 동시에 쓰는 환경에는 적합하지 않습니다. 다중 사용자 운영 시 PostgreSQL 전환을 검토합니다.
- **반응형과 접근성:** 375px과 1280px 폭에서 확인했습니다. 키보드만으로의 전체 조작과 명도 대비는 아직 자동 점검하지 않았습니다 (NFR-16, NFR-18).

## 범위 밖 (MVP에서 하지 않는 것)

비밀번호 재설정, 이메일과 푸시 알림, 소셜 로그인, 거래 검색, CSV 내보내기, 반복 거래, 은행 연동, 다중 통화, 가족 공유.
이후 단계 항목은 기획서 4.6절과 7.2절에 있습니다.
