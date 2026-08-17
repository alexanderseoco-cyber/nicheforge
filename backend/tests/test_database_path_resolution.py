from pathlib import Path

from app.core.config import PROJECT_ROOT, resolve_database_url


def test_relative_sqlite_database_path_is_root_invariant():
    expected = (PROJECT_ROOT / "nicheforge.db").resolve().as_posix()
    assert resolve_database_url("sqlite:///./nicheforge.db") == f"sqlite:///{expected}"
    assert resolve_database_url("sqlite:///../nicheforge.db") == f"sqlite:///{expected}"


def test_non_sqlite_database_url_is_unchanged():
    value = "postgresql+psycopg://user:password@localhost/nicheforge"
    assert resolve_database_url(value) == value
