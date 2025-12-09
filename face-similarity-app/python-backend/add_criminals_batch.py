"""
Batch Add Criminals to Database
Safe script to add multiple criminals with complete details
"""

import json
from datetime import datetime
from database import SessionLocal, Criminal

def add_criminal_to_db(criminal_data, photo_path):
    """
    Add a single criminal to the database
    
    Args:
        criminal_data: Dictionary with all criminal details
        photo_path: Path to the criminal's photo file
    """
    db = SessionLocal()
    
    try:
        # Read photo file
        with open(photo_path, 'rb') as f:
            photo_bytes = f.read()
        
        # Extract photo filename
        photo_filename = photo_path.split('\\')[-1].split('/')[-1]
        
        # Create criminal record
        criminal = Criminal(
            # Required fields
            criminal_id=criminal_data['criminal_id'],
            status=criminal_data['status'],
            full_name=criminal_data['full_name'],
            photo_data=photo_bytes,
            photo_filename=photo_filename,
            
            # Optional basic info
            aliases=json.dumps(criminal_data.get('aliases', [])),
            dob=criminal_data.get('dob'),
            sex=criminal_data.get('sex'),
            nationality=criminal_data.get('nationality'),
            ethnicity=criminal_data.get('ethnicity'),
            
            # Physical appearance
            appearance=json.dumps(criminal_data.get('appearance', {})),
            
            # Location info
            locations=json.dumps(criminal_data.get('locations', {})),
            
            # Criminal history
            summary=json.dumps(criminal_data.get('summary', {})),
            
            # Forensic data
            forensics=json.dumps(criminal_data.get('forensics', {})),
            
            # Evidence
            evidence=json.dumps(criminal_data.get('evidence', [])),
            
            # Witness info
            witness=json.dumps(criminal_data.get('witness', {}))
        )
        
        # Add to database
        db.add(criminal)
        db.commit()
        
        print(f"✅ Successfully added: {criminal_data['full_name']} ({criminal_data['criminal_id']})")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error adding {criminal_data.get('full_name', 'Unknown')}: {str(e)}")
        return False
        
    finally:
        db.close()


# ============================================================================
# CRIMINAL DATA - ADD YOUR CRIMINALS HERE
# ============================================================================

criminals_to_add = [
    # Criminal 1: Kavita Sharma
    {
        'criminal_id': 'CR-2024-002',
        'status': 'Under Investigation',
        'full_name': 'Kavita Sharma',
        
        # Optional fields
        'aliases': ['Kavi'],
        'dob': '1992-11-10',
        'sex': 'Female',
        'nationality': 'Indian',
        'ethnicity': 'Asian',
        
        # Physical appearance
        'appearance': {
            'height': '162 cm',
            'weight': '58 kg',
            'build': 'Slim',
            'hair': 'Brown, straight',
            'eyes': 'Black',
            'marks': 'Mole on right cheek',
            'tattoos': '',
            'scars': ''
        },
        
        # Location
        'locations': {
            'city': 'Jaipur',
            'state': 'Rajasthan',
            'country': 'India',
            'lastSeen': '2024-09-12',
            'knownAddresses': [
                'Mansarovar Colony, Jaipur',
                'PG in Vaishali Nagar'
            ]
        },
        
        # Criminal history
        'summary': {
            'charges': 'Online scam, identity fraud',
            'modus': 'Uses fake profiles, transfers money through proxies',
            'risk': 'Medium',
            'priorConvictions': 'None'
        },
        
        # Forensics
        'forensics': {
            'fingerprintId': 'FP-KAV-118',
            'dnaProfile': 'DNA-KAV-221',
            'gait': 'Normal',
            'voiceprint': 'VP-KAVITA-09'
        },
        
        # Evidence
        'evidence': [
            {
                'type': 'Documents',
                'location': 'Laptop recovered from PG',
                'date': '2024-09-15',
                'caseNumber': 'CS-2024-312'
            }
        ],
        
        # Witness
        'witness': {
            'statements': 'Often seen meeting unknown men at cafés.',
            'credibility': 'Low',
            'contactInfo': 'Witness ID: W-089'
        },
        
        # Photo path
        'photo_path': r'C:\Users\Dell\Downloads\Forensic-face\kavita.png'
    }
]


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("BATCH ADD CRIMINALS TO DATABASE")
    print("=" * 60)
    print()
    
    success_count = 0
    fail_count = 0
    
    for criminal_data in criminals_to_add:
        photo_path = criminal_data.pop('photo_path')  # Remove photo_path from data
        
        if add_criminal_to_db(criminal_data, photo_path):
            success_count += 1
        else:
            fail_count += 1
        
        print()
    
    print("=" * 60)
    print(f"SUMMARY: ✅ {success_count} added, ❌ {fail_count} failed")
    print("=" * 60)
