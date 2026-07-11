from collections.abc import Generator

import time

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.performance import record_db_duration


settings = get_settings()

engine_options: dict[str, object] = {"pool_pre_ping": True}
if not settings.sqlalchemy_database_url.startswith("sqlite"):
    engine_options.update(
        pool_size=max(1, settings.database_pool_size),
        max_overflow=max(0, settings.database_max_overflow),
        pool_timeout=max(1, settings.database_pool_timeout_seconds),
        pool_recycle=max(30, settings.database_pool_recycle_seconds),
    )

engine = create_engine(settings.sqlalchemy_database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "before_cursor_execute")
def _before_cursor_execute(
    _conn: Connection,
    _cursor: object,
    _statement: str,
    _parameters: object,
    context: object,
    _executemany: bool,
) -> None:
    setattr(context, "_febgrid_query_started", time.perf_counter())


@event.listens_for(Engine, "after_cursor_execute")
def _after_cursor_execute(
    _conn: Connection,
    _cursor: object,
    _statement: str,
    _parameters: object,
    context: object,
    _executemany: bool,
) -> None:
    started = getattr(context, "_febgrid_query_started", None)
    if isinstance(started, float):
        record_db_duration((time.perf_counter() - started) * 1000)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
