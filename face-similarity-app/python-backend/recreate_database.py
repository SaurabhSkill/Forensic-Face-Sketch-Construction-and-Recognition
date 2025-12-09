"""
Script to recreate the database with updated schema
This will delete the old database and create a new one with the admin user
"""

import os
from database import create_tables
from auth_v2 import hash_password
from database import User, get_db
from datetime import datetime

# Path to database file
DB_FILE = 'criminal_database.db'

def recreate_database():
    """Delete old database and create new one with admin"""
    
    # Delete old database if it exists
    if os.path.exists(DB_FILE):
        print(f"Deleting old database: {DB_FILE}")
        os.remove(DB_FILE)
        print("✓ Old database deleted")
    
    # Create new tables
    print("Creating new database tables...")
    create_tables()
    print("✓ Tables created")
    
    # Create admin user
    print("\nCreating admin user...")
    admin_email = "nickrichard292@gmail.com"
    admin_password = "Admin123!"
    
    db = next(get_db())
    try:
        admin_user = User(
            full_name="Admin",
            department_name="Administration",
            email=admin_email,
            officer_id="ADMIN-001",
            password_hash=hash_password(admin_password),
            role='admin',
            is_temp_password=0,
            created_at=datetime.utcnow()
        )
        
        db.add(admin_user)
        db.commit()
        
        print("✓ Admin user created successfully")
        print(f"\n{'='*60}")
        print("ADMIN CREDENTIALS:")
        print(f"{'='*60}")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
        print(f"{'='*60}")
        print("\nDatabase recreated successfully!")
        print("You can now:")
        print("1. Login as admin")
        print("2. Add yourself as an officer using the same email")
        print("3. Test the officer portal")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating admin: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    recreate_database()
