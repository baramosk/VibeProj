import json
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).with_name("data.json")

INCOME = "income"
EXPENSE = "expense"
KIND_LABELS = {INCOME: "수입", EXPENSE: "지출"}


class ExpenseManager:
    def __init__(self, path: Path = DATA_FILE):
        self.path = Path(path)
        self.transactions: list[dict] = []
        self.dirty = False

    def add(self, kind: str, date: str, amount: str, category: str, memo: str = "") -> dict:
        # kind는 INCOME 또는 EXPENSE만 허용
        if kind not in KIND_LABELS:
            raise ValueError("구분은 수입 또는 지출이어야 합니다.")
        # 날짜 형식이 잘못되면 ValueError 발생
        datetime.strptime(date, "%Y-%m-%d")
        value = int(amount.replace(",", "").strip())
        if value <= 0:
            raise ValueError("금액은 0보다 커야 합니다.")
        if not category.strip():
            raise ValueError("분류를 입력해야 합니다.")
        entry = {
            "kind": kind,
            "date": date,
            "amount": value,
            "category": category.strip(),
            "memo": memo.strip(),
        }
        self.transactions.append(entry)
        self.transactions.sort(key=lambda t: t["date"])
        self.dirty = True
        return entry

    def list_transactions(self, kind: str | None = None) -> list[dict]:
        # kind가 None이면 수입과 지출을 모두 반환
        if kind is None:
            return list(self.transactions)
        return [t for t in self.transactions if t["kind"] == kind]

    def total_income(self) -> int:
        return sum(t["amount"] for t in self.transactions if t["kind"] == INCOME)

    def total_expense(self) -> int:
        return sum(t["amount"] for t in self.transactions if t["kind"] == EXPENSE)

    def total_balance(self) -> int:
        # 총 잔액 = 총 수입 - 총 지출
        return self.total_income() - self.total_expense()

    def delete_transaction(self, index: int) -> dict:
        # index는 list_transactions()의 목록에 표시되는 1부터 시작하는 번호
        if not 1 <= index <= len(self.transactions):
            raise IndexError("해당 번호의 항목이 없습니다.")
        removed = self.transactions.pop(index - 1)
        self.dirty = True
        return removed

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump({"transactions": self.transactions}, f, ensure_ascii=False, indent=2)
        self.dirty = False

    def load(self) -> int:
        if not self.path.exists():
            self.transactions = []
        else:
            with self.path.open(encoding="utf-8") as f:
                self.transactions = json.load(f).get("transactions", [])
            self.transactions.sort(key=lambda t: t["date"])
        self.dirty = False
        return len(self.transactions)
