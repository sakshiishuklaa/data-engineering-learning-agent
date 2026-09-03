"""Database initialization routines."""

from app.database.base import Base
from app.database.session import engine


def initialize_database() -> None:
    """Create registered tables. Module 0 intentionally has no domain tables yet."""
    Base.metadata.create_all(bind=engine)
