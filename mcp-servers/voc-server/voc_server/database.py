"""Database session and engine management utilities."""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import inspect, text
from sqlalchemy.sql import sqltypes
from sqlmodel import Session, SQLModel, create_engine

from .settings import settings

logger = logging.getLogger(__name__)

_engine = create_engine(settings.database_url, echo=settings.database_echo)
_initialized = False


def init_db() -> None:
    """Create all SQLModel tables if they do not already exist."""
    global _initialized
    if _initialized:
        return

    SQLModel.metadata.create_all(_engine)
    _ensure_long_text_columns()
    _initialized = True


def _ensure_long_text_columns() -> None:
    """Ensure large text columns use unbounded types (e.g., LONGTEXT on MySQL)."""

    if _engine.dialect.name != "mysql":
        return

    target_columns = {
        "transcript_text": "LONGTEXT",
        "summary": "LONGTEXT",
    }

    with _engine.connect() as conn:
        inspector = inspect(conn)
        if "feedback_records" not in inspector.get_table_names():
            return

        columns = inspector.get_columns("feedback_records")
        for column in columns:
            name = column["name"]
            if name not in target_columns:
                continue
            col_type = column["type"]
            if isinstance(col_type, sqltypes.Text):
                continue
            if isinstance(col_type, sqltypes.String):
                desired = target_columns[name]
                logger.info("Altering column feedback_records.%s to %s", name, desired)
                conn.execute(text(f"ALTER TABLE feedback_records MODIFY {name} {desired} NOT NULL"))
        conn.commit()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    with Session(_engine) as session:
        try:
            yield session
            session.commit()
        except Exception:  # pragma: no cover - defensive rollback
            session.rollback()
            raise
