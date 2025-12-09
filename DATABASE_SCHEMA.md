# Database Schema Documentation

## Overview

**Database Type:** SQLite (Development) / PostgreSQL (Production)  
**ORM:** SQLAlchemy  
**Location:** `face-similarity-app/python-backend/criminal_database.db`

---

## Tables

### 1. **users** - Authentication & User Management

Stores admin and officer account information for role-based access control.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique user identifier |
| `full_name` | VARCHAR(255) | NOT NULL | User's full name |
| `department_name` | VARCHAR(255) | NOT NULL | Department/division name |
| `email` | VARCHAR(255) | NOT NULL, INDEXED | User email (can be same for admin & officer) |
| `officer_id` | VARCHAR(100) | NOT NULL, INDEXED | Unique officer/admin ID |
| `password_hash` | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| `role` | VARCHAR(50) | NOT NULL, DEFAULT 'officer' | User role: 'admin' or 'officer' |
| `is_temp_password` | INTEGER | DEFAULT 0 | 1 = temporary password, 0 = changed |
| `created_at` | DATETIME | DEFAULT NOW | Account creation timestamp |
| `last_login` | DATETIME | NULLABLE | Last successful login timestamp |

**Indexes:**
- `email` (non-unique to allow same email for different roles)
- `officer_id`

**Notes:**
- Admin accounts require OTP verification
- Officers with `is_temp_password=1` must change password on first login
- Same email can be used for both admin and officer roles

---

### 2. **otps** - Two-Factor Authentication

Stores one-time passwords for admin login verification.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique OTP record identifier |
| `user_id` | INTEGER | NOT NULL, INDEXED | Foreign key to users.id |
| `otp_hash` | VARCHAR(255) | NOT NULL | Bcrypt hashed OTP code |
| `created_at` | DATETIME | DEFAULT NOW | OTP generation timestamp |
| `expires_at` | DATETIME | NOT NULL | OTP expiration timestamp (5 min) |
| `is_used` | INTEGER | DEFAULT 0 | 0 = unused, 1 = used |

**Indexes:**
- `user_id`

**Notes:**
- OTPs expire after 5 minutes
- Each OTP can only be used once
- Old OTPs are automatically invalidated

---

### 3. **criminals** - Criminal Database

Stores comprehensive forensic profiles with face photos for matching.

#### Basic Identification

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, AUTO INCREMENT | Unique criminal record identifier |
| `criminal_id` | VARCHAR(50) | UNIQUE, NOT NULL, INDEXED | Unique criminal ID (e.g., "CR-0001-TST") |
| `status` | VARCHAR(100) | NOT NULL | Status: "Wanted", "Convicted", "Person of Interest" |
| `full_name` | VARCHAR(255) | NOT NULL | Criminal's full name |
| `aliases` | JSON | NULLABLE | Array of known aliases |
| `dob` | VARCHAR(50) | NULLABLE | Date of birth |
| `sex` | VARCHAR(50) | NULLABLE | Gender |
| `nationality` | VARCHAR(100) | NULLABLE | Nationality |
| `ethnicity` | VARCHAR(100) | NULLABLE | Ethnicity |

#### Photo Data

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `photo_data` | BLOB | NOT NULL | Binary photo data (JPEG/PNG) |
| `photo_filename` | VARCHAR(255) | NOT NULL | Original filename |

#### Forensic Data (JSON Columns)

| Column | Type | Description | JSON Structure |
|--------|------|-------------|----------------|
| `appearance` | JSON | Physical characteristics | `{height, weight, build, hair, eyes, marks, tattoos, scars}` |
| `locations` | JSON | Location information | `{city, state, country, lastSeen, knownAddresses}` |
| `summary` | JSON | Criminal summary | `{charges, modus, risk, priorConvictions}` |
| `forensics` | JSON | Forensic identifiers | `{fingerprintId, dnaProfile, gait, voiceprint}` |
| `evidence` | JSON | Evidence items | Array of evidence objects |
| `witness` | JSON | Witness information | `{statements, credibility, contactInfo}` |

#### Metadata

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `created_at` | DATETIME | DEFAULT NOW | Record creation timestamp |
| `updated_at` | DATETIME | DEFAULT NOW, AUTO UPDATE | Last modification timestamp |

**Indexes:**
- `criminal_id` (unique)

---

## JSON Column Structures

### appearance
```json
{
  "height": "6'2\"",
  "weight": "185 lbs",
  "build": "Athletic",
  "hair": "Brown",
  "eyes": "Blue",
  "marks": "Scar on left cheek",
  "tattoos": "Dragon on right arm",
  "scars": "Surgical scar on abdomen"
}
```

### locations
```json
{
  "city": "New York",
  "state": "NY",
  "country": "USA",
  "lastSeen": "2024-01-15",
  "knownAddresses": ["123 Main St", "456 Oak Ave"]
}
```

### summary
```json
{
  "charges": "Armed Robbery, Assault",
  "modus": "Uses stolen vehicles",
  "risk": "High",
  "priorConvictions": "3 felonies"
}
```

### forensics
```json
{
  "fingerprintId": "FP-12345",
  "dnaProfile": "DNA-67890",
  "gait": "Slight limp on right leg",
  "voiceprint": "VP-ABCDE"
}
```

### evidence
```json
[
  {
    "type": "Fingerprint",
    "location": "Crime scene A",
    "date": "2024-01-10"
  },
  {
    "type": "DNA",
    "location": "Vehicle",
    "date": "2024-01-12"
  }
]
```

### witness
```json
{
  "statements": "Seen fleeing the scene",
  "credibility": "High",
  "contactInfo": "Witness ID: W-001"
}
```

---

## Relationships

```
users (1) ----< (many) otps
  └─ user_id foreign key relationship

criminals (standalone table, no foreign keys)
```

---

## Database Configuration

### SQLite (Development)
```python
DATABASE_URL = 'sqlite:///criminal_database.db'
```

**Settings:**
- `pool_pre_ping=True` - Check connection health
- `check_same_thread=False` - Allow multi-threading

### PostgreSQL (Production)
```python
DATABASE_URL = 'postgresql://user:pass@host:port/dbname'
```

**Settings:**
- `pool_size=10` - Connection pool size
- `max_overflow=20` - Max overflow connections
- `pool_pre_ping=True` - Check connection health
- `pool_recycle=300` - Recycle connections every 5 min

---

## Key Features

### 1. **Role-Based Access Control**
- Admin: Full access + OTP verification
- Officer: Limited access, no OTP required

### 2. **Flexible Email System**
- Same email can be used for admin and officer roles
- Allows testing with personal Gmail for both roles

### 3. **JSON Storage**
- Flexible schema for forensic data
- Easy to extend without migrations
- Compatible with SQLite and PostgreSQL

### 4. **Binary Photo Storage**
- Photos stored as BLOB in database
- No file system dependencies
- Portable across environments

### 5. **Automatic Timestamps**
- `created_at` - Set on record creation
- `updated_at` - Auto-updated on modification
- `last_login` - Tracks user activity

---

## Database Operations

### Create Tables
```python
from database import create_tables
create_tables()
```

### Get Database Session
```python
from database import get_db

db = next(get_db())
# Use db for queries
db.close()
```

### Example Queries

**Get all criminals:**
```python
criminals = db.query(Criminal).all()
```

**Find user by email:**
```python
user = db.query(User).filter(User.email == email, User.role == 'admin').first()
```

**Add new criminal:**
```python
criminal = Criminal(
    criminal_id="CR-0001",
    full_name="John Doe",
    status="Wanted",
    photo_data=photo_bytes,
    photo_filename="john_doe.jpg"
)
db.add(criminal)
db.commit()
```

---

## Migration & Backup

### Recreate Database
```bash
cd face-similarity-app/python-backend
python recreate_database.py
```

### Backup Database
```bash
# SQLite
cp criminal_database.db criminal_database_backup.db

# PostgreSQL
pg_dump dbname > backup.sql
```

---

## Security Considerations

1. **Password Hashing**: Bcrypt with salt
2. **OTP Hashing**: Bcrypt for OTP codes
3. **No Plain Text**: All sensitive data hashed
4. **Session Management**: JWT tokens for API
5. **SQL Injection**: Protected by SQLAlchemy ORM

---

**Last Updated**: December 9, 2025  
**Database Version**: 2.0 (V2 Authentication System)
