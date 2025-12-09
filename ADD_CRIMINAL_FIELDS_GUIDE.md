# Add New Criminal - Fields & Options Guide

## 🔴 REQUIRED FIELDS (Must Fill)

### 1. Photo Upload
- **Type:** File Upload
- **Options:** Upload JPEG or PNG image
- **Requirements:** Clear face photo, minimum 200x200 pixels, max 5MB

### 2. Criminal ID
- **Type:** Text Input
- **Format:** CR-XXXX-YYY (or your custom format)
- **Example:** CR-0001-TST, CR-2024-001
- **Note:** Must be unique

### 3. Status
- **Type:** Dropdown Menu
- **Options:**
  - Wanted
  - Convicted
  - Person of Interest
  - Suspect
  - Under Investigation

### 4. Full Name
- **Type:** Text Input
- **Example:** Brown Venddy, Anna Marie Hardy, John Michael Doe

---

## 🟢 OPTIONAL FIELDS (Can Leave Empty)

### 5. Aliases (Nicknames)
- **Type:** Text Input (can add multiple)
- **Example:** Big B, The Shadow, Mr. V, Johnny Boy
- **Note:** Separate multiple aliases with commas

### 6. Date of Birth
- **Type:** Date Picker or Text Input
- **Format:** YYYY-MM-DD or MM/DD/YYYY
- **Example:** 1985-03-15, 03/15/1985
- **Can write:** Unknown, Approximately 1980

### 7. Sex (Gender)
- **Type:** Dropdown Menu
- **Options:**
  - Male
  - Female
  - Unknown

### 8. Nationality
- **Type:** Text Input or Dropdown
- **Example:** American, British, Indian, Mexican, Unknown

### 9. Ethnicity
- **Type:** Text Input or Dropdown
- **Options:**
  - Caucasian
  - Hispanic
  - Asian
  - African American
  - Middle Eastern
  - Mixed
  - Unknown

---

## 👤 PHYSICAL APPEARANCE SECTION

### 10. Height
- **Type:** Text Input
- **Example:** 6'2", 188 cm, 5'10", 175 cm

### 11. Weight
- **Type:** Text Input
- **Example:** 185 lbs, 84 kg, 200 pounds

### 12. Build (Body Type)
- **Type:** Dropdown Menu
- **Options:**
  - Slim
  - Average
  - Athletic
  - Heavy
  - Muscular
  - Obese

### 13. Hair
- **Type:** Text Input
- **Example:** Brown Short, Black Curly, Blonde Long, Bald, Gray

### 14. Eyes (Eye Color)
- **Type:** Dropdown Menu
- **Options:**
  - Blue
  - Brown
  - Green
  - Hazel
  - Gray
  - Black

### 15. Distinguishing Marks
- **Type:** Text Area
- **Example:** Scar on left cheek, Birthmark on neck, Missing tooth

### 16. Tattoos
- **Type:** Text Area
- **Example:** Dragon on right arm, Rose on chest, Skull on back

### 17. Scars
- **Type:** Text Area
- **Example:** Surgical scar on abdomen, Knife wound on left shoulder

---

## 📍 LOCATION INFORMATION SECTION

### 18. City
- **Type:** Text Input
- **Example:** New York, Los Angeles, Mumbai, London

### 19. State/Province
- **Type:** Text Input
- **Example:** NY, California, Maharashtra, Texas

### 20. Country
- **Type:** Text Input or Dropdown
- **Example:** USA, India, UK, Mexico, Canada

### 21. Last Seen Date
- **Type:** Date Picker
- **Format:** YYYY-MM-DD
- **Example:** 2024-01-15, 2024-12-10

### 22. Known Addresses
- **Type:** Text Area (multiple lines)
- **Example:**
  ```
  123 Main Street, Apt 4B, New York, NY
  456 Oak Avenue, Los Angeles, CA
  789 Park Road, Chicago, IL
  ```

---

## 📄 CRIMINAL HISTORY SECTION

### 23. Charges (Current Charges)
- **Type:** Text Area
- **Example:** Armed Robbery, Assault with Deadly Weapon, Grand Theft Auto

### 24. Modus Operandi (Method of Operation)
- **Type:** Text Area
- **Example:** Uses stolen vehicles, Operates at night, Works with accomplices

### 25. Risk Level
- **Type:** Dropdown Menu
- **Options:**
  - Low
  - Medium
  - High
  - Extreme

### 26. Prior Convictions
- **Type:** Text Area
- **Example:** 3 felonies, 2 misdemeanors, First offense, 5 years prison (2015-2020)

---

## 🔬 FORENSIC DATA SECTION

### 27. Fingerprint ID
- **Type:** Text Input
- **Example:** FP-12345-2024, FINGERPRINT-001

### 28. DNA Profile
- **Type:** Text Input
- **Example:** DNA-67890-XYZ, DNA-PROFILE-001

### 29. Gait Analysis (Walking Pattern)
- **Type:** Text Input
- **Example:** Slight limp on right leg, Normal gait, Walks with cane

### 30. Voiceprint ID
- **Type:** Text Input
- **Example:** VP-ABCDE-001, VOICE-12345

---

## 📦 EVIDENCE SECTION (Can Add Multiple Items)

### 31. Evidence Items
For each evidence item, fill:

**Evidence Type:**
- **Type:** Dropdown Menu
- **Options:**
  - Fingerprint
  - DNA Sample
  - Surveillance Footage
  - Weapon
  - Clothing
  - Vehicle
  - Documents
  - Other

**Location Found:**
- **Type:** Text Input
- **Example:** Crime scene - 123 Main St, Stolen vehicle, Bank ATM

**Date Collected:**
- **Type:** Date Picker
- **Format:** YYYY-MM-DD
- **Example:** 2024-01-10

**Case Number:**
- **Type:** Text Input
- **Example:** CS-2024-001, CASE-001

---

## 👁️ WITNESS INFORMATION SECTION

### 32. Witness Statements
- **Type:** Text Area
- **Example:** Seen fleeing the scene in a black sedan. Witness heard gunshots at 10:30 PM.

### 33. Credibility (Witness Reliability)
- **Type:** Dropdown Menu
- **Options:**
  - Low
  - Medium
  - High

### 34. Contact Information
- **Type:** Text Input
- **Example:** Witness ID: W-001, Detective: Det. Johnson, Case Officer: Officer Smith

---

## 📋 QUICK SUMMARY

### Minimum Required (4 fields):
1. ✅ Photo Upload
2. ✅ Criminal ID
3. ✅ Status
4. ✅ Full Name

### Total Optional Fields: 30 fields
- Basic Info: 5 fields
- Physical Appearance: 8 fields
- Location: 5 fields
- Criminal History: 4 fields
- Forensic Data: 4 fields
- Evidence: 4 fields per item (can add multiple)
- Witness Info: 3 fields

---

## 💡 TIPS

1. **Start Simple:** Only fill required fields first, add details later
2. **Use "Unknown":** If you don't know something, write "Unknown" instead of leaving blank
3. **Be Specific:** More details = better matching and identification
4. **Update Later:** You can always edit and add more information later
5. **Evidence Items:** You can add multiple evidence items (click "Add Evidence" button)

---

## 📝 EXAMPLE: MINIMAL ENTRY

```
Photo: [Upload brown_venddy.jpg]
Criminal ID: CR-0001
Status: Wanted
Full Name: Brown Venddy
```

## 📝 EXAMPLE: COMPLETE ENTRY

```
Photo: [Upload brown_venddy.jpg]
Criminal ID: CR-0001-TST
Status: Wanted
Full Name: Brown Venddy

Aliases: Big B, The Shadow
Date of Birth: 1985-03-15
Sex: Male
Nationality: American
Ethnicity: Caucasian

Height: 6'2"
Weight: 185 lbs
Build: Athletic
Hair: Brown, Short
Eyes: Blue
Marks: Scar on left cheek
Tattoos: Dragon on right arm
Scars: None

City: New York
State: NY
Country: USA
Last Seen: 2024-01-15
Known Addresses: 123 Main Street, 456 Oak Avenue

Charges: Armed Robbery, Assault
Modus: Uses stolen vehicles
Risk Level: High
Prior Convictions: 3 felonies

Fingerprint ID: FP-12345
DNA Profile: DNA-67890
Gait: Normal
Voiceprint: VP-ABCDE

Evidence Item 1:
  Type: Fingerprint
  Location: Crime scene A
  Date: 2024-01-10
  Case Number: CS-001

Witness Statements: Seen fleeing the scene
Credibility: High
Contact Info: Witness ID: W-001
```

---

**Last Updated:** December 10, 2025
