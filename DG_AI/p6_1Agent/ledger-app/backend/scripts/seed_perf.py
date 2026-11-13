"""성능 측정용 시드 데이터 생성 (Q-I, SC-02, SC-03, NFR-13, NFR-14). 개발 전용입니다.

- 운영 DB(ledger.db)와 섞이지 않도록 별도 SQLite 파일(기본 perf.db)에만 씁니다. ledger.db 경로는 거부합니다.
- 만든 것: 테스트 계정 1개, 최근 12개월 거래 (기본 10,000건), 월별 전체 지출 예산과 식비 예산.
- 같은 SEED면 항상 같은 데이터가 나와 측정을 반복할 수 있습니다.

실행 (backend 디렉터리에서):
    .venv/Scripts/python.exe scripts/seed_perf.py --db perf.db --reset
    # 측정할 때는 같은 파일을 가리키도록 설정합니다
    LEDGER_DATABASE_URL=sqlite:///./perf.db uvicorn app.main:app

계정 정보는 아래 상수에 있습니다. 이 계정은 개발 전용이며 운영에 쓰면 안 됩니다.
"""

import argparse
import random
import sys
from datetime import timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import insert, select  # noqa: E402

from app.core.clock import SystemClock  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import make_engine, make_session_factory  # noqa: E402
from app.lib.dates import current_year_month_kst, month_bounds, months_ending_at, today_kst  # noqa: E402
from app.models import Budget, Category, Transaction  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402

PERF_EMAIL = "perf@example.com"
PERF_PASSWORD = "perf-only-1234"  # 개발 전용 값
PERF_NICKNAME = "성능측정"
DEFAULT_COUNT = 10_000
SEED = 20261113
PROTECTED_NAME = "ledger.db"  # 운영 DB 파일 이름. 이 이름으로는 실행하지 않습니다.
TOTAL_BUDGET = 2_000_000
FOOD_BUDGET = 1_000_000


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="성능 측정용 거래 시드 데이터를 만듭니다 (개발 전용).")
    parser.add_argument("--db", default="perf.db", help="만들 SQLite 파일 경로 (기본 perf.db)")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="거래 건수 (기본 10,000)")
    parser.add_argument("--reset", action="store_true", help="파일이 있으면 지우고 새로 만듭니다")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    path = Path(args.db).resolve()
    if path.name == PROTECTED_NAME:
        print(f"거부: {PROTECTED_NAME}은 운영 DB 이름입니다. 다른 파일 이름을 쓰세요.")
        return 2
    if path.exists():
        if not args.reset:
            print(f"거부: {path} 파일이 이미 있습니다. 지우고 다시 만들려면 --reset을 쓰세요.")
            return 2
        path.unlink()

    settings = Settings(_env_file=None, database_url=f"sqlite:///{path.as_posix()}")
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    clock = SystemClock()
    db = make_session_factory(engine)()
    try:
        user_id = AuthService(db, clock, settings).signup(PERF_EMAIL, PERF_PASSWORD, PERF_NICKNAME).user.id
        counts = _seed(db, user_id, args.count, clock.now())
    finally:
        db.close()
        engine.dispose()

    print(f"완료: {path}")
    print(f"  계정: {PERF_EMAIL} / {PERF_PASSWORD} (개발 전용)")
    print(f"  거래: {counts['transactions']}건, 예산: {counts['budgets']}건")
    return 0


def _seed(db, user_id: int, count: int, now) -> dict[str, int]:
    categories = list(db.scalars(select(Category).where(Category.user_id == user_id)).all())
    expense = [c for c in categories if c.type == "EXPENSE"]
    income = [c for c in categories if c.type == "INCOME"]
    food = next(c for c in expense if c.name == "식비")

    today = today_kst(now)
    months = months_ending_at(current_year_month_kst(now), 12)
    rng = random.Random(SEED)

    rows = []
    for _ in range(count):
        year_month = rng.choice(months)
        start, end = month_bounds(year_month)
        end = min(end, today)  # 미래 날짜 거래는 만들지 않습니다 (FR-10과 같은 규칙)
        occurred_on = start + timedelta(days=rng.randrange((end - start).days + 1))
        if rng.random() < 0.1:
            category = rng.choice(income)
            row_type, amount = "INCOME", rng.randrange(100_000, 3_000_000, 1_000)
        else:
            category = rng.choice(expense)
            row_type, amount = "EXPENSE", rng.randrange(100, 20_000, 10)
        rows.append(
            {
                "user_id": user_id,
                "category_id": category.id,
                "type": row_type,
                "amount": amount,
                "occurred_on": occurred_on,
                "memo": None,
                "created_at": now,
                "updated_at": now,
            }
        )
    db.execute(insert(Transaction), rows)

    budgets = []
    for year_month in months:
        budgets.append(
            Budget(
                user_id=user_id,
                category_id=None,
                year_month=year_month,
                amount=TOTAL_BUDGET,
                created_at=now,
                updated_at=now,
            )
        )
        budgets.append(
            Budget(
                user_id=user_id,
                category_id=food.id,
                year_month=year_month,
                amount=FOOD_BUDGET,
                created_at=now,
                updated_at=now,
            )
        )
    db.add_all(budgets)
    db.commit()
    return {"transactions": len(rows), "budgets": len(budgets)}


if __name__ == "__main__":
    raise SystemExit(main())
