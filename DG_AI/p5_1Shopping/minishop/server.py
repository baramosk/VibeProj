"""표준 라이브러리 HTTP 서버와 JSON API 라우팅."""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .multipart import MultipartError, parse_multipart
from .store import MAX_REQUEST_BYTES, ShopError, Store

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MAX_JSON_BYTES = 64 * 1024
AVATAR_URL_PREFIX = "/uploads/avatars/"

log = logging.getLogger("minishop")


def _to_id(raw: str) -> int:
    if not raw.isdigit():
        raise ShopError(404, "잘못된 ID입니다.")
    return int(raw)


class ShopHandler(BaseHTTPRequestHandler):
    store: Store                      # create_server()에서 주입된다.
    server_version = "MiniShop/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        log.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_DELETE(self) -> None:
        self._handle("DELETE")

    # ------------------------------------------------------------------ 진입점
    def _handle(self, method: str) -> None:
        try:
            path = urllib.parse.urlsplit(self.path).path
            if method == "GET" and path in ("/", "/index.html"):
                self._send_bytes(200, _read_static("index.html"), "text/html; charset=utf-8")
            elif method == "GET" and path.startswith(AVATAR_URL_PREFIX):
                name = urllib.parse.unquote(path[len(AVATAR_URL_PREFIX):])
                data, ctype = self.store.read_avatar(name)
                self._send_bytes(200, data, ctype, cache="public, max-age=3600")
            elif path.startswith("/api/"):
                self._route_api(method, path)
            else:
                raise ShopError(404, "경로를 찾을 수 없습니다.")
        except ShopError as exc:
            self._send_json(exc.status, {"error": exc.message})
        except Exception:
            log.exception("처리되지 않은 오류")
            self._send_json(500, {"error": "서버 내부 오류가 발생했습니다."})

    def _route_api(self, method: str, path: str) -> None:
        parts = [urllib.parse.unquote(p) for p in path.strip("/").split("/")]
        s = self.store

        if parts == ["api", "products"] and method == "GET":
            self._send_json(200, {"products": s.list_products()})
        elif parts == ["api", "users"] and method == "POST":
            body = self._read_json()
            self._send_json(201, s.create_user(body.get("name")))
        elif parts == ["api", "me"] and method == "GET":
            self._send_json(200, s.get_user(self._auth()))
        elif len(parts) == 4 and parts[1] == "users" and parts[3] == "avatar" and method == "POST":
            self._upload_avatar(_to_id(parts[2]))
        elif parts == ["api", "cart"] and method == "GET":
            self._send_json(200, s.get_cart(self._auth()))
        elif parts == ["api", "cart"] and method == "POST":
            uid = self._auth()
            body = self._read_json()
            self._send_json(200, s.add_to_cart(uid, body.get("product_id"), body.get("quantity", 1)))
        elif len(parts) == 3 and parts[1] == "cart" and method == "DELETE":
            uid = self._auth()
            self._send_json(200, s.remove_from_cart(uid, _to_id(parts[2])))
        elif parts == ["api", "orders"] and method == "GET":
            self._send_json(200, {"orders": s.list_orders(self._auth())})
        elif parts == ["api", "orders"] and method == "POST":
            uid = self._auth()
            body = self._read_json()
            self._send_json(201, s.create_order(uid, body.get("payment_method")))
        else:
            raise ShopError(404, "API 경로를 찾을 수 없습니다.")

    # ------------------------------------------------------------------ 기능별 처리
    def _upload_avatar(self, uid: int) -> None:
        if self._auth() != uid:
            raise ShopError(403, "본인의 프로필 사진만 변경할 수 있습니다.")
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data"):
            raise ShopError(415, "multipart/form-data 형식으로 보내주세요.")

        body = self._read_body(MAX_REQUEST_BYTES)
        try:
            parts = parse_multipart(body, content_type)
        except MultipartError as exc:
            raise ShopError(400, str(exc)) from exc

        file_part = next((p for p in parts if p.name == "file" and p.filename), None)
        if file_part is None:
            raise ShopError(400, "'file' 필드에 이미지 파일을 담아 보내주세요.")
        self._send_json(200, self.store.save_avatar(uid, file_part.filename, file_part.data))

    def _auth(self) -> int:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise ShopError(401, "로그인이 필요합니다.")
        return self.store.authenticate(header[len("Bearer "):].strip())

    def _read_body(self, limit: int) -> bytes:
        """Content-Length를 먼저 검사해서 제한을 넘는 본문은 읽지도 않고 거부한다."""
        raw = self.headers.get("Content-Length")
        if raw is None:
            raise ShopError(411, "Content-Length 헤더가 필요합니다.")
        try:
            length = int(raw)
        except ValueError as exc:
            raise ShopError(400, "잘못된 Content-Length입니다.") from exc
        if length < 0:
            raise ShopError(400, "잘못된 Content-Length입니다.")
        if length > limit:
            raise ShopError(413, f"요청 본문이 허용 크기({limit:,} bytes)를 초과했습니다.")
        return self.rfile.read(length)

    def _read_json(self) -> dict:
        raw = self._read_body(MAX_JSON_BYTES)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ShopError(400, "JSON 형식이 올바르지 않습니다.") from exc
        if not isinstance(data, dict):
            raise ShopError(400, "JSON 객체를 보내주세요.")
        return data

    # ------------------------------------------------------------------ 응답
    def _send_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _send_bytes(self, status: int, body: bytes, content_type: str, cache: str = "no-store") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


class _ShopServer(ThreadingHTTPServer):
    daemon_threads = True


def create_server(store: Store, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    handler = type("BoundShopHandler", (ShopHandler,), {"store": store})
    return _ShopServer((host, port), handler)


def run(store: Store, host: str = "127.0.0.1", port: int = 8000) -> None:
    server = create_server(store, host, port)
    print(f"미니 쇼핑몰 실행 중: http://{host}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _read_static(name: str) -> bytes:
    with open(os.path.join(STATIC_DIR, name), "rb") as f:
        return f.read()
