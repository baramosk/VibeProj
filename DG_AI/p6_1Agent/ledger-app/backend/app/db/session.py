"""DB 엔진과 세션 팩토리.

SQLAlchemy로만 접근하므로 나중에 PostgreSQL로 옮길 때 DATABASE_URL과 일부 dialect 처리만 바꾸면 됩니다.
"""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def make_engine(database_url: str) -> Engine:
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        # FastAPI 동기 엔드포인트는 여러 스레드에서 실행될 수 있습니다.
        connect_args["check_same_thread"] = False
    engine = create_engine(database_url, connect_args=connect_args)

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
            # SQLite는 외래 키 검사가 기본 꺼져 있어 명시적으로 켭니다.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)
