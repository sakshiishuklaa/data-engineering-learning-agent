"""Logging setup shared by application entry points."""

import logging


def configure_logging(level: str) -> None:
    """Configure process logging once with a concise, useful format."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
