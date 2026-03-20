"""
Production-ready SQLAlchemy 2.0 models — PostgreSQL-first.

Changes from legacy database.py:
  - SQLAlchemy 2.0 style: DeclarativeBase, Mapped[], mapped_column()
  - All FK constraints are now enforced at the DB level
  - Full relationship() graph with proper cascade rules
  - Integer booleans → Boolean
  - JSONEncodedDict (TEXT) → JSONB (PostgreSQL native)
  - LargeBinary photo_data → photo_url String (S3/Supabase)
  - linked_criminals / linked_evidence → association tables (many-to-many)
  - DateTime → DateTime(timezone=True) for UTC-aware timestamps
  - server_default used alongside Python defaults for DB-level safety
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Utility: timezone-aware UTC now
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Association tables (many-to-many)
# ---------------------------------------------------------------------------

# Links cases ↔ criminals (replaces linked_criminals JSON string)
case_criminals = Table(
    "case_criminals",
    Base.metadata,
    Column("case_id", Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("criminal_id", Integer, ForeignKey("criminals.id", ondelete="CASCADE"), primary_key=True),
)

# Links cases ↔ evidence items (replaces linked_evidence JSON string)
case_evidence = Table(
    "case_evidence",
    Base.metadata,
    Column("case_id", Integer, ForeignKey("cases.id", ondelete="CASCADE"), primary_key=True),
    Column("evidence_id", Integer, ForeignKey("evidence_items.id", ondelete="CASCADE"), primary_key=True),
)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    # NOTE: email is intentionally NOT unique at the table level — the same
    # email address is allowed for different roles (admin + officer).
    # A partial unique index per role is enforced via __table_args__.
    __table_args__ = (
        UniqueConstraint("email", "role", name="uq_users_email_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    officer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # 'admin' | 'officer'
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="officer", server_default="officer")

    # Was Integer(0/1) — now a proper Boolean
    is_temp_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────
    # One user → many OTPs (admin 2FA)
    otps: Mapped[List["OTP"]] = relationship(
        "OTP",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # One officer → many Cases they own
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        back_populates="officer",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="Case.officer_id",
    )

    # One user → many CaseNotes they authored
    case_notes: Mapped[List["CaseNote"]] = relationship(
        "CaseNote",
        back_populates="author",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"


# ---------------------------------------------------------------------------
# OTP  (admin two-factor authentication)
# ---------------------------------------------------------------------------

class OTP(Base):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FK enforced — was just an unlinked Integer before
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Was Integer(0/1) — now Boolean
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="otps")

    def __repr__(self) -> str:
        return f"<OTP id={self.id} user_id={self.user_id} is_used={self.is_used}>"


# ---------------------------------------------------------------------------
# Criminal
# ---------------------------------------------------------------------------

class Criminal(Base):
    __tablename__ = "criminals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Human-readable unique identifier e.g. "CR-0001-TST"
    criminal_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(100), nullable=False)  # Person of Interest / Suspect / Convicted

    # Basic demographics
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)          # ["alias1", "alias2"]
    dob: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)          # kept as string for flexibility
    sex: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ethnicity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Photo — stored in private AWS S3 bucket.
    # photo_key holds the S3 object key (e.g. "criminals/CR-0001/abc.jpg").
    # Use s3_service.get_signed_url(photo_key) to generate a presigned URL.
    photo_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    photo_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    # Face embeddings — JSONB replaces JSONEncodedDict(TEXT).
    # Shape: {"arcface": [...512 floats...], "facenet": [...128 floats...]}
    face_embedding: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    embedding_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Detailed forensic profile — all JSONB for native querying
    appearance: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)   # height, weight, build, hair, eyes, marks…
    locations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)    # city, state, lastSeen, knownAddresses…
    summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)      # charges, modus, risk, priorConvictions…
    forensics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)    # fingerprintId, dnaProfile, gait…
    evidence: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)     # array of evidence items
    witness: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)      # statements, credibility, contactInfo…

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    # Many criminals ↔ many cases (via association table)
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        secondary=case_criminals,
        back_populates="criminals",
    )

    def __repr__(self) -> str:
        return f"<Criminal id={self.id} criminal_id={self.criminal_id!r} name={self.full_name!r}>"


# ---------------------------------------------------------------------------
# EvidenceItem  (new standalone table — replaces linked_evidence JSON string)
# ---------------------------------------------------------------------------

class EvidenceItem(Base):
    """
    Standalone evidence record.
    Previously evidence was an unstructured JSON array inside Criminal and
    a raw JSON string inside Case.linked_evidence.  This table gives each
    piece of evidence a proper identity and allows it to be linked to
    multiple cases via the case_evidence association table.
    """
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_ref: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    evidence_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # photo, fingerprint, DNA…
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)       # S3/Supabase URL
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)  # any extra structured data

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    cases: Mapped[List["Case"]] = relationship(
        "Case",
        secondary=case_evidence,
        back_populates="evidence_items",
    )

    def __repr__(self) -> str:
        return f"<EvidenceItem id={self.id} ref={self.evidence_ref!r}>"


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Open | Closed | Under Investigation
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Open", server_default="Open")
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="Medium", server_default="Medium")
    crime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # FK enforced — was just an unlinked Integer before
    officer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    incident_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # linked_criminals (String JSON) and linked_evidence (String JSON) have been
    # replaced by the case_criminals and case_evidence association tables below.

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    # The officer who owns this case
    officer: Mapped["User"] = relationship(
        "User",
        back_populates="cases",
        foreign_keys=[officer_id],
    )

    # Notes attached to this case — cascade delete when case is deleted
    notes: Mapped[List["CaseNote"]] = relationship(
        "CaseNote",
        back_populates="case",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="CaseNote.created_at.desc()",
    )

    # Many-to-many: criminals linked to this case
    criminals: Mapped[List["Criminal"]] = relationship(
        "Criminal",
        secondary=case_criminals,
        back_populates="cases",
    )

    # Many-to-many: evidence items linked to this case
    evidence_items: Mapped[List["EvidenceItem"]] = relationship(
        "EvidenceItem",
        secondary=case_evidence,
        back_populates="cases",
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} case_number={self.case_number!r} status={self.status!r}>"


# ---------------------------------------------------------------------------
# CaseNote
# ---------------------------------------------------------------------------

class CaseNote(Base):
    __tablename__ = "case_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    case_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Denormalized for display convenience — kept intentionally so notes
    # remain readable even if the author account is later anonymised.
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    # ── Relationships ──────────────────────────────────────────────────────
    case: Mapped["Case"] = relationship("Case", back_populates="notes")
    author: Mapped["User"] = relationship("User", back_populates="case_notes")

    def __repr__(self) -> str:
        return f"<CaseNote id={self.id} case_id={self.case_id} author={self.author_name!r}>"
