"""비밀번호 해시와 세션 토큰 유틸 (NFR-01, NFR-03).

- 비밀번호: argon2-cffi의 PasswordHasher (Argon2id, 라이브러리 기본 파라미터).
- 세션 토큰: secrets로 생성한 무작위 값. DB에는 SHA-256 해시만 저장합니다.
  DB가 유출되어도 쿠키 값을 바로 재사용할 수 없게 하기 위함입니다.
"""

import hashlib
import hmac
import secrets
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


@lru_cache
def _dummy_hash() -> str:
    # 존재하지 않는 이메일로 로그인할 때도 해시 검증 시간을 맞추기 위한 값입니다 (계정 존재 여부 노출 방지).
    return hash_password(secrets.token_urlsafe(32))


def burn_password_check(password: str) -> None:
    verify_password(_dummy_hash(), password)


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(expected: str, provided: str) -> bool:
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))
