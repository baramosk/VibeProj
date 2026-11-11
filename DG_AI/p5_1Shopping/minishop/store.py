"""도메인 로직: 상품, 사용자, 장바구니, 주문, 프로필 사진.

모든 상태는 메모리에 보관하며 ``threading.RLock`` 으로 보호한다.
외부 의존성 없이 표준 라이브러리만 사용한다.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import secrets
import threading
import uuid

MAX_UPLOAD_BYTES = 5 * 1024 * 1024          # 업로드 파일 최대 크기 (5MB)
MULTIPART_OVERHEAD_BYTES = 16 * 1024        # multipart 헤더 등 부가 데이터 여유분
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES
MAX_CART_QTY = 99
PAYMENT_METHODS = ("card", "bank_transfer")

SEED_PRODUCTS = (
    (1, "무선 키보드", 39_000, 20),
    (2, "USB-C 허브", 25_000, 15),
    (3, "노트북 파우치", 15_000, 30),
    (4, "머그컵", 9_000, 50),
    (5, "블루투스 이어폰", 89_000, 5),
)

# 업로드 허용 확장자 (jpg, png만 허용)
ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg")
# 실행 파일·스크립트 등 위험한 확장자: 별도의 에러 메시지로 거부한다.
DANGEROUS_EXTS = frozenset({
    ".exe", ".dll", ".com", ".bat", ".cmd", ".msi", ".scr", ".ps1", ".vbs", ".js",
    ".jar", ".sh", ".bin", ".app", ".apk", ".reg", ".lnk", ".php", ".py", ".html", ".htm", ".svg",
})

# (매직 바이트, 확장자) — 확장자가 맞더라도 실제 내용이 PNG/JPEG인지 확인한다.
_IMAGE_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
)
_MIME_BY_EXT = {".png": "image/png", ".jpg": "image/jpeg"}
_AVATAR_NAME_RE = re.compile(r"[\w\-]+\.(?:png|jpg)")


class ShopError(Exception):
    """HTTP 상태 코드와 함께 클라이언트에 전달되는 도메인 오류."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def detect_image(data: bytes) -> str | None:
    """이미지 매직 바이트를 보고 확장자를 돌려준다. PNG/JPEG가 아니면 None."""
    for signature, ext in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            return ext
    return None


def check_extension(filename: str | None) -> str:
    """파일명의 확장자를 검사하고 소문자 확장자를 돌려준다."""
    ext = os.path.splitext((filename or "").strip())[1].lower()
    if ext in DANGEROUS_EXTS:
        raise ShopError(400, f"위험한 확장자({ext})의 파일은 업로드할 수 없습니다.")
    if ext not in ALLOWED_IMAGE_EXTS:
        raise ShopError(415, "jpg, png 파일만 업로드할 수 있습니다.")
    return ext


class PaymentGateway:
    """결제 시뮬레이터. 실제 PG 대신 규칙으로 승인/거절을 결정한다.

    금액이 ``limit`` 을 넘으면 한도 초과로 거절한다.
    """

    def __init__(self, limit: int = 1_000_000) -> None:
        self.limit = limit

    def charge(self, amount: int, method: str) -> dict:
        if method not in PAYMENT_METHODS:
            raise ShopError(400, "지원하지 않는 결제 수단입니다.")
        if amount > self.limit:
            raise ShopError(402, f"결제 한도({self.limit:,}원)를 초과하여 승인이 거절되었습니다.")
        return {
            "method": method,
            "amount": amount,
            "transaction_id": uuid.uuid4().hex,
            "status": "approved",
        }


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ShopError(400, f"'{field}'는 정수여야 합니다.")
    return value


def _safe_stem(filename: str | None) -> str:
    """클라이언트가 보낸 파일명에서 경로 요소와 위험 문자를 제거한 기본 이름."""
    base = os.path.basename((filename or "").replace("\\", "/"))
    stem = os.path.splitext(base)[0]
    stem = re.sub(r"[^\w\-]+", "_", stem).strip("_")[:80]
    return stem or "avatar"


def _timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d%H%M%S%f")


class Store:
    def __init__(self, upload_dir: str, payment: PaymentGateway | None = None) -> None:
        self._lock = threading.RLock()
        self._products = {
            pid: {"id": pid, "name": name, "price": price, "stock": stock}
            for pid, name, price, stock in SEED_PRODUCTS
        }
        self._users: dict[int, dict] = {}
        self._tokens: dict[str, int] = {}
        self._carts: dict[int, dict[int, int]] = {}   # user_id -> {product_id: qty}
        self._orders: list[dict] = []
        self._next_user_id = 1
        self._next_order_id = 1
        self.payment = payment or PaymentGateway()
        self.upload_dir = os.path.abspath(upload_dir)
        os.makedirs(self.upload_dir, exist_ok=True)

    # ------------------------------------------------------------------ 사용자
    def create_user(self, name: object) -> dict:
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 30:
            raise ShopError(400, "이름은 1~30자의 문자열이어야 합니다.")
        name = name.strip()
        with self._lock:
            uid = self._next_user_id
            self._next_user_id += 1
            token = secrets.token_urlsafe(24)
            self._users[uid] = {"id": uid, "name": name, "avatar_url": None}
            self._tokens[token] = uid
            self._carts[uid] = {}
            return {**self._users[uid], "token": token}

    def authenticate(self, token: str) -> int:
        with self._lock:
            uid = self._tokens.get(token)
        if uid is None:
            raise ShopError(401, "유효하지 않은 토큰입니다. 다시 로그인해주세요.")
        return uid

    def get_user(self, uid: int) -> dict:
        with self._lock:
            return dict(self._require_user(uid))

    # ------------------------------------------------------------------ 상품
    def list_products(self) -> list[dict]:
        with self._lock:
            return [dict(p) for p in self._products.values()]

    # ------------------------------------------------------------------ 장바구니
    def get_cart(self, uid: int) -> dict:
        with self._lock:
            items = []
            for pid, qty in self._carts[uid].items():
                product = self._products[pid]
                items.append({
                    "product_id": pid,
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": qty,
                    "subtotal": product["price"] * qty,
                })
            return {"items": items, "total": sum(i["subtotal"] for i in items)}

    def add_to_cart(self, uid: int, product_id: object, quantity: object) -> dict:
        pid = _as_int(product_id, "product_id")
        qty = _as_int(quantity, "quantity")
        if not 1 <= qty <= MAX_CART_QTY:
            raise ShopError(400, f"수량은 1~{MAX_CART_QTY} 사이여야 합니다.")
        with self._lock:
            product = self._require_product(pid)
            cart = self._carts[uid]
            new_qty = cart.get(pid, 0) + qty
            if new_qty > MAX_CART_QTY:
                raise ShopError(400, f"장바구니에 담을 수 있는 최대 수량은 {MAX_CART_QTY}개입니다.")
            if new_qty > product["stock"]:
                raise ShopError(409, f"재고가 부족합니다. (남은 재고 {product['stock']}개)")
            cart[pid] = new_qty
            return self.get_cart(uid)

    def remove_from_cart(self, uid: int, product_id: int) -> dict:
        with self._lock:
            cart = self._carts[uid]
            if product_id not in cart:
                raise ShopError(404, "장바구니에 없는 상품입니다.")
            del cart[product_id]
            return self.get_cart(uid)

    # ------------------------------------------------------------------ 주문
    def create_order(self, uid: int, payment_method: object) -> dict:
        if payment_method not in PAYMENT_METHODS:
            raise ShopError(400, "결제 수단은 card 또는 bank_transfer 이어야 합니다.")
        with self._lock:
            cart = self._carts[uid]
            if not cart:
                raise ShopError(400, "장바구니가 비어 있습니다.")

            lines, total = [], 0
            for pid, qty in cart.items():
                product = self._products[pid]
                if qty > product["stock"]:
                    raise ShopError(409, f"'{product['name']}' 재고가 부족합니다. (남은 재고 {product['stock']}개)")
                subtotal = product["price"] * qty
                total += subtotal
                lines.append({"product_id": pid, "name": product["name"],
                              "price": product["price"], "quantity": qty})

            # 결제가 승인된 뒤에만 재고를 차감한다. 거절되면 아무것도 변하지 않는다.
            receipt = self.payment.charge(total, payment_method)
            for pid, qty in cart.items():
                self._products[pid]["stock"] -= qty

            order = {
                "id": self._next_order_id,
                "user_id": uid,
                "items": lines,
                "total": total,
                "status": "paid",
                "payment": receipt,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            }
            self._next_order_id += 1
            self._orders.append(order)
            cart.clear()
            return order

    def list_orders(self, uid: int) -> list[dict]:
        with self._lock:
            return [o for o in self._orders if o["user_id"] == uid]

    # ------------------------------------------------------------------ 프로필 사진
    def save_avatar(self, uid: int, filename: str | None, data: bytes) -> dict:
        check_extension(filename)                   # 확장자 검사 (위험 확장자 / jpg·png 외)
        if not data:
            raise ShopError(400, "빈 파일은 업로드할 수 없습니다.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ShopError(413, "파일은 최대 5MB까지 업로드할 수 있습니다.")
        ext = detect_image(data)                    # 실제 내용이 PNG/JPEG인지 확인
        if ext is None:
            raise ShopError(415, "실제 내용이 jpg, png 이미지가 아닙니다.")

        stem = _safe_stem(filename)
        with self._lock:
            user = self._require_user(uid)
            name = self._write_unique(stem, ext, data)
            user["avatar_url"] = f"/uploads/avatars/{name}"
            return dict(user)

    def read_avatar(self, name: str) -> tuple[bytes, str]:
        if not _AVATAR_NAME_RE.fullmatch(name):
            raise ShopError(404, "파일을 찾을 수 없습니다.")
        ext = os.path.splitext(name)[1].lower()
        path = os.path.join(self.upload_dir, name)
        if not os.path.isfile(path):
            raise ShopError(404, "파일을 찾을 수 없습니다.")
        with open(path, "rb") as f:
            return f.read(), _MIME_BY_EXT[ext]

    def _write_unique(self, stem: str, ext: str, data: bytes) -> str:
        """같은 이름의 파일이 있으면 덮어쓰지 않고 뒤에 타임스탬프를 붙인다.

        ``"xb"`` 모드로 열어 존재 검사와 생성을 원자적으로 처리한다.
        """
        name = f"{stem}{ext}"
        while True:
            try:
                with open(os.path.join(self.upload_dir, name), "xb") as f:
                    f.write(data)
                return name
            except FileExistsError:
                name = f"{stem}_{_timestamp()}{ext}"

    # ------------------------------------------------------------------ 내부 헬퍼
    def _require_user(self, uid: int) -> dict:
        user = self._users.get(uid)
        if user is None:
            raise ShopError(404, "사용자를 찾을 수 없습니다.")
        return user

    def _require_product(self, pid: int) -> dict:
        product = self._products.get(pid)
        if product is None:
            raise ShopError(404, "상품을 찾을 수 없습니다.")
        return product
