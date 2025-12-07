# AddCriminalForm Component Documentation

## Overview
The `AddCriminalForm` component is a comprehensive, tabbed form interface for adding detailed criminal profiles to the forensic database. It provides an organized, user-friendly way to collect extensive forensic data.

## Component Location
```
face-similarity-app/frontend/src/components/AddCriminalForm.js
face-similarity-app/frontend/src/components/AddCriminalForm.css
```

## Features

### 1. **Tabbed Interface**
The form is organized into 4 logical tabs for better UX:
- **Tab 1: Basic Info** - Core identification data
- **Tab 2: Appearance** - Physical characteristics
- **Tab 3: Location & History** - Geographic and criminal history
- **Tab 4: Forensics & Evidence** - Forensic data and evidence

### 2. **Dynamic Array Management**
Fields that accept multiple values (aliases, marks, addresses, evidence) have:
- Input field with "+ Add" button
- Visual display of added items
- Remove button (×) for each item
- Enter key support for quick addition

### 3. **Photo Upload with Preview**
- File input for photo upload
- Real-time preview of selected image
- Required field validation

### 4. **Form Validation**
- Required fields: Criminal ID, Full Name, Photo
- Client-side validation before submission
- User-friendly error messages

## Props

### `onSubmit` (function, required)
Callback function called when form is submitted with valid data.
```javascript
onSubmit={(formData) => {
  // formData contains all form fields and photo file
  console.log(formData);
}}
```

### `onCancel` (function, required)
Callback function called when user cancels the form.
```javascript
onCancel={() => {
  // Close the form
  setShowForm(false);
}}
```

## Form Data Structure

The component manages a comprehensive state object:

```javascript
{
  // Basic Info
  criminal_id: string,        // e.g., "CR-0001-TST"
  status: string,             // "Person of Interest", "Suspect", "Wanted", etc.
  full_name: string,
  aliases: string[],          // Array of alias names
  dob: string,                // Date string
  sex: string,                // "Male", "Female", "Other"
  nationality: string,
  ethnicity: string,
  photo: File,                // File object
  
  // Appearance
  appearance: {
    height: string,           // e.g., "6'2""
    weight: string,           // e.g., "180 lbs"
    build: string,            // "Slim", "Athletic", "Average", etc.
    hair: string,             // Hair color
    eyes: string,             // Eye color
    marks: string[],          // Array of distinguishing marks
    tattoos: string,          // Description
    scars: string             // Description
  },
  
  // Locations
  locations: {
    city: string,
    state: string,
    country: string,
    lastSeen: string,         // Date string
    knownAddresses: string[]  // Array of addresses
  },
  
  // Summary
  summary: {
    charges: string,
    modus: string,            // Modus operandi
    risk: string,             // "Low", "Medium", "High", "Critical"
    priorConvictions: number
  },
  
  // Forensics
  forensics: {
    fingerprintId: string,
    dnaProfile: string,
    gait: string,             // Gait analysis
    voiceprint: string
  },
  
  // Evidence
  evidence: string[],         // Array of evidence items
  
  // Witness
  witness: {
    statements: string,
    credibility: string,      // "Low", "Medium", "High"
    contactInfo: string
  }
}
```

## Usage Example

```javascript
import React, { useState } from 'react';
import AddCriminalForm from './components/AddCriminalForm';
import axios from 'axios';

function App() {
  const [showForm, setShowForm] = useState(false);

  const handleSubmit = async (formData) => {
    try {
      // Create FormData for multipart upload
      const submitData = new FormData();
      
      // Add photo file
      submitData.append('photo', formData.photo);
      
      // Create data object (without photo)
      const profileData = {
        criminal_id: formData.criminal_id,
        status: formData.status,
        full_name: formData.full_name,
        aliases: formData.aliases,
        dob: formData.dob,
        sex: formData.sex,
        nationality: formData.nationality,
        ethnicity: formData.ethnicity,
        appearance: formData.appearance,
        locations: formData.locations,
        summary: formData.summary,
        forensics: formData.forensics,
        evidence: formData.evidence,
        witness: formData.witness
      };
      
      // Add JSON data as string
      submitData.append('data', JSON.stringify(profileData));
      
      // Submit to API
      const response = await axios.post(
        'http://localhost:5001/api/criminals',
        submitData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      
      console.log('Success:', response.data);
      alert('Criminal profile added successfully!');
      setShowForm(false);
      
    } catch (error) {
      console.error('Error:', error);
      alert('Failed to add criminal profile.');
    }
  };

  return (
    <div>
      <button onClick={() => setShowForm(true)}>
        Add New Criminal
      </button>
      
      {showForm && (
        <AddCriminalForm
          onSubmit={handleSubmit}
          onCancel={() => setShowForm(false)}
        />
      )}
    </div>
  );
}
```

## Field Descriptions

### Tab 1: Basic Info
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Criminal ID | Text | Yes | Unique identifier (e.g., CR-0001-TST) |
| Status | Select | Yes | Current status (Person of Interest, Suspect, etc.) |
| Full Name | Text | Yes | Complete legal name |
| Aliases | Array | No | Known aliases or nicknames |
| Date of Birth | Date | No | Birth date |
| Sex | Select | No | Gender |
| Nationality | Text | No | Country of citizenship |
| Ethnicity | Text | No | Ethnic background |
| Photo | File | Yes | Criminal's photograph |

### Tab 2: Appearance
| Field | Type | Description |
|-------|------|-------------|
| Height | Text | Height measurement |
| Weight | Text | Weight measurement |
| Build | Select | Body type (Slim, Athletic, etc.) |
| Hair Color | Text | Hair color description |
| Eye Color | Text | Eye color description |
| Distinguishing Marks | Array | Notable marks or features |
| Tattoos | Textarea | Tattoo descriptions |
| Scars | Textarea | Scar descriptions |

### Tab 3: Location & History
| Field | Type | Description |
|-------|------|-------------|
| City | Text | Current/last known city |
| State | Text | State/province |
| Country | Text | Country |
| Last Seen | Date | Date last observed |
| Known Addresses | Array | List of known addresses |
| Charges | Text | Criminal charges |
| Modus Operandi | Textarea | Typical criminal methods |
| Risk Level | Select | Threat assessment (Low to Critical) |
| Prior Convictions | Number | Number of previous convictions |

### Tab 4: Forensics & Evidence
| Field | Type | Description |
|-------|------|-------------|
| Fingerprint ID | Text | Fingerprint database ID |
| DNA Profile ID | Text | DNA database ID |
| Gait Analysis | Text | Walking pattern description |
| Voiceprint ID | Text | Voice database ID |
| Evidence Items | Array | List of evidence |
| Witness Statements | Textarea | Witness testimony |
| Witness Credibility | Select | Reliability rating |
| Witness Contact | Text | Contact information |

## Styling

The component uses a dark theme consistent with the forensic application:
- **Primary Color**: #00ff88 (Green accent)
- **Background**: Dark gradient (#0a1628 to #1a2a3a)
- **Text**: White (#ffffff)
- **Hover Effects**: Smooth transitions and shadows
- **Responsive**: Mobile-friendly with breakpoints

## Keyboard Shortcuts

- **Enter Key**: In array input fields, pressing Enter adds the item
- **Tab Key**: Navigate between form fields
- **Escape Key**: (Can be added) Close the form

## Accessibility Features

- Proper label associations
- Focus states on all interactive elements
- Keyboard navigation support
- Clear visual feedback
- Semantic HTML structure

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Future Enhancements

Potential improvements:
1. Auto-save draft functionality
2. Field validation with real-time feedback
3. Image cropping/editing for photos
4. Duplicate criminal ID detection
5. Import/export profile data
6. Multi-language support
7. Accessibility improvements (ARIA labels)
8. Undo/redo functionality

## Notes

- All array fields support dynamic addition/removal
- Photo preview updates in real-time
- Form state is managed internally
- Validation occurs on submit
- Clean, modern UI with smooth animations
