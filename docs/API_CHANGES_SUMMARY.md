# API Changes Summary - Step 2 Complete

## Updated Backend API Endpoints

### 1. **POST /api/criminals** (Add Criminal)
**Updated to accept detailed forensic profile**

**Request Format:**
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `photo` (file) - Criminal photo (required)
  - `data` (text) - JSON string containing the complete profile (required)

**JSON Data Structure:**
```json
{
  "criminal_id": "CR-0001-TST",
  "status": "Person of Interest",
  "full_name": "John Doe",
  "aliases": ["Johnny", "JD"],
  "dob": "1990-01-15",
  "sex": "Male",
  "nationality": "American",
  "ethnicity": "Caucasian",
  "appearance": {
    "height": "6'2\"",
    "weight": "180 lbs",
    "build": "Athletic",
    "hair": "Brown",
    "eyes": "Blue",
    "marks": "Scar on left cheek",
    "tattoos": "Dragon on right arm",
    "scars": "Knife wound on abdomen"
  },
  "locations": {
    "city": "New York",
    "state": "NY",
    "country": "USA",
    "lastSeen": "2024-12-01",
    "knownAddresses": ["123 Main St", "456 Oak Ave"]
  },
  "summary": {
    "charges": "Armed Robbery",
    "modus": "Uses disguises",
    "risk": "High",
    "priorConvictions": 3
  },
  "forensics": {
    "fingerprintId": "FP-12345",
    "dnaProfile": "DNA-67890",
    "gait": "Slight limp on right leg",
    "voiceprint": "VP-11223"
  },
  "evidence": ["Security footage", "Fingerprints", "Witness testimony"],
  "witness": {
    "statements": "Seen fleeing the scene",
    "credibility": "High",
    "contactInfo": "witness@email.com"
  }
}
```

**Response:**
```json
{
  "message": "Criminal added successfully",
  "criminal": {
    "id": 1,
    "criminal_id": "CR-0001-TST",
    "status": "Person of Interest",
    "full_name": "John Doe",
    ... (all fields returned)
  }
}
```

---

### 2. **GET /api/criminals** (Get All Criminals)
**Updated to return detailed forensic profiles**

**Response:**
```json
{
  "criminals": [
    {
      "id": 1,
      "criminal_id": "CR-0001-TST",
      "status": "Person of Interest",
      "full_name": "John Doe",
      "aliases": ["Johnny", "JD"],
      "dob": "1990-01-15",
      "sex": "Male",
      "nationality": "American",
      "ethnicity": "Caucasian",
      "photo_filename": "photo.jpg",
      "appearance": {...},
      "locations": {...},
      "summary": {...},
      "forensics": {...},
      "evidence": [...],
      "witness": {...},
      "created_at": "2024-12-07T10:00:00",
      "updated_at": "2024-12-07T10:00:00"
    }
  ]
}
```

---

### 3. **GET /api/criminals/:id** (Get Single Criminal)
**New endpoint to retrieve detailed profile of a single criminal**

**Response:**
```json
{
  "criminal": {
    "id": 1,
    "criminal_id": "CR-0001-TST",
    ... (all detailed fields)
  }
}
```

---

### 4. **PUT /api/criminals/:id** (Update Criminal)
**New endpoint to update existing criminal profile**

**Request Format:**
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `data` (text) - JSON string with fields to update (required)
  - `photo` (file) - New photo (optional)

**Response:**
```json
{
  "message": "Criminal updated successfully",
  "criminal": {
    ... (updated criminal data)
  }
}
```

---

### 5. **POST /api/criminals/search** (Search by Sketch)
**Updated to return detailed forensic profiles in matches**

**Response:**
```json
{
  "matches": [
    {
      "criminal": {
        "id": 1,
        "criminal_id": "CR-0001-TST",
        "full_name": "John Doe",
        ... (all detailed fields)
      },
      "similarity_score": 0.85,
      "distance": 0.15,
      "verified": true
    }
  ],
  "total_matches": 1,
  "threshold_used": 0.6
}
```

---

### 6. **DELETE /api/criminals/:id** (Delete Criminal)
**No changes - works as before**

---

## Key Changes Summary:

✅ **POST /api/criminals** - Now accepts `data` field with JSON string containing detailed profile
✅ **GET /api/criminals** - Returns all detailed fields for each criminal
✅ **GET /api/criminals/:id** - New endpoint for single criminal retrieval
✅ **PUT /api/criminals/:id** - New endpoint for updating criminal profiles
✅ **POST /api/criminals/search** - Returns detailed profiles in search results
✅ All JSON fields are automatically serialized/deserialized by SQLAlchemy
✅ Backward compatible with photo storage (binary data)

---

## Required Fields:
- `criminal_id` (unique identifier)
- `full_name` (criminal's name)
- `status` (criminal status)
- `photo` (photo file)

All other fields are optional and can be null/empty.
