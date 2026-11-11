"""마이그레이션 검증 (NFR-23): 마이그레이션 이력으로 만든 스키마가 모델과 일치해야 합니다."""

from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db.base import Base
from app.db.session import make_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["database_url"] = database_url
    return config


def test_NFR23_migration_history_matches_models(settings, tmp_path):
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    command.upgrade(_alembic_config(url), "head")

    engine = make_engine(url)
    try:
        with engine.connect() as connection:
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        assert differences == []

        tables = set(inspect(engine).get_table_names())
        assert {"users", "auth_sessions", "categories", "transactions", "budgets", "notifications"} <= tables
    finally:
        engine.dispose()


def test_NFR23_downgrade_then_upgrade_round_trip(tmp_path):
    url = f"sqlite:///{(tmp_path / 'roundtrip.db').as_posix()}"
    config = _alembic_config(url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = make_engine(url)
    try:
        assert "transactions" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
