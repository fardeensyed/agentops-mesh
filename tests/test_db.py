import os


def test_init_db_uses_sqlite_fallback_when_no_database_url_is_set():
    os.environ.pop("DATABASE_URL", None)

    from backend.app.db import engine, init_db

    init_db()

    assert str(engine.url).startswith("sqlite")
