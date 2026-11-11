# 가계부 앱 분석 자료

> 대상: `C:\Users\great\VibeProj\DG_AI\p3_2Expense`
> 목적: 프로젝트 구조, 핵심 함수, 실행 흐름을 정리한 학습 및 리뷰용 문서

---

## 1. 프로젝트 구조

```
p3_2Expense/
├── main.py                    # 진입점: 콘솔 메뉴 UI (123줄)
├── expense_manager.py         # 핵심 로직: 모델, 검증, 합계, 저장/불러오기 (78줄)
├── test_expense_manager.py    # pytest 단위 테스트 (113줄)
├── data.json                  # 실제 사용자 거래 데이터 (주의: 덮어쓰기 대상)
├── practice.ipynb             # pytest·ruff 학습용 노트북
├── requirements.txt           # 런타임 의존성 없음 (표준 라이브러리만 사용)
├── requirements-dev.txt       # 개발 도구: pytest, ruff
├── ruff.toml                  # 린터 설정 (target py311, 줄 길이 100)
├── CLAUDE.md                  # 프로젝트 지침
├── account_book_analysis.md   # 이 문서
└── .ruff_cache/               # ruff 캐시 (자동 생성)
```

### 파일별 역할

| 파일 | 역할 |
|---|---|
| `expense_manager.py` | `ExpenseManager` 클래스. 추가, 조회, 합계, 삭제, 저장, 불러오기를 담당합니다. 상수 `INCOME`, `EXPENSE`, `KIND_LABELS`를 정의합니다. |
| `main.py` | 콘솔 메뉴 루프와 입출력을 담당합니다. 계산은 `ExpenseManager`에 맡깁니다. |
| `test_expense_manager.py` | 임시 폴더(`tmp_path`)를 사용해 `ExpenseManager`를 테스트합니다. 실제 `data.json`은 건드리지 않습니다. |
| `data.json` | `{"transactions": [...]}` 구조. 각 항목은 `kind`, `date`, `amount`, `category`, `memo`를 가집니다. |

### 데이터 흐름

```
main.py (메뉴, 입출력)
   │  from expense_manager import EXPENSE, INCOME, KIND_LABELS, ExpenseManager
   ▼
ExpenseManager (검증, 계산, 영속화)
   │  load() / save()
   ▼
data.json
```

### 실행 및 점검 명령 (CLAUDE.md 기준)

- 실행: `C:/Users/great/anaconda3/envs/py311/python.exe main.py`
- 테스트: `pytest` (requirements-dev.txt 설치 후)
- 린트: `python -m ruff check .`
- 검증 원칙: 메뉴 5(저장)와 종료 시 `y` 응답은 `data.json`을 덮어쓰므로, 동작 확인은 임시 폴더의 복사본에서 합니다.

---

## 2. 핵심 함수

### 2-1. 내역 추가

| 함수 | 위치 | 입력 (Parameter) | 출력 (Return) |
|---|---|---|---|
| `ExpenseManager.add` | `expense_manager.py:18` | `kind: str`, `date: str`(YYYY-MM-DD), `amount: str`(쉼표 허용), `category: str`, `memo: str = ""` | `dict` 추가된 항목. 실패 시 `ValueError` |
| `add_transaction` | `main.py:30` | `manager: ExpenseManager` (입력은 `input()`) | `None` (출력만 함) |

### 2-2. 내역 삭제

| 함수 | 위치 | 입력 (Parameter) | 출력 (Return) |
|---|---|---|---|
| `ExpenseManager.delete_transaction` | `expense_manager.py:57` | `index: int` (1부터 시작) | `dict` 삭제된 항목. 범위 밖이면 `IndexError` |
| `delete_transaction` | `main.py:59` | `manager: ExpenseManager` | `None` |

### 2-3. 내역 조회

| 함수 | 위치 | 입력 (Parameter) | 출력 (Return) |
|---|---|---|---|
| `ExpenseManager.list_transactions` | `expense_manager.py:41` | `kind: str \| None = None` | `list[dict]` 복사본 |
| `print_transactions` | `main.py:17` | `manager`, `kind: str \| None = None` | `bool` 내역 존재 여부 |
| `browse_transactions` | `main.py:50` | `manager` | `None` |

### 2-4. 잔액 계산

| 함수 | 위치 | 입력 (Parameter) | 출력 (Return) |
|---|---|---|---|
| `ExpenseManager.total_income` | `expense_manager.py:47` | 없음 | `int` 총 수입 |
| `ExpenseManager.total_expense` | `expense_manager.py:50` | 없음 | `int` 총 지출 |
| `ExpenseManager.total_balance` | `expense_manager.py:53` | 없음 | `int` 잔액 (수입 - 지출, 음수 가능) |
| `show_balance` | `main.py:74` | `manager` | `None` |

### 2-5. 저장과 불러오기

| 함수 | 위치 | 입력 (Parameter) | 출력 (Return) |
|---|---|---|---|
| `ExpenseManager.save` | `expense_manager.py:65` | 없음 | `None`. `dirty`를 `False`로 바꿈 |
| `ExpenseManager.load` | `expense_manager.py:70` | 없음 | `int` 불러온 개수. 파일이 없으면 0 |

### 요약

- 데이터 처리(검증, 추가, 삭제, 조회, 합계, 저장)는 `ExpenseManager`가 맡고, 화면과 분리되어 있습니다.
- `main.py`의 함수는 입력을 받고 결과를 출력하는 역할만 합니다.
- `delete_transaction`이라는 이름이 두 모듈에 있습니다. 모듈이 달라 충돌은 없지만 읽을 때 헷갈릴 수 있습니다.
- 삭제 번호와 화면 번호는 모두 전체 목록 기준이라 현재는 일치합니다.

---

## 3. 실행 흐름

### 3-1. 시작

1. `main()` (`main.py:88`) → `ExpenseManager()` 생성. `transactions = []`, `dirty = False`
2. `load_transactions()` (`main.py:80`) → `load()` (`expense_manager.py:70`)
   - 파일이 있으면 읽어서 날짜순 정렬, 파일이 없으면 빈 리스트
   - `dirty = False`, 개수를 출력

### 3-2. 내역 입력부터 잔액 확인까지 (메뉴 1 → 4 → 5)

1. 메인 메뉴 표시, 번호 입력 (`main.py:92-94`)
2. 메뉴 1 → `add_transaction()` (`main.py:30`). 구분, 날짜, 금액, 분류, 메모를 입력받습니다.
3. `manager.add()` (`expense_manager.py:18`)
   - 구분 검사 (`:20`), 날짜 검사 `strptime` (`:23`), 금액 변환 `int()` (`:24`), 금액 > 0 검사 (`:25`), 분류 검사 (`:27`)
   - 항목 생성 (`:29-35`), `append` (`:36`), 날짜순 정렬 (`:37`), `dirty = True` (`:38`), `entry` 반환 (`:39`)
4. 성공 시 추가 완료 메시지 출력. 실패 시 `ValueError` 메시지를 `추가 실패:`와 함께 출력합니다 (`main.py:43-47`). 실패하면 리스트와 `dirty`는 바뀌지 않습니다.
5. 메뉴 4 → `show_balance()` (`main.py:74`)
   - 별도의 갱신 단계 없이, 메모리 리스트로 `total_income()`, `total_expense()`, `total_balance()`를 다시 계산합니다.
   - 방금 추가한 내역이 바로 반영됩니다.
6. 메뉴 5 → `save()` (`expense_manager.py:65`)
   - `data.json`을 `"w"`로 열어 전체를 다시 씁니다.
   - `dirty = False`, `저장했습니다: data.json` 출력

### 3-3. 종료

1. 메뉴 0 (`main.py:112`)
2. `dirty`가 `True`이면 저장 여부를 묻습니다 (`main.py:113`).
3. `y`이면 `save()`를 호출하고, 그 밖의 응답이면 저장하지 않고 종료합니다.

### 3-4. 상태 변화 요약

| 단계 | 메모리 리스트 | `dirty` | `data.json` |
|---|---|---|---|
| 시작 | 파일 내용으로 채워짐 | `False` | 변경 없음 |
| 메뉴 1 (성공) | 추가 및 정렬 | `True` | 변경 없음 |
| 메뉴 1 (실패) | 변경 없음 | 변경 없음 | 변경 없음 |
| 메뉴 4 | 읽기만 | 변경 없음 | 변경 없음 |
| 메뉴 5 또는 종료 시 `y` | 변경 없음 | `False` | 전체 덮어쓰기 |
| 종료 시 `n` | 소실 | `True` | 이전 상태 유지 |

---

## 4. 리뷰 시 확인된 사항

| 번호 | 구분 | 내용 | 관련 위치 |
|---|---|---|---|
| 1 | 데이터 손실 | 저장하지 않고 종료(`n`)하면 입력한 내역이 사라집니다. | `main.py:113` |
| 2 | 예외 처리 | `save()` 호출부에 `try`가 없어서, 쓰기 중 `OSError`가 나면 프로그램이 traceback과 함께 종료됩니다. `load_transactions()`는 `OSError`를 잡는 것과 비교하면 일관성이 없습니다. | `main.py:104-106`, `main.py:84` |
| 3 | 파일 안전성 | `"w"` 모드로 열면 파일이 먼저 비워지므로, 쓰기 도중 실패하면 `data.json`이 손상될 수 있습니다. 임시 파일에 쓴 뒤 교체하는 방식이 더 안전합니다. | `expense_manager.py:66-67` |
| 4 | 번호 체계 | 조회와 삭제가 모두 전체 목록 기준 번호를 씁니다. 종류 필터 기능이 추가되면 번호가 어긋날 수 있습니다. | `main.py:17`, `main.py:59` |
| 5 | 이름 중복 | `delete_transaction`이 두 모듈에 있습니다. | `expense_manager.py:57`, `main.py:59` |
| 6 | 인코딩 | `practice.ipynb`를 기본 인코딩으로 읽었을 때 한글이 깨져 보였습니다. 파일 자체의 문제인지는 확인하지 않았습니다. | `practice.ipynb` |
| 7 | 저장소 설정 | `.gitignore`가 없어서 `.ruff_cache/`, `__pycache__/`가 버전 관리에 섞일 수 있습니다. | 프로젝트 루트 |
| 8 | 검증 상태 | 이 문서 작성 시점에 pytest와 ruff는 실행하지 않았습니다. | - |

---

## 5. 추후 학습 및 개선 메모

- **단위 테스트 보강**: `main.py`의 입출력 함수와 메뉴 흐름은 테스트 대상이 아닙니다. `input` 모킹으로 테스트를 추가할 수 있습니다.
- **저장 안정성**: 임시 파일 쓰기 후 `os.replace`로 교체하는 방식을 검토합니다. 예외 처리도 함께 추가합니다.
- **번호 체계 분리**: 내역에 고유 ID를 부여하면 필터 조회와 삭제가 번호에 의존하지 않게 됩니다.
- **인터페이스 분리**: 입출력과 로직을 더 나누면 `main.py`의 테스트가 쉬워집니다.
- **Git 설정**: `.gitignore`에 `__pycache__/`, `.ruff_cache/`를 추가합니다.

---

*작성 기준: 프로젝트 파일 직접 분석. 코드 변경은 하지 않았고, `data.json`은 읽기만 했습니다.*
