# Criminal Profile Schema - Add New Criminal

## Complete Field Reference for Adding Criminal Profiles

---

## 📋 Required Fields

### 1. **Photo** (Required)
- **Field Name:** `photo`
- **Type:** File Upload (JPEG/PNG)
- **Description:** Criminal's face photo for matching
- **Requirements:**
  - Clear frontal face photo
  - Good lighting
  - Minimum 200x200 pixels
  - Maximum 5MB file size
- **Example:** `brown_venddy.jpg`

---

### 2. **Criminal ID** (Required)
- **Field Name:** `criminal_id`
- **Type:** String (50 chars max)
- **Description:** Unique identifier for the criminal
- **Format:** `CR-XXXX-YYY` or custom format
- **Example:** `CR-0001-TST`, `CR-2024-001`
- **Validation:** Must be unique across database

---

### 3. **Status** (Required)
- **Field Name:** `status`
- **Type:** String (100 chars max)
- **Description:** Current legal status
- **Options:**
  - `Wanted`
  - `Convicted`
  - `Person of Interest`
  - `Suspect`
  - `Under Investigation`
- **Example:** `Wanted`

---

### 4. **Full Name** (Required)
- **Field Name:** `full_name`
- **Type:** String (255 chars max)
- **Description:** Criminal's complete legal name
- **Format:** First Middle Last
- **Example:** `Brown Venddy`, `Anna Marie Hardy`

---

## 📝 Optional Basic Information

### 5. **Aliases**
- **Field Name:** `aliases`
- **Type:** Array of Strings (JSON)
- **Description:** Known aliases, nicknames, or false names
- **Format:** `["Alias 1", "Alias 2", "Alias 3"]`
- **Example:** `["Big B", "The Shadow", "Mr. V"]`

---

### 6. **Date of Birth**
- **Field Name:** `dob`
- **Type:** String (50 chars max)
- **Description:** Birth date
- **Format:** `YYYY-MM-DD` or `MM/DD/YYYY`
- **Example:** `1985-03-15`, `03/15/1985`, `Unknown`

---

### 7. **Sex**
- **Field Name:** `sex`
- **Type:** String (50 chars max)
- **Description:** Gender
- **Options:** `Male`, `Female`, `Unknown`
- **Example:** `Male`

---

### 8. **Nationality**
- **Field Name:** `nationality`
- **Type:** String (100 chars max)
- **Description:** Country of citizenship
- **Example:** `American`, `British`, `Unknown`

---

### 9. **Ethnicity**
- **Field Name:** `ethnicity`
- **Type:** String (100 chars max)
- **Description:** Ethnic background
- **Example:** `Caucasian`, `Hispanic`, `Asian`, `African American`

---

## 👤 Physical Appearance (JSON Object)

### 10. **Appearance**
- **Field Name:** `appearance`
- **Type:** JSON Object
- **Description:** Detailed physical characteristics

**Structure:**
```json
{
  "height": "6'2\" (188 cm)",
  "weight": "185 lbs (84 kg)",
  "build": "Athletic",
  "hair": "Brown, Short",
  "eyes": "Blue",
  "marks": "Scar on left cheek",
  "tattoos": "Dragon tattoo on right arm",
  "scars": "Surgical scar on abdomen"
}
```

**Field Details:**
- `height`: Height in feet/inches or cm
- `weight`: Weight in lbs or kg
- `build`: Body type (Slim, Average, Athletic, Heavy, Muscular)
- `hair`: Hair color and style
- `eyes`: Eye color
- `marks`: Distinguishing marks
- `tattoos`: Tattoo descriptions and locations
- `scars`: Scar descriptions and locations

---

## 📍 Location Information (JSON Object)

### 11. **Locations**
- **Field Name:** `locations`
- **Type:** JSON Object
- **Description:** Geographic and location data

**Structure:**
```json
{
  "city": "New York",
  "state": "NY",
  "country": "USA",
  "lastSeen": "2024-01-15",
  "knownAddresses": [
    "123 Main Street, Apt 4B",
    "456 Oak Avenue"
  ]
}
```

**Field Details:**
- `city`: Current or last known city
- `state`: State/province
- `country`: Country
- `lastSeen`: Date last spotted (YYYY-MM-DD)
- `knownAddresses`: Array of known addresses

---

## 📄 Criminal Summary (JSON Object)

### 12. **Summary**
- **Field Name:** `summary`
- **Type:** JSON Object
- **Description:** Criminal history and risk assessment

**Structure:**
```json
{
  "charges": "Armed Robbery, Assault with Deadly Weapon",
  "modus": "Uses stolen vehicles, operates at night",
  "risk": "High",
  "priorConvictions": "3 felonies, 2 misdemeanors"
}
```

**Field Details:**
- `charges`: Current or pending charges
- `modus`: Modus operandi (method of operation)
- `risk`: Risk level (Low, Medium, High, Extreme)
- `priorConvictions`: Previous criminal record

---

## 🔬 Forensic Data (JSON Object)

### 13. **Forensics**
- **Field Name:** `forensics`
- **Type:** JSON Object
- **Description:** Forensic identifiers and biometric data

**Structure:**
```json
{
  "fingerprintId": "FP-12345-2024",
  "dnaProfile": "DNA-67890-XYZ",
  "gait": "Slight limp on right leg",
  "voiceprint": "VP-ABCDE-001"
}
```

**Field Details:**
- `fingerprintId`: Fingerprint database ID
- `dnaProfile`: DNA profile reference number
- `gait`: Walking pattern characteristics
- `voiceprint`: Voice analysis ID

---

## 📦 Evidence (JSON Array)

### 14. **Evidence**
- **Field Name:** `evidence`
- **Type:** JSON Array of Objects
- **Description:** Physical evidence linking to crimes

**Structure:**
```json
[
  {
    "type": "Fingerprint",
    "location": "Crime scene - 123 Main St",
    "date": "2024-01-10",
    "caseNumber": "CS-2024-001"
  },
  {
    "type": "DNA Sample",
    "location": "Stolen vehicle",
    "date": "2024-01-12",
    "caseNumber": "CS-2024-002"
  },
  {
    "type": "Surveillance Footage",
    "location": "Bank ATM",
    "date": "2024-01-15",
    "caseNumber": "CS-2024-003"
  }
]
```

**Evidence Object Fields:**
- `type`: Type of evidence (Fingerprint, DNA, Footage, Weapon, etc.)
- `location`: Where evidence was found
- `date`: Collection date (YYYY-MM-DD)
- `caseNumber`: Associated case reference

---

## 👁️ Witness Information (JSON Object)

### 15. **Witness**
- **Field Name:** `witness`
- **Type:** JSON Object
- **Description:** Witness statements and credibility

**Structure:**
```json
{
  "statements": "Seen fleeing the scene in a black sedan. Witness heard gunshots.",
  "credibility": "High",
  "contactInfo": "Witness ID: W-001, Detective: Det. Johnson"
}
```

**Field Details:**
- `statements`: Summary of witness testimony
- `credibility`: Witness reliability (Low, Medium, High)
- `contactInfo`: Reference to witness records

---

## 📊 Complete Example - Adding a Criminal

### API Request Format

**Endpoint:** `POST /api/criminals`

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
```

**Form Data:**

```javascript
{
  // File upload
  photo: <binary file data>,
  
  // JSON data field
  data: {
    // Required fields
    "criminal_id": "CR-0001-TST",
    "status": "Wanted",
    "full_name": "Brown Venddy",
    
    // Optional basic info
    "aliases": ["Big B", "The Shadow"],
    "dob": "1985-03-15",
    "sex": "Male",
    "nationality": "American",
    "ethnicity": "Caucasian",
    
    // Appearance
    "appearance": {
      "height": "6'2\" (188 cm)",
      "weight": "185 lbs (84 kg)",
      "build": "Athletic",
      "hair": "Brown, Short",
      "eyes": "Blue",
      "marks": "Scar on left cheek",
      "tattoos": "Dragon on right arm",
      "scars": "None"
    },
    
    // Locations
    "locations": {
      "city": "New York",
      "state": "NY",
      "country": "USA",
      "lastSeen": "2024-01-15",
      "knownAddresses": [
        "123 Main Street",
        "456 Oak Avenue"
      ]
    },
    
    // Summary
    "summary": {
      "charges": "Armed Robbery, Assault",
      "modus": "Uses stolen vehicles",
      "risk": "High",
      "priorConvictions": "3 felonies"
    },
    
    // Forensics
    "forensics": {
      "fingerprintId": "FP-12345",
      "dnaProfile": "DNA-67890",
      "gait": "Normal",
      "voiceprint": "VP-ABCDE"
    },
    
    // Evidence
    "evidence": [
      {
        "type": "Fingerprint",
        "location": "Crime scene A",
        "date": "2024-01-10",
        "caseNumber": "CS-001"
      }
    ],
    
    // Witness
    "witness": {
      "statements": "Seen fleeing the scene",
      "credibility": "High",
      "contactInfo": "Witness ID: W-001"
    }
  }
}
```

---

## ✅ Validation Rules

### Required Field Validation
- ✅ `photo`: Must be present, valid image file
- ✅ `criminal_id`: Must be unique, not empty
- ✅ `status`: Must be one of valid statuses
- ✅ `full_name`: Must not be empty

### Optional Field Validation
- All optional fields can be `null` or omitted
- JSON fields must be valid JSON format
- Dates should follow YYYY-MM-DD format
- Arrays must be valid JSON arrays

---

## 🎯 Minimum Required Data

**Absolute minimum to add a criminal:**

```json
{
  "photo": <file>,
  "data": {
    "criminal_id": "CR-0001",
    "status": "Wanted",
    "full_name": "John Doe"
  }
}
```

All other fields are optional and can be added/updated later.

---

## 📱 Frontend Form Fields

### Section 1: Basic Information (Required)
1. Photo Upload
2. Criminal ID
3. Status (Dropdown)
4. Full Name

### Section 2: Personal Details (Optional)
5. Aliases (Multi-input)
6. Date of Birth
7. Sex (Dropdown)
8. Nationality
9. Ethnicity

### Section 3: Physical Appearance (Optional)
10. Height
11. Weight
12. Build (Dropdown)
13. Hair Description
14. Eye Color
15. Distinguishing Marks
16. Tattoos
17. Scars

### Section 4: Location (Optional)
18. City
19. State
20. Country
21. Last Seen Date
22. Known Addresses (Multi-input)

### Section 5: Criminal History (Optional)
23. Charges
24. Modus Operandi
25. Risk Level (Dropdown)
26. Prior Convictions

### Section 6: Forensic Data (Optional)
27. Fingerprint ID
28. DNA Profile
29. Gait Analysis
30. Voiceprint ID

### Section 7: Evidence (Optional)
31. Evidence Items (Dynamic list)
    - Type
    - Location
    - Date
    - Case Number

### Section 8: Witness Info (Optional)
32. Witness Statements
33. Credibility (Dropdown)
34. Contact Information

---

## 🔄 Update Criminal Profile

**Endpoint:** `PUT /api/criminals/{id}`

Same structure as adding, but all fields are optional. Only provided fields will be updated.

---

**Last Updated**: December 9, 2025  
**Version**: 2.0
