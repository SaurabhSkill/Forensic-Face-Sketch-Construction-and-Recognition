import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, LargeBinary, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator, TEXT
from datetime import datetime

# Database configuration
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'sqlite:///criminal_database.db'
)


# Create engine with better connection pool settings
if DATABASE_URL.startswith('sqlite'):
    # SQLite specific settings
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300
    )

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class
Base = declarative_base()


# Custom JSON type for SQLite/PostgreSQL compatibility
class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""
    
    impl = TEXT
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


# User model for authentication
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    department_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)  # Removed unique=True to allow same email for different roles
    officer_id = Column(String(100), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='officer')  # 'admin' or 'officer'
    is_temp_password = Column(Integer, default=0)  # 1 if temporary password, 0 if changed
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


# OTP model for admin two-factor authentication
class OTP(Base):
    __tablename__ = "otps"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Integer, default=0)  # 0 = not used, 1 = used


# Criminal model with detailed forensic profile
class Criminal(Base):
    __tablename__ = "criminals"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    criminal_id = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "CR-0001-TST"
    status = Column(String(100), nullable=False)  # e.g., "Person of Interest", "Suspect", "Convicted"
    
    # Basic information
    full_name = Column(String(255), nullable=False)
    aliases = Column(JSONEncodedDict, nullable=True)  # Array of strings
    dob = Column(String(50), nullable=True)  # Date of birth (stored as string for flexibility)
    sex = Column(String(50), nullable=True)
    nationality = Column(String(100), nullable=True)
    ethnicity = Column(String(100), nullable=True)
    
    # Photo data (keep as binary)
    photo_data = Column(LargeBinary, nullable=False)
    photo_filename = Column(String(255), nullable=False)
    
    # Precomputed ArcFace embedding (512-D vector stored as JSON)
    face_embedding = Column(JSONEncodedDict, nullable=True)  # 512-dimensional vector
    embedding_version = Column(String(50), nullable=True)  # Track embedding model version
    
    # Detailed forensic data (JSON columns)
    appearance = Column(JSONEncodedDict, nullable=True)  # {height, weight, build, hair, eyes, marks, tattoos, scars}
    locations = Column(JSONEncodedDict, nullable=True)  # {city, state, country, lastSeen, knownAddresses}
    summary = Column(JSONEncodedDict, nullable=True)  # {charges, modus, risk, priorConvictions}
    forensics = Column(JSONEncodedDict, nullable=True)  # {fingerprintId, dnaProfile, gait, voiceprint}
    evidence = Column(JSONEncodedDict, nullable=True)  # Array of evidence items
    witness = Column(JSONEncodedDict, nullable=True)  # {statements, credibility, contactInfo}
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Case Management model
class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "CASE-2026-001"
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='Open')  # Open, Closed, Under Investigation
    priority = Column(String(50), default='Medium')
    crime_type = Column(String(100), nullable=True)
    
    # Associated Officer
    officer_id = Column(Integer, index=True, nullable=False) # Foreign Key concept pointing to users.id
    
    # Case Details
    incident_date = Column(DateTime, nullable=True)
    location = Column(String(255), nullable=True)
    
    # Store JSON strings for relationships without complex secondary tables for MVP
    linked_criminals = Column(String, default='[]')
    linked_evidence = Column(String, default='[]')
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CaseNote(Base):
    __tablename__ = 'case_notes'
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey('cases.id', ondelete='CASCADE'), index=True)
    author_id = Column(Integer, ForeignKey('users.id'), index=True)
    author_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
