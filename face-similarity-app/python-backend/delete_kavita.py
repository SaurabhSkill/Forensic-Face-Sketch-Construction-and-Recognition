"""
Delete Kavita Sharma from database
"""

from database import SessionLocal, Criminal

db = SessionLocal()

try:
    # Find and delete Kavita Sharma
    criminal = db.query(Criminal).filter(Criminal.criminal_id == 'CR-2024-002').first()
    
    if criminal:
        db.delete(criminal)
        db.commit()
        print(f"✅ Deleted: {criminal.full_name} (CR-2024-002)")
    else:
        print("❌ Kavita Sharma (CR-2024-002) not found in database")
        
except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
finally:
    db.close()
