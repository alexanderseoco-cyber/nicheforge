from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_auth_migration_upgrade_on_isolated_database(tmp_path):
    database = tmp_path / "auth-migration.sqlite"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    command.upgrade(config, "c12authidentity")
    names = set(inspect(create_engine(f"sqlite:///{database.as_posix()}")).get_table_names())
    assert {"users", "user_sessions"}.issubset(names)
