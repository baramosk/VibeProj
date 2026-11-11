# 미니 쇼핑몰 백엔드 분석 보고서

- 대상: `p5_1Shopping` (Python 표준 라이브러리만 사용)
- 작성 목적: 프로젝트 구조, 핵심 클래스의 역할, 실행 흐름, 개선점과 취약점을 한 곳에 정리

---

## 1. 프로젝트 구조

```
p5_1Shopping/
├── main.py                       ← 진입점 (서버 실행)
├── CLAUDE.md                     ← Claude Code용 프로젝트 지침
├── ProjectAnalyze.md             ← 이 보고서
├── .claude/
│   ├── settings.json             ← PostToolUse 훅 설정
│   ├── hooks/py_compile_check.py ← .py 편집 후 문법 검사
│   └── skills/verify/SKILL.md    ← /verify (테스트 실행 스킬)
├── minishop/
│   ├── __init__.py               ← 패키지 표시
│   ├── store.py                  ← 도메인 로직과 데이터 저장
│   ├── server.py                 ← HTTP 서버와 API 라우팅
│   ├── multipart.py              ← multipart/form-data 파서
│   └── static/index.html         ← 프론트엔드 단일 페이지
├── tests/test_minishop.py        ← 단위 + HTTP 통합 테스트 (23개)
└── uploads/                      ← 업로드된 프로필 사진 (런타임 데이터)
```

| 파일 | 역할 |
|---|---|
| `main.py` | 인자를 파싱하고 `Store`를 만든 뒤 `run()`으로 서버를 시작합니다. |
| `minishop/store.py` | 상품, 사용자, 장바구니, 주문, 결제 시뮬레이션, 파일 저장을 담당합니다. 상태는 메모리에 있습니다. |
| `minishop/server.py` | `ShopHandler`가 요청을 라우팅하고, `Store`를 호출한 뒤 JSON이나 파일로 응답합니다. |
| `minishop/multipart.py` | 업로드 본문을 필드 단위로 분해합니다. `cgi`를 쓰지 않고 직접 구현했습니다. |
| `minishop/static/index.html` | 상품, 장바구니, 주문, 프로필 화면과 `fetch` 호출을 담당합니다. |
| `tests/test_minishop.py` | `Store` 단위 테스트와 실제 서버를 띄우는 HTTP 테스트입니다. |

---

## 2. 진입점

**주 진입점은 `main.py:18`의 `main()`입니다.**

```
python main.py
 → main()                        main.py:18
 → Store(args.uploads)           store.py:115  (Store.__init__)
 → run(store, host, port)        server.py:170
 → create_server()               server.py:165 → ShopHandler 바인딩
 → serve_forever()               요청마다 ShopHandler._handle() 실행
```

테스트 진입점은 `python -m unittest discover -s tests`입니다.

---

## 3. 핵심 클래스와 함수

### 3.1 `Store` (`store.py`)
모든 비즈니스 로직을 담은 중심 클래스입니다. `threading.RLock`으로 상태를 보호합니다.

| 메서드 | 입력 | 출력 / 동작 |
|---|---|---|
| `create_user(name)` | 닉네임 | `{id, name, avatar_url, token}`. 토큰을 발급하고 빈 장바구니를 만듭니다. |
| `authenticate(token)` | Bearer 토큰 | `user_id`. 없으면 `ShopError(401)`. |
| `list_products()` | 없음 | `[{id, name, price, stock}]` |
| `add_to_cart(uid, pid, qty)` | 사용자, 상품, 수량 | `{items, total}`. 재고와 1회 최대 99개를 검사합니다. |
| `remove_from_cart(uid, pid)` | 사용자, 상품 | 갱신된 장바구니 |
| `create_order(uid, method)` | 사용자, 결제 수단 | 주문 dict. 장바구니 확인 → 재고 확인 → 결제 → 재고 차감 → 장바구니 비우기. |
| `save_avatar(uid, filename, data)` | 사용자, 원본 파일명, 바이트 | 갱신된 사용자 dict. 확장자, 크기, 매직 바이트를 검사하고 중복을 피해 저장합니다. |
| `read_avatar(name)` | 저장된 파일명 | `(bytes, mime)`. 파일명 정규식 검사로 경로 탈출을 막습니다. |
| `_write_unique(stem, ext, data)` | 기본 이름, 확장자, 바이트 | 저장된 파일명. `"xb"` 모드로 덮어쓰기를 막고, 충돌하면 `_타임스탬프`를 붙입니다. |

### 3.2 `PaymentGateway` (`store.py`)
- `charge(amount, method)`: `limit`(기본 1,000,000원)을 넘으면 `ShopError(402)`. 승인되면 `{method, amount, transaction_id, status}`를 반환합니다.

### 3.3 `ShopError` (`store.py`)
- `(status, message)`를 담는 예외입니다. `ShopHandler`가 잡아 `{"error": message}` JSON으로 바꿉니다. 도메인과 HTTP를 잇는 연결점입니다.

### 3.4 `check_extension`, `detect_image` (`store.py`)
- `check_extension(filename)`: 위험한 확장자면 400, `.png`/`.jpg`/`.jpeg`가 아니면 415를 던집니다.
- `detect_image(data)`: 실제 내용의 매직 바이트가 PNG/JPEG인지 보고 확장자를 반환합니다. 아니면 `None`입니다.

### 3.5 `ShopHandler` (`server.py`)
`BaseHTTPRequestHandler`를 상속한 요청 처리기입니다.

- `_handle(method)` (server.py:44): 최상위 진입점입니다. `/`는 HTML, `/uploads/avatars/*`는 파일, `/api/*`는 `_route_api`로 보냅니다.
- `_route_api(method, path)` (server.py:63): 경로와 메서드로 분기해 `Store` 메서드를 호출합니다.
- `_auth()` (server.py:113): `Authorization: Bearer` 헤더를 파싱해 `user_id`를 얻습니다.
- `_read_body(limit)` (server.py:119): `Content-Length`를 먼저 검사합니다. 제한을 넘으면 본문을 읽지 않고 413을 반환합니다.
- `_read_json()` (server.py:134): JSON 객체만 허용합니다.
- `_upload_avatar(uid)` (server.py:95): 본인 확인 → multipart 확인 → 본문 읽기 → `parse_multipart` → `save_avatar`.

### 3.6 `parse_multipart(body, content_type)` (`multipart.py:28`)
- 입력: 원시 바이트와 `Content-Type` 헤더
- 출력: `list[Part]`. `Part`는 `name`, `filename`, `content_type`, `data`를 가진 dataclass입니다.

---

## 4. 실행 흐름 (Call Stack / Flow)

### 4.1 서버 시작
```
main.py:main
 ├─ argparse                     --host, --port, --uploads
 ├─ logging.basicConfig
 ├─ Store.__init__(upload_dir)
 │    ├─ SEED_PRODUCTS → self._products (5개 상품)
 │    ├─ PaymentGateway() 기본 생성
 │    └─ os.makedirs(uploads/)
 └─ server.run(store, host, port)
      ├─ create_server → type("BoundShopHandler", (ShopHandler,), {"store": store})
      │                  _ShopServer((host, port), handler)
      └─ serve_forever()          ← 요청마다 스레드 생성 (ThreadingHTTPServer)
```

### 4.2 브라우저 접속 (`GET /`)
```
브라우저 → GET /
 → ShopHandler._handle("GET")
   → path == "/" → _read_static("index.html") → _send_bytes(200, html)
```
브라우저는 HTML을 받은 뒤 JavaScript를 실행합니다. 로그인 전이라 `#login-box`만 보입니다. `localStorage`에 토큰이 있으면 `GET /api/me`로 세션을 복원하고, 없으면 상품 목록을 불러옵니다(`showView("products")` → `loadProducts()` → `GET /api/products`).

### 4.3 사용자 등록 / "시작하기" (`POST /api/users`)
```
[브라우저] #login-form submit
 → api("POST", "/api/users", {name})
 → fetch
[서버] _handle → _route_api
 → _read_json()                    {"name": "..."}
 → Store.create_user(name)
     ├─ 이름 검사 (1~30자)
     ├─ uid 발급, token = secrets.token_urlsafe(24)
     ├─ _users[uid], _tokens[token] = uid, _carts[uid] = {}
     └─ {id, name, avatar_url, token}
 → 201 JSON
[브라우저]
 → localStorage에 token 저장
 → GET /api/me → me 갱신 → renderAuth() → showView("products")
```

### 4.4 상품 담기 (`POST /api/cart`)
```
[브라우저] data-add 버튼 click (이벤트 위임)
 → api("POST", "/api/cart", {product_id, quantity:1})
[서버] _route_api
 → _auth()                         Bearer 토큰 → uid
 → _read_json()
 → Store.add_to_cart(uid, pid, qty)
     ├─ _as_int 검사, 1~99 범위 검사
     ├─ _require_product(pid)
     ├─ new_qty = 기존 수량 + qty
     ├─ new_qty > 99 → 400, new_qty > stock → 409
     └─ cart[pid] = new_qty → get_cart(uid) 반환
 → 200 JSON {items, total}
[브라우저] 배지 갱신 (setCartCount)
```

### 4.5 주문 / 결제 (`POST /api/orders`)
```
[브라우저] #order-btn click
 → api("POST", "/api/orders", {payment_method})
[서버] _route_api
 → _auth() → uid
 → Store.create_order(uid, method)
     [RLock 보유]
     ├─ 결제 수단 검사
     ├─ 장바구니가 비었으면 400
     ├─ 상품별 재고 확인 → 부족하면 409
     ├─ total 계산 (서버가 가격을 직접 계산: 클라이언트 가격을 신뢰하지 않음)
     ├─ PaymentGateway.charge(total, method)  → 한도 초과면 402 (여기서 중단, 재고 불변)
     ├─ 재고 차감
     ├─ 주문 dict 생성 → _orders.append
     └─ cart.clear()
 → 201 JSON (주문)
[브라우저] 토스트 표시 → loadCart()
```

### 4.6 프로필 사진 업로드 (`POST /api/users/{id}/avatar`)
```
[브라우저] #avatar-form submit
 → 클라이언트 5MB 검사 (1차 방어, 우회 가능)
 → FormData.append("file", file)
 → api("POST", "/api/users/{id}/avatar", formData)   ※ Content-Type은 브라우저가 설정
[서버] _route_api → _upload_avatar(uid)
 ├─ _auth() == uid ?              아니면 403
 ├─ Content-Type 이 multipart ?    아니면 415
 ├─ _read_body(MAX_REQUEST_BYTES)  Content-Length 먼저 검사 → 초과면 413
 ├─ parse_multipart(body, ctype)   → [Part(name="file", filename, data)]
 ├─ name=="file" & filename 존재 ?  아니면 400
 └─ Store.save_avatar(uid, filename, data)
      ├─ check_extension(filename)  위험 확장자 400 / 허용 외 415
      ├─ 빈 파일 400, 5MB 초과 413
      ├─ detect_image(data)         매직 바이트 아니면 415
      ├─ [RLock 보유]
      │   ├─ _require_user(uid)
      │   └─ _write_unique(_safe_stem(filename), ext, data)
      │        open(uploads/avatars/stem.ext, "xb")
      │        충돌 → stem_타임스탬프.ext 로 재시도
      └─ user.avatar_url = "/uploads/avatars/<name>"
 → 200 JSON (사용자)
[브라우저] 이미지 src 갱신 (?v=타임스탬프로 캐시 우회)
```

### 4.7 사진 조회 (`GET /uploads/avatars/<name>`)
```
→ _handle → path 시작이 /uploads/avatars/
  → unquote → Store.read_avatar(name)
      ├─ 정규식 fullmatch (경로 요소 차단)
      ├─ 파일 존재 확인
      └─ (bytes, mime)
  → _send_bytes(200, data, mime, cache="public, max-age=3600")
     + X-Content-Type-Options: nosniff
```

### 4.8 데이터 저장 위치 요약

| 데이터 | 저장 위치 | 수명 |
|---|---|---|
| 상품 | `Store._products` (메모리) | 프로세스 종료 시 소멸 (매번 시드값으로 초기화) |
| 사용자, 토큰 | `Store._users`, `Store._tokens` (메모리) | 프로세스 종료 시 소멸 |
| 장바구니 | `Store._carts` (메모리) | 프로세스 종료 시 소멸 |
| 주문 | `Store._orders` (메모리 리스트) | 프로세스 종료 시 소멸 |
| 프로필 사진 | `uploads/avatars/` (디스크) | 영구. 삭제 로직 없음 |
| 토큰 (브라우저) | `localStorage["minishop_token"]` | 브라우저 저장소가 지워질 때까지 |

---

## 5. 개선점과 취약점

심각도는 **높음 / 중간 / 낮음**으로 나눴습니다. 코드 위치는 확인된 함수 기준입니다.

### 5.1 높음

**(1) 실제 로그인이 없습니다 — 기능 결함이자 보안 문제**
- `POST /api/users`는 누구나 새 사용자를 만들 수 있고, 같은 이름을 다시 넣어도 **새 계정**이 생깁니다.
- 프론트엔드의 "시작하기" 버튼도 항상 `POST /api/users`를 호출하므로, 같은 닉네임으로 다시 시작하면 이전 장바구니와 주문 내역에 접근할 수 없습니다.
- 개선: 비밀번호 해시 저장(`hashlib.pbkdf2_hmac`, 표준 라이브러리), `POST /api/login` 추가, 토큰에 만료 시간 부여.

**(2) 토큰이 만료되지 않고 폐기할 방법도 없습니다**
- `Store._tokens`의 토큰은 영구히 유효합니다. 토큰이 유출되면 프로세스를 재시작하기 전까지 악용됩니다.
- 로그아웃도 서버에서는 아무 일도 하지 않습니다(브라우저에서 토큰을 지울 뿐입니다).
- 개선: 만료 시간과 `POST /api/logout` 시 토큰 삭제.

**(3) 토큰을 `localStorage`에 저장합니다**
- 현재 HTML에는 XSS 취약점이 없도록 `esc()`를 적용해 두었습니다. 하지만 `localStorage`의 토큰은 스크립트가 실행되는 모든 곳에서 읽을 수 있습니다. 한 곳이라도 뚫리면 토큰이 그대로 유출됩니다.
- 개선: `HttpOnly; SameSite=Strict` 쿠키로 옮기고, 그에 맞춰 CSRF 방어(토큰 헤더 또는 Origin 검사)를 추가합니다.

**(4) 무제한 리소스 증가로 메모리와 디스크가 고갈될 수 있습니다**
- 사용자 생성에 제한이 없어서 `_users`, `_tokens`, `_carts`가 무한히 커질 수 있습니다.
- `_orders`는 계속 늘어나고, `list_orders`는 전체를 순회합니다(O(n)).
- 프로필 사진을 바꿀 때 이전 파일을 지우지 않습니다. 같은 사용자가 계속 올리면 디스크를 채웁니다.
- 개선: IP나 사용자별 속도 제한, 사용자당 파일 수 상한, 교체 시 이전 파일 삭제, 주문 조회 인덱스(`dict[user_id] -> list`).

**(5) 느린 클라이언트로 스레드를 점유할 수 있습니다 (Slowloris 류)**
- `ShopHandler`에 소켓 타임아웃이 없습니다. 본문을 천천히 보내는 클라이언트 하나가 스레드 하나를 계속 붙잡습니다.
- 개선: `ShopHandler.timeout = 10`처럼 타임아웃을 설정하고, 앞단에 리버스 프록시(nginx 등)를 두어 연결 수를 제한합니다.

**(6) 기본 바인딩 주소를 바꾸면 인증 없이 외부에 노출됩니다**
- `--host 0.0.0.0`이면 같은 네트워크의 누구나 API를 호출할 수 있습니다. TLS도 없어서 토큰이 평문으로 오갑니다.
- 개선: 외부 공개 시 TLS 종단(프록시) 필수. 문서에 경고 추가.

### 5.2 중간

**(7) 업로드 파일의 내용 검사가 얕습니다**
- `detect_image`는 앞부분 매직 바이트만 봅니다. 앞부분이 PNG 헤더이고 뒷부분에 HTML이나 스크립트가 붙은 "폴리글롯" 파일도 통과합니다.
- 현재는 `Content-Type: image/png`와 `nosniff`로 응답해서 브라우저가 HTML로 실행하지는 않습니다. 하지만 다른 경로로 제공하면 위험합니다.
- 이미지 디코딩 검증을 하지 않습니다. 파일 크기는 5MB로 제한되지만, PNG 헤더에 `30000×30000`처럼 큰 해상도를 적어 두면 디코더가 메모리를 과도하게 쓸 수 있습니다(디컴프레션 봄).
- 개선: 이미지 라이브러리로 열어 픽셀 크기를 제한하고, 재인코딩해서 저장합니다. 표준 라이브러리만 쓰는 제약이 있으므로, 헤더를 파싱해 크기를 검사하는 방식을 고려할 수 있습니다.

**(8) 이중 확장자를 허용합니다**
- `photo.exe.png`는 마지막 확장자가 `.png`이므로 통과합니다. 현재 저장 이름은 내용 기준이라 실행은 안 되지만, 파일 이름에 의존하는 다른 시스템에서는 문제가 됩니다.
- 개선: 파일명의 모든 확장자 조각을 검사하거나, 저장 이름을 `uuid`로만 만들고 원본 이름은 버립니다.

**(9) multipart 파서가 단순합니다**
- `parse_multipart`는 바이트 문자열을 구분자로 나누는 방식입니다. 본문 안에 구분자와 같은 바이트열이 있으면 잘못 나눌 수 있습니다. 구분자는 클라이언트가 정하므로 공격자는 자기 요청만 망가뜨릴 수 있습니다. 하지만 파서 자체가 엄격하지 않습니다.
- `filename*=UTF-8''...` 형식이나 이스케이프된 따옴표를 처리하지 않습니다.
- 개선: 검증된 파서로 교체하거나, 최소한 구분자 충돌과 헤더 길이에 대한 테스트를 추가합니다.

**(10) 파일 I/O 중에 전역 락을 잡습니다**
- `save_avatar`는 `_lock`을 잡은 채 디스크에 씁니다. 큰 파일이 들어오면 장바구니, 주문, 로그인이 모두 기다립니다.
- 개선: 파일 쓰기는 락 밖에서 하고, 락 안에서는 사용자 객체만 갱신합니다.

**(11) 내부 객체를 그대로 돌려줍니다**
- `list_orders`는 `_orders` 안의 dict 참조를 반환합니다. 호출자가 수정하면 저장된 주문이 바뀝니다. 현재는 바로 JSON으로 직렬화해서 문제가 드러나지 않을 뿐입니다.
- 개선: `copy.deepcopy`나 복사본 반환.

**(12) 보안 응답 헤더가 부족합니다**
- `X-Content-Type-Options`만 있습니다. CSP, `X-Frame-Options` 또는 `frame-ancestors`, `Referrer-Policy`가 없습니다.
- `index.html`은 인라인 스크립트를 사용하므로 CSP를 적용하려면 외부 파일로 빼야 합니다.

**(13) 프로토콜이 HTTP/1.0입니다**
- `BaseHTTPRequestHandler`의 기본값이라 keep-alive가 없습니다. 요청마다 연결을 새로 맺어 성능이 떨어집니다. 현재 규모에서는 문제가 아닙니다.

**(14) 결제 시뮬레이션이 프로세스 내부에서만 일관됩니다**
- 재고 차감과 결제가 같은 락 안에서 일어나므로 한 프로세스에서는 일관됩니다. 여러 워커나 여러 서버로 확장하면 재고가 깨집니다. 현재 구조는 단일 프로세스 전제입니다.

### 5.3 낮음

**(15) 클라이언트 검사만으로는 충분하지 않습니다**
- 프론트엔드의 5MB 검사는 편의 기능입니다. 실제 방어는 서버의 `_read_body`와 `save_avatar`가 담당하며, 두 곳 모두 구현되어 있습니다. 다만 문서상 "클라이언트 검사"를 보안 장치처럼 설명하지 않도록 주의합니다.

**(16) 예외 메시지와 로그**
- 500 응답은 일반 메시지만 보내고 스택트레이스는 로그에만 남깁니다. 좋은 설계입니다. 다만 로그에 토큰이나 본문 내용이 찍히지 않는지 점검이 필요합니다. 현재 코드는 찍지 않습니다.

**(17) 테스트의 빈 곳**
- 동시성 테스트(여러 스레드가 같은 상품을 동시에 주문하는 경우)가 없습니다.
- 한도 초과 402 후 재고가 그대로인지는 단위 테스트로 확인했지만, 주문 경쟁은 확인하지 않았습니다.
- 손상된 multipart 입력에 대한 퍼징 테스트도 없습니다.

**(18) 프론트엔드 설계**
- 상품 목록을 다시 그릴 때 `innerHTML`을 씁니다. `esc()`로 막아 두었지만, 새 코드에서 이 규칙을 빼먹기 쉽습니다. 템플릿 엔진이나 DOM API로 옮기면 안전성이 올라갑니다.
- 인라인 `onsubmit`이나 `onclick` 없이 이벤트 위임을 쓰는 것은 좋습니다.

**(19) `uploads/` 안의 개인 파일**
- `uploads/여권용사진.jpg`는 개인 정보가 들어 있을 수 있는 파일입니다. 이 파일이 어떻게 생겼는지는 확인하지 못했습니다(테스트는 임시 폴더를 쓰므로 테스트가 만든 파일은 아닙니다). 저장소를 공유하기 전에 삭제하거나 `.gitignore`에 넣어야 합니다. 내용은 열어 보지 않았습니다.

---

## 6. 잘 된 점

- **가격을 서버가 계산합니다.** 클라이언트가 보낸 금액을 믿지 않습니다.
- **`_read_body`가 본문을 읽기 전에 `Content-Length`를 검사합니다.** 큰 요청을 메모리에 올리지 않습니다.
- **파일 저장에 `"xb"` 모드를 씁니다.** 존재 확인과 생성이 원자적이라 덮어쓰기 경쟁이 없습니다.
- **파일명을 정규식으로 검사합니다.** `read_avatar`는 경로 탈출을 막습니다.
- **500 응답에 내부 정보를 노출하지 않습니다.**
- **인증 헤더 기반이라 CSRF 자동 전송 문제가 없습니다.** 브라우저가 토큰을 자동으로 보내지 않기 때문입니다.
- **기본 바인딩이 `127.0.0.1`입니다.**
- **`Store`가 HTTP를 모릅니다.** 계층 분리가 되어 있어 테스트가 쉽습니다.

---

## 7. 우선순위 제안

1. 실제 로그인(비밀번호 해시)과 토큰 만료
2. 업로드 이미지 검증 강화(크기 제한, 재인코딩 또는 헤더 검사)와 이전 파일 삭제
3. 소켓 타임아웃과 사용자 생성 속도 제한
4. `_lock` 범위 축소, `list_orders` 복사본 반환
5. 보안 응답 헤더와 CSP 추가
6. 동시성 테스트와 multipart 퍼징 테스트 추가
7. `uploads/`를 `.gitignore`에 추가하고 개인 파일 정리
