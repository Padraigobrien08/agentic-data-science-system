"""Engine and session factory — sync SQLAlchemy, one session per request in FastAPI."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config.settings import get_settings

_settings = get_settings()

_is_sqlite = _settings.database_url.startswith("sqlite")
_connect_args = {}
if _is_sqlite:
    _connect_args["check_same_thread"] = False

engine: Engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

if _is_sqlite:
    # WAL lets progress pollers read while an execution commits phase-by-phase;
    # busy_timeout avoids spurious "database is locked" under that concurrency.
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a session and always close."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
