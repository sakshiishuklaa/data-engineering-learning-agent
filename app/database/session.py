"""Database connection and session helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    return {"check_same_thread": False} if database_url.startswith("sqlite") else {}


def _ensure_sqlite_directory(database_url: str) -> None:
    """Create the parent folder for a file-based SQLite database."""
    prefix = "sqlite:///"
    if database_url.startswith(prefix) and not database_url.startswith("sqlite:///:memory:"):
        database_path = Path(database_url.removeprefix(prefix))
        database_path.parent.mkdir(parents=True, exist_ok=True)


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create an SQLAlchemy engine using the configured URL by default."""
    resolved_url = database_url or get_settings().database_url
    _ensure_sqlite_directory(resolved_url)
    return create_engine(resolved_url, connect_args=_sqlite_connect_args(resolved_url))


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db():
    """Yield a request-scoped database session."""
    database_session = SessionLocal()
    try:
        yield database_session
    finally:
        database_session.close()
