"""미니 쇼핑몰 테스트 (unittest, 표준 라이브러리만 사용).

실행: python -m unittest discover -s tests -v
"""

from __future__ import annotations

import http.client
import json
import os
import re
import sys
import tempfile
import threading
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from minishop.multipart import MultipartError, parse_multipart  # noqa: E402
from minishop.server import create_server  # noqa: E402
from minishop.store import (  # noqa: E402
    MAX_REQUEST_BYTES,
    MAX_UPLOAD_BYTES,
    PaymentGateway,
    ShopError,
    Store,
    detect_image,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def multipart_body(filename: str, data: bytes, boundary: str = "XBOUNDARY"):
    head = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode()
    return head + data + tail, f"multipart/form-data; boundary={boundary}"


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.upload_dir = os.path.join(self.tmp.name, "uploads")
        self.store = Store(self.upload_dir)
        self.uid = self.store.create_user("tester")["id"]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _stock(self, pid: int) -> int:
        return next(p["stock"] for p in self.store.list_products() if p["id"] == pid)

    def test_products_are_seeded(self) -> None:
        products = self.store.list_products()
        self.assertGreaterEqual(len(products), 1)
        self.assertEqual(set(products[0]), {"id", "name", "price", "stock"})

    def test_cart_add_and_quantity_limits(self) -> None:
        cart = self.store.add_to_cart(self.uid, 1, 2)
        self.assertEqual(cart["items"][0]["quantity"], 2)
        self.assertEqual(cart["total"], 2 * 39_000)
        with self.assertRaises(ShopError) as ctx:          # 재고 20 초과
            self.store.add_to_cart(self.uid, 1, 19)
        self.assertEqual(ctx.exception.status, 409)
        with self.assertRaises(ShopError) as ctx:          # 1회 최대 수량 초과
            self.store.add_to_cart(self.uid, 3, 100)
        self.assertEqual(ctx.exception.status, 400)
        with self.assertRaises(ShopError):                 # 정수가 아님
            self.store.add_to_cart(self.uid, "1", 1)

    def test_order_decrements_stock_and_clears_cart(self) -> None:
        self.store.add_to_cart(self.uid, 1, 3)
        order = self.store.create_order(self.uid, "card")
        self.assertEqual(order["total"], 3 * 39_000)
        self.assertEqual(order["payment"]["status"], "approved")
        self.assertEqual(self._stock(1), 17)
        self.assertEqual(self.store.get_cart(self.uid)["items"], [])
        self.assertEqual(len(self.store.list_orders(self.uid)), 1)

    def test_declined_payment_keeps_stock_and_cart(self) -> None:
        store = Store(self.upload_dir, payment=PaymentGateway(limit=1_000))
        uid = store.create_user("buyer")["id"]
        store.add_to_cart(uid, 1, 1)                       # 39,000원 > 한도 1,000원
        with self.assertRaises(ShopError) as ctx:
            store.create_order(uid, "card")
        self.assertEqual(ctx.exception.status, 402)
        self.assertEqual(store.get_cart(uid)["items"][0]["quantity"], 1)
        self.assertEqual(next(p["stock"] for p in store.list_products() if p["id"] == 1), 20)

    def test_empty_cart_and_bad_payment_method_rejected(self) -> None:
        with self.assertRaises(ShopError):
            self.store.create_order(self.uid, "card")
        self.store.add_to_cart(self.uid, 1, 1)
        with self.assertRaises(ShopError):
            self.store.create_order(self.uid, "bitcoin")

    def test_avatar_saved_and_duplicate_gets_timestamp_suffix(self) -> None:
        first = self.store.save_avatar(self.uid, "photo.png", PNG)
        self.assertEqual(first["avatar_url"], "/uploads/avatars/photo.png")
        second = self.store.save_avatar(self.uid, "photo.png", PNG + b"\x01")
        name = second["avatar_url"].rsplit("/", 1)[1]
        self.assertRegex(name, r"^photo_\d{20}\.png$")

        with open(os.path.join(self.upload_dir, "photo.png"), "rb") as f:
            self.assertEqual(f.read(), PNG)                # 원본은 덮어쓰이지 않았다
        self.assertTrue(os.path.isfile(os.path.join(self.upload_dir, name)))

    def test_dangerous_extensions_rejected(self) -> None:
        for name in ("setup.exe", "run.BAT", "tool.dll", "script.ps1", "x.js", "page.html"):
            with self.subTest(name=name):
                with self.assertRaises(ShopError) as ctx:
                    self.store.save_avatar(self.uid, name, PNG)
                self.assertEqual(ctx.exception.status, 400)
                self.assertIn("위험한 확장자", ctx.exception.message)

    def test_non_image_extensions_rejected(self) -> None:
        for name in ("doc.pdf", "photo.gif", "photo.webp", "noext"):
            with self.subTest(name=name):
                with self.assertRaises(ShopError) as ctx:
                    self.store.save_avatar(self.uid, name, PNG)
                self.assertEqual(ctx.exception.status, 415)

    def test_fake_image_content_rejected(self) -> None:
        with self.assertRaises(ShopError) as ctx:       # 확장자는 png지만 내용은 exe
            self.store.save_avatar(self.uid, "fake.png", b"MZ\x90\x00" + b"\x00" * 64)
        self.assertEqual(ctx.exception.status, 415)

    def test_jpeg_extension_accepted(self) -> None:
        user = self.store.save_avatar(self.uid, "pic.jpeg", JPG)
        self.assertEqual(user["avatar_url"], "/uploads/avatars/pic.jpg")

    def test_avatar_size_and_type_limits(self) -> None:
        big = PNG + b"\x00" * (MAX_UPLOAD_BYTES - len(PNG) + 1)
        with self.assertRaises(ShopError) as ctx:
            self.store.save_avatar(self.uid, "big.png", big)
        self.assertEqual(ctx.exception.status, 413)

        exact = PNG + b"\x00" * (MAX_UPLOAD_BYTES - len(PNG))
        self.assertEqual(len(exact), MAX_UPLOAD_BYTES)
        self.store.save_avatar(self.uid, "exact.png", exact)   # 정확히 5MB는 허용

        with self.assertRaises(ShopError) as ctx:
            self.store.save_avatar(self.uid, "evil.png", b"<script>alert(1)</script>")
        self.assertEqual(ctx.exception.status, 415)

    def test_avatar_filename_is_sanitized(self) -> None:
        user = self.store.save_avatar(self.uid, "../../etc/evil.png", PNG)
        name = user["avatar_url"].rsplit("/", 1)[1]
        self.assertNotIn("..", user["avatar_url"])
        self.assertTrue(os.path.isfile(os.path.join(self.upload_dir, name)))

    def test_read_avatar_blocks_traversal(self) -> None:
        with self.assertRaises(ShopError) as ctx:
            self.store.read_avatar("../store.py")
        self.assertEqual(ctx.exception.status, 404)

    def test_detect_image(self) -> None:
        self.assertEqual(detect_image(PNG), ".png")
        self.assertEqual(detect_image(JPG), ".jpg")
        self.assertIsNone(detect_image(b"GIF89a" + b"\x00" * 16))
        self.assertIsNone(detect_image(b"hello"))


class MultipartTests(unittest.TestCase):
    def test_parse_file_part(self) -> None:
        body, ctype = multipart_body("a b.png", PNG)
        parts = parse_multipart(body, ctype)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].name, "file")
        self.assertEqual(parts[0].filename, "a b.png")
        self.assertEqual(parts[0].data, PNG)

    def test_missing_boundary_raises(self) -> None:
        with self.assertRaises(MultipartError):
            parse_multipart(b"", "multipart/form-data")


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "uploads"))
        self.server = create_server(self.store, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def _request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = dict(headers or {})
        payload = body
        if isinstance(body, (dict, list)):
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        ctype = resp.getheader("Content-Type", "")
        conn.close()
        data = json.loads(raw) if ctype.startswith("application/json") else raw
        return resp.status, data, ctype

    def _login(self, name: str):
        status, data, _ = self._request("POST", "/api/users", {"name": name})
        self.assertEqual(status, 201)
        return data

    def test_full_shopping_flow(self) -> None:
        user = self._login("kim")
        auth = {"Authorization": "Bearer " + user["token"]}

        status, data, _ = self._request("GET", "/api/products")
        self.assertEqual(status, 200)
        pid = data["products"][0]["id"]

        status, data, _ = self._request("POST", "/api/cart", {"product_id": pid, "quantity": 2}, auth)
        self.assertEqual(status, 200)
        self.assertEqual(data["items"][0]["quantity"], 2)

        status, data, _ = self._request("POST", "/api/orders", {"payment_method": "card"}, auth)
        self.assertEqual(status, 201)
        self.assertEqual(data["status"], "paid")

        status, data, _ = self._request("GET", "/api/orders", headers=auth)
        self.assertEqual(len(data["orders"]), 1)

    def test_cart_requires_login(self) -> None:
        status, data, _ = self._request("GET", "/api/cart")
        self.assertEqual(status, 401)
        self.assertIn("error", data)

    def test_cart_remove_and_bad_json(self) -> None:
        user = self._login("lee")
        auth = {"Authorization": "Bearer " + user["token"]}
        self._request("POST", "/api/cart", {"product_id": 2, "quantity": 1}, auth)
        status, data, _ = self._request("DELETE", "/api/cart/2", headers=auth)
        self.assertEqual(status, 200)
        self.assertEqual(data["items"], [])

        status, _, _ = self._request("POST", "/api/cart", b"{not json", auth)
        self.assertEqual(status, 400)

    def test_avatar_upload_and_fetch(self) -> None:
        user = self._login("park")
        auth = {"Authorization": "Bearer " + user["token"]}
        body, ctype = multipart_body("me.png", PNG)
        status, data, _ = self._request(
            "POST", f"/api/users/{user['id']}/avatar", body,
            {**auth, "Content-Type": ctype})
        self.assertEqual(status, 200)
        self.assertEqual(data["avatar_url"], "/uploads/avatars/me.png")

        status, raw, ctype_out = self._request("GET", data["avatar_url"])
        self.assertEqual(status, 200)
        self.assertEqual(ctype_out, "image/png")
        self.assertEqual(raw, PNG)

    def test_cannot_upload_avatar_for_another_user(self) -> None:
        owner = self._login("owner")
        other = self._login("other")
        body, ctype = multipart_body("x.png", PNG)
        status, _, _ = self._request(
            "POST", f"/api/users/{owner['id']}/avatar", body,
            {"Authorization": "Bearer " + other["token"], "Content-Type": ctype})
        self.assertEqual(status, 403)

    def test_oversized_request_rejected_before_body_is_read(self) -> None:
        user = self._login("big")
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("POST", f"/api/users/{user['id']}/avatar")
        conn.putheader("Authorization", "Bearer " + user["token"])
        conn.putheader("Content-Type", "multipart/form-data; boundary=X")
        conn.putheader("Content-Length", str(MAX_REQUEST_BYTES + 1))
        conn.endheaders()                       # 본문은 보내지 않는다
        resp = conn.getresponse()
        self.assertEqual(resp.status, 413)
        conn.close()

    def test_index_page_is_served(self) -> None:
        status, raw, ctype = self._request("GET", "/")
        self.assertEqual(status, 200)
        self.assertTrue(ctype.startswith("text/html"))
        self.assertIn("미니 쇼핑몰".encode("utf-8"), raw)


if __name__ == "__main__":
    unittest.main()
