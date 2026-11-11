import json

from schedule_manager import ScheduleManager

MENU = """
===== 스케줄 관리 =====
1. 스케줄 추가
2. 스케줄 목록
3. 스케줄 삭제
4. 파일 저장
5. 파일 불러오기
0. 종료
"""


def print_schedules(manager: ScheduleManager) -> bool:
    schedules = manager.list()
    if not schedules:
        print("등록된 스케줄이 없습니다.")
        return False
    for i, s in enumerate(schedules, 1):
        line = f"{i}. {s['date']} {s['time']}  {s['title']}"
        if s.get("memo"):
            line += f"  ({s['memo']})"
        print(line)
    return True


def add_schedule(manager: ScheduleManager) -> None:
    date = input("날짜 (YYYY-MM-DD): ").strip()
    time = input("시간 (HH:MM): ").strip()
    title = input("제목: ")
    memo = input("메모 (선택): ")
    try:
        manager.add(date, time, title, memo)
        print("스케줄을 추가했습니다.")
    except ValueError as e:
        msg = str(e) if "제목" in str(e) else "날짜/시간 형식이 올바르지 않습니다."
        print(f"추가 실패: {msg}")


def delete_schedule(manager: ScheduleManager) -> None:
    if not print_schedules(manager):
        return
    choice = input("삭제할 번호: ").strip()
    try:
        removed = manager.delete(int(choice))
        print(f"삭제했습니다: {removed['date']} {removed['time']} {removed['title']}")
    except ValueError:
        print("숫자를 입력하세요.")
    except IndexError as e:
        print(e)


def load_schedules(manager: ScheduleManager) -> None:
    try:
        count = manager.load()
        print(f"{count}개의 스케줄을 불러왔습니다.")
    except (json.JSONDecodeError, OSError) as e:
        print(f"불러오기 실패: {e}")


def main() -> None:
    manager = ScheduleManager()
    load_schedules(manager)

    while True:
        print(MENU)
        choice = input("번호 선택: ").strip()

        if choice == "1":
            add_schedule(manager)
        elif choice == "2":
            print_schedules(manager)
        elif choice == "3":
            delete_schedule(manager)
        elif choice == "4":
            manager.save()
            print(f"저장했습니다: {manager.path.name}")
        elif choice == "5":
            if manager.dirty and input("저장하지 않은 변경 사항이 사라집니다. 계속할까요? (y/n): ").lower() != "y":
                continue
            load_schedules(manager)
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
