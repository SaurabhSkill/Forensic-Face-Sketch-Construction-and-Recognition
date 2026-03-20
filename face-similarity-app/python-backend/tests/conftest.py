"""
tests/conftest.py
─────────────────
Pytest fixtures for Flask + SQLAlchemy integration tests.

Strategy
────────
- Requires DATABASE_URL to be set (PostgreSQL via Supabase)
- Wraps every test in a transaction that is rolled back → clean state, no teardown
- Mocks Supabase Storage so photo uploads never hit a real bucket
- Mocks embedding services so AI tests are fast and deterministic
"""

from __future__ import annotations

import io
import os
import sys
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# ── 1. Load .env BEFORE any app module is imported ────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..")
load_dotenv(dotenv_path=os.path.join(_ROOT, ".env"), override=False)

if not os.environ.get("DATABASE_URL"):
    raise RuntimeError(
        "DATABASE_URL is not set. Tests require a PostgreSQL connection. "
        "Copy .env.example to .env and fill in your Supabase credentials."
    )

# Ensure required env vars have test-safe defaults
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-access-key")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret-key")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_S3_BUCKET_NAME", "test-bucket")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")

# ── 2. Stub out `boto3` S3 client if needed ───────────────────────────────

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from auth_v2 import generate_token, hash_password
from db_models import Base, Case, CaseNote, Criminal, EvidenceItem, OTP, User

# ── 3. Build the test engine (PostgreSQL) ─────────────────────────────────

TEST_ENGINE = create_engine(os.environ["DATABASE_URL"], future=True)
TestSessionLocal = sessionmaker(bind=TEST_ENGINE, autocommit=False, autoflush=False)


# ── 4. Session-scoped schema creation ─────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def create_schema():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


# ── 5. Per-test rolled-back DB session ────────────────────────────────────

@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """
    Provide a DB session wrapped in a transaction that is rolled back after
    each test, keeping the DB clean without any teardown scripts.
    """
    connection = TEST_ENGINE.connect()
    transaction = connection.begin()
    session = TestSessionLocal(bind=connection)

    with patch("database.SessionLocal", return_value=session):
        yield session

    session.close()
    transaction.rollback()
    connection.close()


# ── 6. Image helpers ──────────────────────────────────────────────────────

@pytest.fixture()
def sample_image_bytes() -> bytes:
    """Minimal valid 1×1 white JPEG."""
    return bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
        0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
        0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00, 0xFB, 0xD2,
        0x8A, 0x28, 0x03, 0xFF, 0xD9,
    ])


@pytest.fixture()
def sample_image_file(sample_image_bytes) -> io.BytesIO:
    buf = io.BytesIO(sample_image_bytes)
    buf.name = "test_photo.jpg"
    return buf


# ── 7. User fixtures ──────────────────────────────────────────────────────

@pytest.fixture()
def admin_user(db: Session) -> User:
    user = User(
        full_name="Test Admin",
        department_name="Administration",
        email="admin@forensic.gov.in",
        officer_id="ADMIN-TEST-001",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        is_temp_password=False,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def officer_user(db: Session) -> User:
    user = User(
        full_name="Test Officer",
        department_name="Forensics",
        email="officer@forensic.gov.in",
        officer_id="OFF-TEST-001",
        password_hash=hash_password("OfficerPass123!"),
        role="officer",
        is_temp_password=False,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def admin_token(admin_user: User) -> str:
    return generate_token(admin_user.id, admin_user.email, admin_user.role)


@pytest.fixture()
def officer_token(officer_user: User) -> str:
    return generate_token(officer_user.id, officer_user.email, officer_user.role)


@pytest.fixture()
def auth_headers_admin(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def auth_headers_officer(officer_token: str) -> dict:
    return {"Authorization": f"Bearer {officer_token}"}


# ── 8. Domain fixtures ────────────────────────────────────────────────────

FAKE_EMBEDDING = {"arcface": [0.1] * 512, "facenet": [0.2] * 128}


@pytest.fixture()
def criminal(db: Session) -> Criminal:
    c = Criminal(
        criminal_id="CR-TEST-001",
        status="Suspect",
        full_name="John Doe",
        aliases=["JD", "Johnny"],
        photo_key="criminals/CR-TEST-001/photo.jpg",
        photo_filename="photo.jpg",
        face_embedding=FAKE_EMBEDDING,
        embedding_version="v2",
        appearance={"height": "5ft10", "build": "medium"},
        locations={"city": "Mumbai"},
        summary={},
        forensics={},
        evidence=[],
        witness={},
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture()
def case(db: Session, officer_user: User) -> Case:
    c = Case(
        case_number="CASE-2026-TEST-0001",
        title="Test Case",
        description="A test case",
        status="Open",
        priority="High",
        crime_type="Robbery",
        officer_id=officer_user.id,
        location="Mumbai",
    )
    db.add(c)
    db.flush()
    return c


# ── 9. Flask test client ──────────────────────────────────────────────────

@pytest.fixture()
def client(db: Session):
    """
    Flask test client with get_db() overridden to use the test session
    and Supabase storage fully mocked.
    """
    mock_storage = MagicMock()
    mock_storage.return_value = "criminals/CR-NEW-001/abc123.jpg"

    with patch("services.s3_service.upload_criminal_photo", mock_storage), \
         patch("services.s3_service.delete_criminal_photo", return_value=True):

        import app_v2 as flask_app_module

        flask_app_module.app.config["TESTING"] = True
        flask_app_module.app.config["WTF_CSRF_ENABLED"] = False

        with flask_app_module.app.test_client() as c:
            yield c


# ── 10. Embedding mock ────────────────────────────────────────────────────

@pytest.fixture()
def mock_embedding():
    """Patch embedding extraction to return deterministic fake vectors."""
    import numpy as np
    fake = {
        "success": True,
        "arcface": np.array([0.1] * 512),
        "facenet": np.array([0.2] * 128),
        "aligned_face": np.zeros((112, 112, 3), dtype=np.uint8),
    }
    with patch("services.embedding_service.extract_dual_embeddings", return_value=fake), \
         patch("app_v2.extract_dual_embeddings", return_value=fake):
        yield fake
