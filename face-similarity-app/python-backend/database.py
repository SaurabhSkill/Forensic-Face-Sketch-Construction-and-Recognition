"""
database.py — PostgreSQL engine, session factory, and model re-exports.

All model definitions live in db_models.py.
Backward-compatible: existing imports like
    from database import User, Criminal, get_db, create_tables
continue to work without any changes in app_v2.py.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from db_models import Base  # noqa: F401
from db_models import Case, CaseNote, Criminal, EvidenceItem, OTP, User  # noqa: F401 — re-exported

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

load_dotenv()

DATABASE_URL: str = os.environ["DATABASE_URL"]  # hard-fail fast if not set

# ---------------------------------------------------------------------------
# Engine — PostgreSQL only
# ---------------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    future=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoids lazy-load errors after commit in Flask
)

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Generator-based session dependency.

    Flask usage:
        db = next(get_db())
        ...
        db.close()
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context-manager session for use outside of request scope
    (scripts, background tasks, startup hooks).

    Usage:
        with db_session() as db:
            db.query(User).all()
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def create_tables() -> None:
    """
    Create all tables that don't yet exist.
    For schema changes on an existing DB, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)


def check_connection() -> bool:
    """Verify the database is reachable. Returns True on success."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Connected to database successfully")
        return True
    except Exception as exc:
        print(f"❌ Failed to connect to database: {exc}", flush=True)
        return False


# ---------------------------------------------------------------------------
# Startup connection check — runs once when this module is first imported.
# Prints a clear terminal message so both local and EC2 environments confirm
# the DB is reachable before the Flask app begins serving requests.
# ---------------------------------------------------------------------------
check_connection()
