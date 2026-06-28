"""SQLite database setup and session management."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Set

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from src.vialpilot.config import DATA_DIR, DATABASE_URL

logger = logging.getLogger(__name__)

DATA_DIR.mkdir(parents=True, exist_ok=True)

if DATABASE_URL.endswith(":memory:") or DATABASE_URL.rstrip("/").endswith(":memory:"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
elif DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _sqlite_columns(table: str) -> Set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {row[1] for row in rows}


def _migrate_sqlite() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return

    from src.vialpilot.db.models import RunRecord  # noqa: F401

    expected = {
        "run_meta": "TEXT NOT NULL DEFAULT '{}'",
        "current_agent": "VARCHAR(64)",
    }

    existing = _sqlite_columns("runs")
    with engine.begin() as conn:
        for col, typedef in expected.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE runs ADD COLUMN {col} {typedef}"))
                logger.info("Migrated runs table: added column %s", col)


def init_db() -> None:
    from src.vialpilot.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()