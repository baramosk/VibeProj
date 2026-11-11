import pytest

from expense_manager import EXPENSE, INCOME, ExpenseManager


@pytest.fixture
def manager(tmp_path):
    # 실제 data.json을 건드리지 않도록 임시 폴더의 파일을 사용한다.
    return ExpenseManager(tmp_path / "data.json")


def test_add_income_and_expense_updates_totals(manager):
    manager.add(INCOME, "2025-03-01", "500,000", "월급")
    manager.add(EXPENSE, "2025-03-02", "12000", "식비", "점심")

    assert manager.total_income() == 500000
    assert manager.total_expense() == 12000
    assert manager.total_balance() == 488000


def test_add_strips_commas_and_whitespace(manager):
    entry = manager.add(EXPENSE, "2025-03-02", " 1,500 ", "  교통  ", " 버스 ")

    assert entry["amount"] == 1500
    assert entry["category"] == "교통"
    assert entry["memo"] == "버스"


@pytest.mark.parametrize(
    "kind, date, amount, category",
    [
        ("transfer", "2025-03-01", "100", "기타"),  # 알 수 없는 구분
        (INCOME, "2025/03/01", "100", "기타"),  # 날짜 형식 오류
        (INCOME, "2025-03-01", "0", "기타"),  # 0원
        (EXPENSE, "2025-03-01", "-100", "기타"),  # 음수
        (EXPENSE, "2025-03-01", "abc", "기타"),  # 숫자가 아닌 금액
        (EXPENSE, "2025-03-01", "100", "   "),  # 빈 분류
    ],
)
def test_add_rejects_invalid_input(manager, kind, date, amount, category):
    with pytest.raises(ValueError):
        manager.add(kind, date, amount, category)
    assert manager.list_transactions() == []


def test_list_transactions_filters_by_kind(manager):
    manager.add(INCOME, "2025-03-01", "100", "용돈")
    manager.add(EXPENSE, "2025-03-02", "200", "식비")
    manager.add(EXPENSE, "2025-03-03", "300", "교통")

    assert len(manager.list_transactions()) == 3
    assert [t["kind"] for t in manager.list_transactions(INCOME)] == [INCOME]
    assert len(manager.list_transactions(EXPENSE)) == 2


def test_transactions_are_sorted_by_date(manager):
    manager.add(EXPENSE, "2025-03-05", "100", "식비")
    manager.add(EXPENSE, "2025-03-01", "100", "교통")

    dates = [t["date"] for t in manager.list_transactions()]
    assert dates == ["2025-03-01", "2025-03-05"]


def test_delete_transaction_removes_entry_and_updates_balance(manager):
    manager.add(INCOME, "2025-03-01", "1000", "용돈")
    manager.add(EXPENSE, "2025-03-02", "300", "식비")

    removed = manager.delete_transaction(2)  # 날짜 순 2번째 = 지출 항목

    assert removed["category"] == "식비"
    assert len(manager.list_transactions()) == 1
    assert manager.total_balance() == 1000
    assert manager.dirty is True


@pytest.mark.parametrize("index", [0, 2, -1])
def test_delete_transaction_rejects_out_of_range_index(manager, index):
    manager.add(INCOME, "2025-03-01", "1000", "용돈")

    with pytest.raises(IndexError):
        manager.delete_transaction(index)
    assert len(manager.list_transactions()) == 1


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "data.json"
    first = ExpenseManager(path)
    first.add(INCOME, "2025-03-01", "500000", "월급", "3월")
    first.add(EXPENSE, "2025-03-02", "12000", "식비")
    first.save()

    assert first.dirty is False

    second = ExpenseManager(path)
    assert second.load() == 2
    assert second.total_balance() == 488000
    assert second.list_transactions()[0]["memo"] == "3월"


def test_load_returns_zero_when_file_missing(tmp_path):
    manager = ExpenseManager(tmp_path / "missing.json")

    assert manager.load() == 0
    assert manager.list_transactions() == []


def test_unsaved_changes_are_not_written_to_disk(tmp_path):
    path = tmp_path / "data.json"
    manager = ExpenseManager(path)
    manager.add(INCOME, "2025-03-01", "1000", "용돈")

    assert manager.dirty is True
    assert not path.exists()
