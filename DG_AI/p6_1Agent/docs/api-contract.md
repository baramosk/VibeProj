# API 계약 (백엔드 ↔ 프런트엔드)

- 작성일: 2026-11-06
- 기준 기획서: `docs/planning/2026-11-06-가계부-앱.md`
- 백엔드: `ledger-app/backend` (FastAPI, Python)
- 프런트엔드: `ledger-app/frontend` (React + Vite)

이 문서는 두 쪽이 공유하는 계약입니다. 백엔드와 프런트엔드는 이 계약을 따르며, 바꿔야 하면 이 문서를 먼저 고치고 양쪽에 알립니다.

## 공통 규칙

- 기본 경로: `/api`
- 데이터 형식: JSON (`Content-Type: application/json`), 날짜는 `YYYY-MM-DD`, 월은 `YYYY-MM`
- 금액: 원 단위 정수 (`amount: number`, 소수 없음)
- 인증: HttpOnly 세션 쿠키. 로그인하지 않은 요청은 `401`
- CSRF (NFR-05): POST, PUT, PATCH, DELETE 요청에는 헤더 `X-CSRF-Token`이 필요합니다. 값은 로그인과 `GET /api/auth/me` 응답의 `csrf_token`입니다. 없거나 틀리면 `403`
- 오류 형식:
  ```json
  { "error": { "code": "VALIDATION_ERROR", "message": "사용자에게 보여줄 문장", "details": {} } }
  ```
  주요 `code`: `VALIDATION_ERROR`(400), `UNAUTHORIZED`(401), `FORBIDDEN`(403), `NOT_FOUND`(404), `CONFLICT`(409), `ACCOUNT_LOCKED`(423), `RATE_LIMITED`(429), `INTERNAL_ERROR`(500)
- 소유 격리: 모든 리소스는 로그인한 사용자 소유만 조회, 수정, 삭제할 수 있습니다. 다른 사용자의 리소스는 `404`로 응답합니다.

## 1. 인증 (FR-01~04)

| 메서드 | 경로 | 설명 | 요청 | 응답 |
|---|---|---|---|---|
| POST | `/api/auth/signup` | 회원가입 | `{ email, password, nickname }` | `201` `{ user, csrf_token }`, 세션 쿠키 설정 |
| POST | `/api/auth/login` | 로그인 | `{ email, password }` | `200` `{ user, csrf_token }`. 5회 실패 시 `423` `ACCOUNT_LOCKED` |
| POST | `/api/auth/logout` | 로그아웃 | 없음 | `204`, 세션 삭제 |
| GET | `/api/auth/me` | 현재 사용자 | 없음 | `200` `{ user, csrf_token }` |
| DELETE | `/api/auth/account` | 회원 탈퇴 | `{ password }` | `204`, 데이터 전부 삭제 |

`user`: `{ id, email, nickname, created_at }` (비밀번호 해시는 응답에 없음)

## 2. 카테고리 (FR-06~09)

| 메서드 | 경로 | 설명 | 요청 | 응답 |
|---|---|---|---|---|
| GET | `/api/categories` | 목록 | 쿼리: `type` (선택, `INCOME`/`EXPENSE`) | `200` `Category[]` |
| POST | `/api/categories` | 추가 | `{ name, type, color }` | `201` `Category` |
| PATCH | `/api/categories/{id}` | 이름, 색상 수정 | `{ name?, color? }` | `200` `Category` |
| DELETE | `/api/categories/{id}` | 삭제 (거래 이동 포함) | `?replacement_id=` 필수 | `204`. 같은 유형이 아니면 `400` |

`Category`: `{ id, name, type, color, is_default, created_at, transaction_count }`. `transaction_count`는 목록과 수정 응답에서 채워지며, 추가 응답에서는 `0`입니다 (Q-C).

기본 카테고리는 가입 시 자동 생성합니다 (FR-06). 예: 수입 (급여, 기타 수입), 지출 (식비, 교통, 주거, 쇼핑, 기타).

## 3. 거래 (FR-10~13)

| 메서드 | 경로 | 설명 | 요청 | 응답 |
|---|---|---|---|---|
| GET | `/api/transactions` | 목록 (필터) | 쿼리: `from`, `to`, `category_id`, `type`, `page`, `size` | `200` `{ items: Transaction[], total, page, size }` |
| POST | `/api/transactions` | 기록 | `{ type, amount, category_id, occurred_on, memo? }` | `201` `{ transaction, budget_status }` |
| PATCH | `/api/transactions/{id}` | 수정 | 위와 같은 필드 일부 | `200` `{ transaction, budget_status }` |
| DELETE | `/api/transactions/{id}` | 삭제 (영구) | 없음 | `200` `{ budget_status }` |

`Transaction`: `{ id, type, amount, category_id, category_name, occurred_on, memo, created_at, updated_at }`

`budget_status`: 거래 저장 후 영향받은 예산의 상태 목록. 흐름 1 (기획서 10.5) 참고.
`[{ budget_id, category_id, year_month, spent, amount, usage_percent, new_thresholds: [80 | 100] }]`

## 4. 리포트 (FR-14~17)

| 메서드 | 경로 | 설명 | 요청 | 응답 |
|---|---|---|---|---|
| GET | `/api/reports/monthly` | 월 요약과 카테고리별 지출 | 쿼리: `year_month` (필수) | `200` `MonthlyReport` |
| GET | `/api/reports/trend` | 최근 12개월 월별 지출 | 쿼리: `end` (선택, 기본 이번 달) | `200` `{ items: [{ year_month, expense }] }` |

`MonthlyReport`:
```json
{
  "year_month": "2026-11",
  "income_total": 3000000,
  "expense_total": 1200000,
  "balance": 1800000,
  "by_category": [
    { "category_id": 3, "name": "식비", "color": "#f59e0b", "amount": 400000, "ratio": 33.3 }
  ]
}
```

## 5. 예산 (FR-18~20)

| 메서드 | 경로 | 설명 | 요청 | 응답 |
|---|---|---|---|---|
| GET | `/api/budgets` | 월별 예산 목록과 사용률 | 쿼리: `year_month` (필수) | `200` `Budget[]` |
| POST | `/api/budgets` | 예산 설정 | `{ year_month, amount, category_id? }` (`category_id` 없으면 전체 지출) | `201` `Budget`. 중복은 `409` |
| PUT | `/api/budgets/{id}` | 금액 수정 | `{ amount }` | `200` `Budget` |
| DELETE | `/api/budgets/{id}` | 삭제 | 없음 | `204` |

`Budget`: `{ id, year_month, category_id, category_name, amount, spent, usage_percent, status }`
`status`: `NORMAL` (0~79%), `WARNING` (80~99%), `EXCEEDED` (100% 이상)

## 6. 알림 (FR-21~22)

| 메서드 | 경로 | 설명 | 요청 | 응답 |
|---|---|---|---|---|
| GET | `/api/notifications` | 목록 | 쿼리: `unread_only` (선택) | `200` `{ items: Notification[], unread_count }` |
| POST | `/api/notifications/{id}/read` | 읽음 처리 | 없음 | `200` `Notification` |

`Notification`: `{ id, budget_id, year_month, threshold_percent, message, is_read, created_at }`

## 상태 코드 요약

- 생성은 `201`, 본문 없는 삭제는 `204`
- 입력 검증 실패는 `400` (`details`에 필드별 메시지)
- 세션 없음은 `401`, CSRF 실패는 `403`, 자원 없음 또는 타인 자원은 `404`
- 중복 (이메일, 카테고리 이름, 월별 예산)은 `409`
- 속도 제한 초과는 `429` (`RATE_LIMITED`)이며, `Retry-After` 헤더와 `details.retry_after_seconds`로 대기 시간을 알립니다 (NFR-07)

## 구현 반영 변경 (2026-11-06)

백엔드 구현 과정에서 계약에 추가되거나 바뀐 항목입니다. 프런트엔드는 이 기준으로 연동합니다.

1. `POST /api/auth/signup`, `POST /api/auth/login`은 세션 전이라 CSRF 토큰이 없습니다. 대신 `Content-Type: application/json`이 아니면 `403`으로 막습니다.
2. `POST /api/transactions`의 `occurred_on`은 선택이며, 없으면 오늘(KST)입니다.
3. `GET /api/transactions`에 `sort` (`date_desc` 기본, `amount_desc`, `amount_asc`)를 추가했습니다. `category_id`는 반복 전달로 다중 선택을 지원합니다.
4. `GET /api/reports/trend`에 `months` (6 또는 12, 기본 12)를 추가했습니다.
5. `POST /api/notifications/read-all` (`204`)을 추가했습니다. 모두 읽음 처리입니다.
6. `POST /api/categories`의 `color`는 선택이며, 기본값은 `#64748b`입니다.
7. `DELETE /api/auth/account`에서 비밀번호가 틀리면 `401`이 아니라 `400` (`details.password`)입니다. `401`은 세션 만료로만 씁니다.
8. 전체 예산의 `category_name`은 `null`입니다. 예산 금액 상한은 999,999,999원입니다.
9. 예산 생성과 수정에서는 알림을 만들지 않고, 거래 저장, 수정, 삭제에서만 판정합니다.
10. 계약에 없는 오류 코드 `HTTP_ERROR`는 기타 HTTP 상태에 사용합니다.
11. 시각은 UTC ISO 8601 (`...Z`)로 응답합니다.
12. `/docs`(Swagger)는 기본적으로 비활성화되어 있습니다 (`LEDGER_DOCS_ENABLED`).

## 구현 반영 변경 (2026-11-13, 열린 질문 결정 반영)

13. `Category`에 `transaction_count`를 추가했습니다. 삭제 확인 창에서 옮겨질 거래 수로 씁니다 (Q-C).
14. 속도 제한 (NFR-07, Q-E): IP 단위, 고정 시간 창 (기본 60초). `POST /api/auth/login`, `POST /api/auth/signup`은 창당 10회, `POST`, `PATCH`, `DELETE /api/transactions`는 창당 60회를 넘으면 `429`입니다. 읽기 API는 제한하지 않습니다. 설정은 `LEDGER_RATE_LIMIT_*`입니다.
15. 만료 세션 정리 (NFR-03, Q-F): API 변경은 없습니다. 앱 시작 시와 `LEDGER_SESSION_CLEANUP_INTERVAL_SECONDS` 주기 (기본 24시간)로 만료 세션을 삭제합니다.
16. `FR-08` 카테고리 유형 변경은 MVP에서 제외합니다 (Q-B). 유형은 생성 후 고정입니다.

### 결정으로 닫힌 항목
- FR-08 카테고리 유형 변경: 제외 (Q-B)
- FR-09 삭제 전 거래 수 표시: `transaction_count`로 해결 (Q-C)
