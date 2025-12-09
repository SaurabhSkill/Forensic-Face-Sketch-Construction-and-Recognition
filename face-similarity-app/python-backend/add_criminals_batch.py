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
    # Criminal 1: [PASTE YOUR FIRST CRIMINAL DETAILS HERE]
    {
        'criminal_id': 'CR-2024-002',
        'status': 'Wanted',
        'full_name': 'Criminal Name Here',
        
        # Optional fields
        'aliases': ['Alias1', 'Alias2'],
        'dob': '1990-01-01',
        'sex': 'Male',
        'nationality': 'Indian',
        'ethnicity': 'Asian',
        
        # Physical appearance
        'appearance': {
            'height': '175 cm',
            'weight': '70 kg',
            'build': 'Athletic',
            'hair': 'Black, short',
            'eyes': 'Brown',
            'marks': 'Scar on left cheek',
            'tattoos': 'Dragon on right arm',
            'scars': 'None'
        },
        
        # Location
        'locations': {
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'country': 'India',
            'lastSeen': '2024-12-01',
            'knownAddresses': [
                'Address line 1',
                'Address line 2'
            ]
        },
        
        # Criminal history
        'summary': {
            'charges': 'Armed robbery, assault',
            'modus': 'Operates at night',
            'risk': 'High',
            'priorConvictions': '2 felonies'
        },
        
        # Forensics
        'forensics': {
            'fingerprintId': 'FP-XXX-2024',
            'dnaProfile': 'DNA-XXX-001',
            'gait': 'Normal',
            'voiceprint': 'VP-XXX-001'
        },
        
        # Evidence
        'evidence': [
            {
                'type': 'Weapon',
                'location': 'Crime scene',
                'date': '2024-12-01',
                'caseNumber': 'CS-2024-001'
            }
        ],
        
        # Witness
        'witness': {
            'statements': 'Seen fleeing the scene',
            'credibility': 'High',
            'contactInfo': 'Witness ID: W-001'
        },
        
        # Photo path (IMPORTANT: Update this path!)
        'photo_path': 'path/to/criminal1_photo.jpg'
    },
    
    # Criminal 2: [PASTE YOUR SECOND CRIMINAL DETAILS HERE]
    {
        'criminal_id': 'CR-2024-003',
        'status': 'Wanted',
        'full_name': 'Another Criminal Name',
        
        # Optional fields
        'aliases': ['Alias1', 'Alias2'],
        'dob': '1985-05-15',
        'sex': 'Female',
        'nationality': 'Indian',
        'ethnicity': 'Asian',
        
        # Physical appearance
        'appearance': {
            'height': '165 cm',
            'weight': '60 kg',
            'build': 'Slim',
            'hair': 'Black, long',
            'eyes': 'Brown',
            'marks': 'Birthmark on neck',
            'tattoos': 'None',
            'scars': 'None'
        },
        
        # Location
        'locations': {
            'city': 'Delhi',
            'state': 'Delhi',
            'country': 'India',
            'lastSeen': '2024-11-20',
            'knownAddresses': [
                'Address line 1',
                'Address line 2'
            ]
        },
        
        # Criminal history
        'summary': {
            'charges': 'Fraud, forgery',
            'modus': 'Uses fake documents',
            'risk': 'Medium',
            'priorConvictions': '1 felony'
        },
        
        # Forensics
        'forensics': {
            'fingerprintId': 'FP-YYY-2024',
            'dnaProfile': 'DNA-YYY-001',
            'gait': 'Normal',
            'voiceprint': 'VP-YYY-001'
        },
        
        # Evidence
        'evidence': [
            {
                'type': 'Documents',
                'location': 'Office raid',
                'date': '2024-11-15',
                'caseNumber': 'CS-2024-002'
            }
        ],
        
        # Witness
        'witness': {
            'statements': 'Seen at the bank',
            'credibility': 'Medium',
            'contactInfo': 'Witness ID: W-002'
        },
        
        # Photo path (IMPORTANT: Update this path!)
        'photo_path': 'path/to/criminal2_photo.jpg'
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
