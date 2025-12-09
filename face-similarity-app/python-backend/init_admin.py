"""
Initialize Admin User
Run this script once to create the first admin account
"""

from database import get_db, create_tables, User
from auth_v2 import hash_password

def create_admin():
    """Create default admin user"""
    create_tables()
    
    db = next(get_db())
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.role == 'admin').first()
        
        if existing_admin:
            print("Admin user already exists!")
            print(f"Email: {existing_admin.email}")
            return
        
        # Create admin user
        admin_email = input("Enter admin email (can be Gmail): ").strip()
        admin_password = input("Enter admin password: ").strip()
        admin_name = input("Enter admin full name: ").strip()
        admin_dept = input("Enter admin department: ").strip()
        admin_officer_id = input("Enter admin officer ID: ").strip()
        
        if len(admin_password) < 8:
            print("Error: Password must be at least 8 characters long")
            return
        
        password_hash = hash_password(admin_password)
        
        admin_user = User(
            full_name=admin_name,
            department_name=admin_dept,
            email=admin_email.lower(),
            officer_id=admin_officer_id,
            password_hash=password_hash,
            role='admin',
            is_temp_password=0
        )
        
        db.add(admin_user)
        db.commit()
        
        print("\n" + "=" * 60)
        print("Admin user created successfully!")
        print("=" * 60)
        print(f"Email: {admin_email}")
        print(f"Name: {admin_name}")
        print(f"Role: admin")
        print("=" * 60)
        print("\nYou can now login with these credentials.")
        print("Admin login requires OTP verification.")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating admin: {e}")
    finally:
        db.close()


if __name__ == '__main__':
    create_admin()
