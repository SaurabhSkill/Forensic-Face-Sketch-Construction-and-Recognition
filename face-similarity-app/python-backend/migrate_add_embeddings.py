"""
Database Migration: Add face_embedding and embedding_version columns
"""

import os
import sys
from sqlalchemy import create_engine, text
from database import DATABASE_URL

def migrate_database():
    """Add face_embedding and embedding_version columns to criminals table"""
    
    print("="*60)
    print("DATABASE MIGRATION: Add Embedding Columns")
    print("="*60)
    
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if columns already exist
            if DATABASE_URL.startswith('sqlite'):
                result = conn.execute(text("PRAGMA table_info(criminals)"))
                columns = [row[1] for row in result]
            else:
                # PostgreSQL
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='criminals'
                """))
                columns = [row[0] for row in result]
            
            # Add face_embedding column if it doesn't exist
            if 'face_embedding' not in columns:
                print("Adding face_embedding column...")
                if DATABASE_URL.startswith('sqlite'):
                    conn.execute(text("ALTER TABLE criminals ADD COLUMN face_embedding TEXT"))
                else:
                    conn.execute(text("ALTER TABLE criminals ADD COLUMN face_embedding TEXT"))
                conn.commit()
                print("✓ face_embedding column added")
            else:
                print("✓ face_embedding column already exists")
            
            # Add embedding_version column if it doesn't exist
            if 'embedding_version' not in columns:
                print("Adding embedding_version column...")
                if DATABASE_URL.startswith('sqlite'):
                    conn.execute(text("ALTER TABLE criminals ADD COLUMN embedding_version VARCHAR(50)"))
                else:
                    conn.execute(text("ALTER TABLE criminals ADD COLUMN embedding_version VARCHAR(50)"))
                conn.commit()
                print("✓ embedding_version column added")
            else:
                print("✓ embedding_version column already exists")
        
        print("\n[SUCCESS] Migration completed successfully!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        print("="*60)
        return False

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
