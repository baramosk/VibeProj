# 스케줄 관리 앱 분석 문서

> 대상 프로젝트: `C:\Users\great\VibeProj\DG_AI\p3_1schedule`
> 목적: 프로젝트 구조, 핵심 함수, 상태 관리(`dirty`), 실행 흐름을 정리한 학습·리뷰 자료

---

## 1. 프로젝트 구조

```
p3_1schedule/
├── main.py                  # 진입점. 콘솔 메뉴와 입출력 처리 (95줄)
├── schedule_manager.py      # 데이터 로직. 추가·삭제·정렬·저장·불러오기 (49줄)
├── schedules.json           # 실제 사용자 데이터 (저장 결과 파일)
├── requirements.txt         # 런타임 의존성 (비어 있음, 표준 라이브러리만 사용)
├── requirements-dev.txt     # 개발 도구 (black)
├── CLAUDE.md                # Claude Code용 프로젝트 지침
├── __pycache__/             # Python 컴파일 캐시 (자동 생성)
└── .claude/
    ├── settings.json        # 훅: Write/Edit 후 format_py.py 실행
    ├── hooks/
    │   └── format_py.py     # 저장 시 black으로 자동 정렬
    └── skills/
        └── verify-app/
            └── SKILL.md     # 앱을 실제 실행해 동작을 확인하는 절차
```

### 구성 요약

| 항목 | 내용 |
|---|---|
| 파일 구성 | Python 모듈 2개 + 데이터 파일 1개 |
| 외부 의존성 | 없음 (표준 라이브러리만 사용) |
| 실행 환경 | conda `py311` (Python 3.11). 시스템 기본 Python 3.9는 사용하지 않음 |
| 테스트 | 자동 테스트 없음. `verify-app` 스킬로 수동 검증 |
| 자동화 | Write/Edit 후 black 자동 정렬 훅 |

### 주의 사항

- 메뉴 4(저장)와 종료 시 `y` 응답은 `schedules.json`을 **덮어쓴다.** 검증은 임시 폴더 복사본에서 해야 한다 (CLAUDE.md 지침).
- `main.py`는 `from schedule_manager import ScheduleManager`로 불러오므로 모듈 파일명에 하이픈을 쓰지 않는다.

---

## 2. 모듈별 역할

| 모듈 | 책임 | 계층 |
|---|---|---|
| `schedule_manager.py` | 데이터 보관, 검증, 파일 입출력 | 데이터 / 비즈니스 로직 |
| `main.py` | 메뉴 표시, 사용자 입력 수집, 결과 출력 | 프레젠테이션 (콘솔 UI) |

`main.py`는 데이터를 직접 다루지 않고 `ScheduleManager`의 메서드를 호출한다. 파일 경로와 JSON 형식도 `schedule_manager.py` 안에 숨겨져 있다.

---

## 3. 핵심 함수 명세

### 3.1 `schedule_manager.py` — `ScheduleManager`

| 메서드 | 역할 | 입력 (Parameter) | 출력 (Return) | 예외 / 부작용 |
|---|---|---|---|---|
| `__init__(path=DATA_FILE)` | 매니저 초기화 | `path: Path` (기본값: 스크립트와 같은 폴더의 `schedules.json`) | 없음 | 없음. `schedules=[]`, `dirty=False` |
| `add(date, time, title, memo="")` | 일정 추가 후 정렬, `dirty=True` | `date: str` (YYYY-MM-DD)<br>`time: str` (HH:MM)<br>`title: str`<br>`memo: str` | `dict` — 추가된 항목 | `ValueError`: 날짜·시간 형식 오류, 또는 제목이 공백뿐 |
| `list()` | 목록 복사본 반환 | 없음 | `list[dict]` (얕은 복사본) | 없음 |
| `delete(index)` | 번호로 삭제, `dirty=True` | `index: int` (1부터 시작) | `dict` — 삭제된 항목 | `IndexError`: 범위 밖 번호 |
| `save()` | 메모리 → 파일 저장, `dirty=False` | 없음 | `None` | `OSError`: 파일 쓰기 실패 |
| `load()` | 파일 → 메모리 불러오기, `dirty=False` | 없음 (`self.path` 사용) | `int` — 불러온 개수 | `JSONDecodeError`: JSON 형식 오류<br>`OSError`: 읽기 실패<br>파일이 없으면 빈 목록으로 처리 |

### 3.2 `main.py` — 콘솔 흐름 함수

| 함수 | 역할 | 입력 (Parameter) | 출력 (Return) | 비고 |
|---|---|---|---|---|
| `print_schedules(manager)` | 목록을 번호와 함께 출력 | `manager: ScheduleManager` | `bool` (목록이 있으면 `True`) | 메뉴 2, 삭제 전 목록 표시에 사용 |
| `add_schedule(manager)` | 입력 4개를 받아 `add()` 호출 | `manager` | `None` | `ValueError`를 잡아 메시지 출력 |
| `delete_schedule(manager)` | 목록 표시 후 번호를 받아 `delete()` 호출 | `manager` | `None` | 숫자 아님은 `ValueError`, 범위 밖은 `IndexError` 처리 |
| `load_schedules(manager)` | `load()` 호출 후 개수 출력 | `manager` | `None` | `JSONDecodeError`, `OSError` 처리 |
| `main()` | 진입점. 시작 시 불러오기, 메뉴 루프 실행 | 없음 | `None` | 메뉴 번호별 분기 |

---

## 4. 상태 관리: `dirty` 플래그

`dirty`는 **메모리의 일정 목록이 마지막 파일 저장(또는 불러오기) 시점과 다른지** 나타내는 플래그다. 파일을 건드리지 않고 메모리에서만 판단하며, 저장되지 않은 변경을 잃지 않도록 확인 질문을 띄우는 데 쓰인다.

### 4.1 값 변화 지점

| 위치 | 코드 | 의미 |
|---|---|---|
| `__init__` | `dirty = False` | 초기 상태는 변경 없음 |
| `add()` | `dirty = True` | 추가로 파일과 달라짐 |
| `delete()` | `dirty = True` | 삭제로 파일과 달라짐 |
| `save()` | `dirty = False` | 메모리 내용을 파일에 기록해 일치 |
| `load()` | `dirty = False` | 파일 내용을 메모리에 읽어 일치 |

### 4.2 사용 지점 (`main.py`)

| 메뉴 | 조건 | 동작 |
|---|---|---|
| 5 (불러오기) | `dirty == True` | "사라집니다. 계속할까요?" 질문. `y`가 아니면 `continue`로 불러오기 취소 |
| 0 (종료) | `dirty == True` | "저장할까요?" 질문. `y`일 때만 `save()` 호출 |

`dirty == False`이면 질문 없이 바로 진행한다.

### 4.3 한계

- `dirty`는 **변경 여부만** 알려 준다. 어떤 변경이 있었는지는 추적하지 않는다.
- 추가한 뒤 삭제해 원래 상태로 돌아와도 `dirty`는 여전히 `True`다. 불필요한 확인 질문이 나올 수 있다.

---

## 5. 실행 흐름 (Execution Flow)

### 5.1 전체 호출 구조

```
main.py
 ├ main()
 │   ├ ScheduleManager()            ← 객체 생성, 파일 경로 결정
 │   ├ load_schedules(manager)
 │   │   └ manager.load()           ← 파일 → 메모리
 │   └ while True:
 │       ├ print(MENU)
 │       ├ input("번호 선택: ")
 │       ├ "1" → add_schedule(manager)
 │       │        ├ input() × 4     ← 사용자 입력
 │       │        └ manager.add()   ← 메모리 목록 갱신
 │       ├ "2" → print_schedules(manager)
 │       │        └ manager.list()  ← 메모리 복사본 → 화면 출력
 │       ├ "4" → manager.save()     ← 메모리 → 파일
 │       └ "0" → 종료
```

### 5.2 시나리오: 추가 → 조회 → 저장 → 종료

예시 입력: `2025-03-01` / `10:00` / `회의` / (메모 없음)

| 단계 | 호출 | 데이터 이동 | 상태 변화 | 화면 출력 |
|---|---|---|---|---|
| 1. 시작 | `main.py:94-95` → `main()` | — | — | — |
| 2. 객체 생성 | `ScheduleManager()` | — | `path` 결정, `dirty=False` | — |
| 3. 불러오기 | `load()` | 파일 → 메모리 | `schedules` 채움, `dirty=False` | "N개의 스케줄을 불러왔습니다." |
| 4. 메뉴 입력 | `input("번호 선택")` | 사용자 → 프로그램 | — | 메뉴 |
| 5. 추가 | `add_schedule` → `add()` | 입력 → 메모리 | 목록에 추가, `dirty=True` | "스케줄을 추가했습니다." |
| 6. 조회 | `print_schedules` → `list()` | 메모리 복사본 → 화면 | 변화 없음 | "1. 2025-03-01 10:00  회의" |
| 7. 저장 | `save()` | 메모리 → 파일 | 파일 덮어씀, `dirty=False` | "저장했습니다: schedules.json" |
| 8. 종료 | `dirty` 확인 → `break` | — | `dirty=False`라 질문 없음 | "종료합니다." |

### 5.3 데이터 이동 요약

| 방향 | 함수 | 설명 |
|---|---|---|
| 파일 → 메모리 | `load()` | 시작 시, 메뉴 5에서 호출 |
| 입력 → 메모리 | `add()` | 검증 후 리스트에 추가 |
| 메모리 → 화면 | `list()`, `print_schedules()` | 복사본을 출력. 원본은 보호됨 |
| 메모리 → 파일 | `save()` | 메뉴 4, 또는 종료 시 `y` |

### 5.4 저장하지 않고 종료하면

1. 추가 후 저장 없이 메뉴 0을 누른다.
2. `dirty == True`이므로 "저장할까요?"를 묻는다.
3. `n`을 고르면 파일은 바뀌지 않는다.
4. 다음 실행 때 `load()`가 예전 파일만 읽어 와서 추가했던 일정이 사라진다.

---

## 6. 리뷰 메모

리뷰 단계에서 확인할 만한 항목을 정리했다. 확정된 버그가 아니라 검토 후보다.

| # | 위치 | 내용 | 분류 |
|---|---|---|---|
| 1 | `schedule_manager.py` `list()` | 메서드 이름이 내장 타입 `list`와 같다. 클래스 안에서 `list[dict]` 타입 힌트와 혼동될 수 있다. `get_all()` 같은 이름이 더 명확하다. | 가독성 |
| 2 | `main.py:32-33` | 제목과 메모를 입력받을 때 `.strip()`하지 않는다. 공백 제거는 `add()` 안에서 이뤄진다. 검증 위치가 나뉘어 있다. | 일관성 |
| 3 | `main.py:35` | `add()`가 반환하는 `entry`를 사용하지 않는다. 필요 없다면 괜찮지만, 확인 메시지에 활용할 수 있다. | 참고 |
| 4 | `schedule_manager.py` `dirty` | 추가 후 삭제해도 `True`가 유지된다. 변경 내역 기반 판단이 필요하면 개선 대상이다. | 설계 |
| 5 | `schedule_manager.py` `save()` | 임시 파일에 쓴 뒤 교체하지 않으므로, 쓰기 도중 오류가 나면 기존 파일이 손상될 수 있다. | 안정성 |
| 6 | `main.py:81` | 메뉴 5의 확인 질문에서 `.lower() != "y"`를 쓴다. 메뉴 0은 `== "y"`를 쓴다. 두 조건의 의미를 한눈에 알기 어렵다. | 가독성 |
| 7 | 테스트 | 자동 테스트가 없다. `ScheduleManager`는 `path` 인자를 받으므로 임시 파일로 단위 테스트를 작성하기 쉽다. | 테스트 |

---

## 7. 학습 포인트 요약

- **책임 분리**: 데이터 로직(`ScheduleManager`)과 입출력(`main.py`)을 나눠서, 데이터 로직을 콘솔 없이 테스트할 수 있다.
- **방어적 복사**: `list()`가 복사본을 반환해 외부에서 내부 상태를 바꾸지 못하게 한다.
- **플래그 기반 확인**: `dirty`로 데이터 손실 가능성이 있는 동작 앞에서만 사용자에게 확인을 받는다.
- **경로 기준 설정**: `Path(__file__)`을 사용해 실행 위치와 상관없이 같은 데이터 파일을 참조한다.
- **입력 검증 계층**: 형식 검증은 `datetime.strptime`, 빈 제목 검증은 `add()`에서 맡는다. 예외 메시지는 `main.py`가 사용자에게 보여 준다.
