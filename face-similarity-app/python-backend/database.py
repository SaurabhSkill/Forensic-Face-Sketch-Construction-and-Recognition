import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database configuration
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://postgres:%28S212003%40g%29@localhost:5432/criminal_database'
)


# Create engine
engine = create_engine(DATABASE_URL)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class
Base = declarative_base()

# Criminal model
class Criminal(Base):
    __tablename__ = "criminals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    crime = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    photo_data = Column(LargeBinary, nullable=False)  # Store image as binary data
    photo_filename = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

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
