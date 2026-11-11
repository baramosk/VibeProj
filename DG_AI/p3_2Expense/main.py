import json

from expense_manager import EXPENSE, INCOME, KIND_LABELS, ExpenseManager

MENU = """
===== 가계부 =====
1. 수입/지출 추가
2. 수입/지출 조회
3. 항목 삭제
4. 총 잔액 보기
5. 파일 저장
6. 파일 불러오기
0. 종료
"""


def print_transactions(manager: ExpenseManager, kind: str | None = None) -> bool:
    transactions = manager.list_transactions(kind)
    if not transactions:
        print("등록된 내역이 없습니다.")
        return False
    for i, t in enumerate(transactions, 1):
        line = f"{i}. [{KIND_LABELS[t['kind']]}] {t['date']}  {t['category']}  {t['amount']:,}원"
        if t.get("memo"):
            line += f"  ({t['memo']})"
        print(line)
    return True


def add_transaction(manager: ExpenseManager) -> None:
    kind_choice = input("구분 (1: 수입, 2: 지출): ").strip()
    kind = {"1": INCOME, "2": EXPENSE}.get(kind_choice)
    if kind is None:
        print("1 또는 2를 입력하세요.")
        return
    date = input("날짜 (YYYY-MM-DD): ").strip()
    amount = input("금액 (원): ").strip()
    category = input("분류 (예: 월급, 식비): ")
    memo = input("메모 (선택): ")
    try:
        manager.add(kind, date, amount, category, memo)
        print(f"{KIND_LABELS[kind]}을(를) 추가했습니다.")
    except ValueError as e:
        msg = str(e)
        if not ("분류" in msg or "금액" in msg or "구분" in msg):
            msg = "날짜/금액 형식이 올바르지 않습니다."
        print(f"추가 실패: {msg}")


def browse_transactions(manager: ExpenseManager) -> None:
    choice = input("조회 (1: 전체, 2: 수입, 3: 지출): ").strip()
    kind = {"1": None, "2": INCOME, "3": EXPENSE}.get(choice, "invalid")
    if kind == "invalid":
        print("1, 2, 3 중에서 선택하세요.")
        return
    print_transactions(manager, kind)


def delete_transaction(manager: ExpenseManager) -> None:
    if not print_transactions(manager):
        return
    choice = input("삭제할 번호: ").strip()
    try:
        removed = manager.delete_transaction(int(choice))
        label = KIND_LABELS[removed["kind"]]
        amount = f"{removed['amount']:,}원"
        print(f"삭제했습니다: [{label}] {removed['date']} {removed['category']} {amount}")
    except ValueError:
        print("숫자를 입력하세요.")
    except IndexError as e:
        print(e)


def show_balance(manager: ExpenseManager) -> None:
    print(f"총 수입: {manager.total_income():,}원")
    print(f"총 지출: {manager.total_expense():,}원")
    print(f"총 잔액: {manager.total_balance():,}원")


def load_transactions(manager: ExpenseManager) -> None:
    try:
        count = manager.load()
        print(f"{count}개의 내역을 불러왔습니다.")
    except (json.JSONDecodeError, OSError) as e:
        print(f"불러오기 실패: {e}")


def main() -> None:
    manager = ExpenseManager()
    load_transactions(manager)

    while True:
        print(MENU)
        choice = input("번호 선택: ").strip()

        if choice == "1":
            add_transaction(manager)
        elif choice == "2":
            browse_transactions(manager)
        elif choice == "3":
            delete_transaction(manager)
        elif choice == "4":
            show_balance(manager)
        elif choice == "5":
            manager.save()
            print(f"저장했습니다: {manager.path.name}")
        elif choice == "6":
            warning = "저장하지 않은 변경 사항이 사라집니다. 계속할까요? (y/n): "
            if manager.dirty and input(warning).lower() != "y":
                continue
            load_transactions(manager)
        elif choice == "0":
            if manager.dirty and input("변경 사항을 저장할까요? (y/n): ").lower() == "y":
                manager.save()
                print("저장했습니다.")
            print("종료합니다.")
            break
        else:
            print("올바른 번호를 선택하세요.")


if __name__ == "__main__":
    main()
