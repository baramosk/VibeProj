import json
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).with_name("schedules.json")


class ScheduleManager:
    def __init__(self, path: Path = DATA_FILE):
        self.path = Path(path)
        self.schedules: list[dict] = []
        self.dirty = False

    def add(self, date: str, time: str, title: str, memo: str = "") -> dict:
        # 형식이 잘못되면 ValueError 발생
        datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        if not title.strip():
            raise ValueError("제목을 입력해야 합니다.")
        entry = {"date": date, "time": time, "title": title.strip(), "memo": memo.strip()}
        self.schedules.append(entry)
        self.schedules.sort(key=lambda s: (s["date"], s["time"]))
        self.dirty = True
        return entry

    def list(self) -> list[dict]:
        return list(self.schedules)

    def delete(self, index: int) -> dict:
        # index는 목록에 표시되는 1부터 시작하는 번호
        if not 1 <= index <= len(self.schedules):
            raise IndexError("해당 번호의 스케줄이 없습니다.")
        removed = self.schedules.pop(index - 1)
        self.dirty = True
        return removed

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump({"schedules": self.schedules}, f, ensure_ascii=False, indent=2)
        self.dirty = False

    def load(self) -> int:
        if not self.path.exists():
            self.schedules = []
        else:
            with self.path.open(encoding="utf-8") as f:
                self.schedules = json.load(f).get("schedules", [])
            self.schedules.sort(key=lambda s: (s["date"], s["time"]))
        self.dirty = False
        return len(self.schedules)
