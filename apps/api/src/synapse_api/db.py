"""Database engine and session lifecycle."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from synapse_api.config import get_settings

_engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    return _engine


def reset_engine() -> None:
    """Drop a cached engine after tests change configuration."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal(bind=get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
