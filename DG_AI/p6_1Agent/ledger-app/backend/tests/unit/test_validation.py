"""서버 입력 검증 스키마 단위 테스트 (NFR-06, FR-01, FR-07, FR-10)."""

import pytest
from pydantic import ValidationError

from app.constants import CATEGORY_COLOR_PALETTE
from app.schemas.auth import LoginRequest, SignupRequest
from app.schemas.budget import BudgetCreate
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.transaction import TransactionCreate, TransactionUpdate


def _signup(**overrides):
    data = {"email": "User@Example.com", "password": "abcd1234", "nickname": "닉"}
    data.update(overrides)
    return SignupRequest(**data)


# FR-01: 이메일은 소문자로 정규화하고 형식을 검사합니다.
def test_FR01_email_is_normalized_to_lowercase_and_trimmed():
    assert _signup(email="  User@Example.com ").email == "user@example.com"


@pytest.mark.parametrize("email", ["no-at-sign", "a@b", "a b@c.com", "x" * 250 + "@a.com"])
def test_FR01_invalid_email_is_rejected(email):
    with pytest.raises(ValidationError):
        _signup(email=email)


# FR-01: 비밀번호 8자 이상, 영문과 숫자 포함
@pytest.mark.parametrize("password", ["abc1234", "abcdefgh", "12345678", "abcdefg1"[:7]])
def test_FR01_weak_password_is_rejected(password):
    with pytest.raises(ValidationError):
        _signup(password=password)


def test_FR01_password_policy_accepts_letters_and_digits():
    assert _signup(password="abcd1234").password == "abcd1234"


def test_FR02_login_does_not_apply_signup_password_policy():
    # 로그인 입력은 길이만 확인하고, 정책 위반 여부로 계정 정보를 드러내지 않습니다.
    assert LoginRequest(email="a@b.co", password="12345").password == "12345"


def test_FR01_nickname_blank_after_trim_is_rejected():
    with pytest.raises(ValidationError):
        _signup(nickname="   ")


# FR-07: 이름 1~20자, 공백 제거, 팔레트 색상
def test_FR07_category_name_is_trimmed_and_length_checked():
    assert CategoryCreate(name="  식비  ", type="EXPENSE").name == "식비"
    with pytest.raises(ValidationError):
        CategoryCreate(name="가" * 21, type="EXPENSE")
    with pytest.raises(ValidationError):
        CategoryCreate(name="   ", type="EXPENSE")


def test_FR07_category_color_must_come_from_palette():
    assert CategoryCreate(name="a", type="INCOME", color=CATEGORY_COLOR_PALETTE[0]).color
    with pytest.raises(ValidationError):
        CategoryCreate(name="a", type="INCOME", color="#000001")


def test_FR08_category_update_rejects_explicit_null_name():
    with pytest.raises(ValidationError):
        CategoryUpdate.model_validate({"name": None})


def test_FR07_category_type_must_be_income_or_expense():
    with pytest.raises(ValidationError):
        CategoryCreate(name="a", type="TRANSFER")


# FR-10: 금액은 정수 1 ~ 999,999,999
@pytest.mark.parametrize("amount", [0, -1, 1_000_000_000])
def test_FR10_amount_out_of_range_is_rejected(amount):
    with pytest.raises(ValidationError):
        TransactionCreate(type="EXPENSE", amount=amount, category_id=1)


@pytest.mark.parametrize("amount", [1, 999_999_999])
def test_FR10_amount_bounds_are_inclusive(amount):
    assert TransactionCreate(type="EXPENSE", amount=amount, category_id=1).amount == amount


@pytest.mark.parametrize("amount", [1.5, "1000", True])
def test_FR10_amount_must_be_integer_not_decimal_string_or_bool(amount):
    with pytest.raises(ValidationError):
        TransactionCreate(type="EXPENSE", amount=amount, category_id=1)


def test_FR10_memo_max_200_chars_and_blank_becomes_none():
    body = TransactionCreate(type="EXPENSE", amount=1, category_id=1, memo="가" * 200)
    assert len(body.memo) == 200
    assert TransactionCreate(type="EXPENSE", amount=1, category_id=1, memo="   ").memo is None
    with pytest.raises(ValidationError):
        TransactionCreate(type="EXPENSE", amount=1, category_id=1, memo="가" * 201)


def test_FR12_transaction_update_rejects_explicit_null_amount_but_allows_memo_null():
    with pytest.raises(ValidationError):
        TransactionUpdate.model_validate({"amount": None})
    assert "memo" in TransactionUpdate.model_validate({"memo": None}).model_fields_set


def test_FR18_budget_amount_must_be_positive_integer():
    with pytest.raises(ValidationError):
        BudgetCreate(year_month="2026-11", amount=0)
    with pytest.raises(ValidationError):
        BudgetCreate(year_month="2026-13", amount=100)
