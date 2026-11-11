# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 환경
- conda 가상환경 `py311`(Python 3.11)을 사용한다. 이 PC의 기본 `python`은 base(3.9)이므로 그대로 쓰지 않는다.
  - 실행: `C:/Users/great/anaconda3/envs/py311/python.exe main.py` (또는 `conda activate py311` 후 `python main.py`)
- 앱은 표준 라이브러리만 사용한다(`requirements.txt`는 비어 있음). 개발 도구 black은 `requirements-dev.txt`에 있다.

## 규칙
- 화면 문구(메뉴, 안내·오류 메시지)와 코드 주석은 한국어로 쓴다.
- 코드를 바꾸면 반드시 직접 실행해 확인한다. 방법은 `/verify-app` 스킬을 따른다.
- `.py` 파일은 수정할 때마다 훅(`.claude/hooks/format_py.py`)이 black으로 자동 정렬하므로 수동 정렬은 필요 없다.

## 주의
- 메뉴 4(저장)와 종료 시 `y` 응답은 `schedules.json`(실제 사용자 데이터)을 덮어쓴다. 검증 실행은 임시 폴더의 복사본에서 한다.
- `main.py`는 `from schedule_manager import ScheduleManager`로 불러오므로 모듈 파일명에 하이픈을 쓰지 않는다.
