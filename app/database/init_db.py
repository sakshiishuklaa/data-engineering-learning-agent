"""Database initialization routines."""

from app.database.base import Base
from app.database.session import engine
# Import models before metadata creation so every table is registered.
import app.models  # noqa: F401


def initialize_database() -> None:
    """Create all registered application tables."""
    Base.metadata.create_all(bind=engine)
