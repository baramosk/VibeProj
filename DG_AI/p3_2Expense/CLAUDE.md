# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 환경
- 실행은 conda 가상환경 `py311`(Python 3.11)으로 한다: `C:/Users/great/anaconda3/envs/py311/python.exe main.py`
- 이 PC의 기본 `python`은 base(3.9)이므로 그대로 쓰지 않는다. 코드는 3.10 이상 문법(`str | None`)을 쓴다.
- 표준 라이브러리만 사용한다. `requirements.txt`에는 패키지가 없다.

## 규칙
- 화면 문구(메뉴, 안내·오류 메시지)와 코드 주석은 한국어로 쓴다.
- `main.py`는 `from expense_manager import ...`로 불러오므로 모듈 파일명에 하이픈을 쓰지 않는다.
- 데이터 구조: `data.json`은 `{"transactions": [...]}` 형식이다. 각 항목은 `kind`(`"income"` 또는 `"expense"`), `date`(YYYY-MM-DD), `amount`(정수), `category`, `memo`를 가진다. 구분 상수는 `expense_manager.py`의 `INCOME`, `EXPENSE`를 쓴다.

## 주의
- `data.json`은 실제 사용자 데이터다. 메뉴 5(저장)와 종료 시 `y` 응답은 이 파일을 덮어쓴다. 동작을 검증할 때는 임시 폴더의 복사본에서 실행한다.
- 자동화 테스트와 린터는 아직 없다. 변경 후에는 복사본에서 `main.py`를 직접 실행해 확인한다.
