# 🎨 FaceFind Forensics - Frontend

Modern React-based UI with glassmorphism design for forensic face matching system.

---

## 🎯 Features

- **Premium Glassmorphism UI**: Modern glass-effect design with dark theme
- **Role-Based Dashboards**: Separate interfaces for Admin and Officer
- **Face Sketch Builder**: Interactive drag-and-drop sketch creation
- **Real-Time Face Comparison**: Live matching with confidence scores
- **Criminal Database Management**: Complete CRUD operations
- **Responsive Design**: Optimized for desktop, tablet, and mobile
- **Data Visualization**: Charts and graphs for match results
- **Smooth Animations**: Professional transitions and micro-interactions

---

## 📋 Prerequisites

- Node.js 16+
- npm or yarn

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env  # Mac/Linux
copy .env.example .env  # Windows
```

Edit `.env`:

```env
REACT_APP_API_URL=http://localhost:5001
```

For production:
```env
REACT_APP_API_URL=https://your-api-domain.com
```

### 3. Start Development Server

```bash
npm start
```

Opens: **http://localhost:3000**

---

## 📁 Project Structure

```
frontend/
├── public/
│   ├── assets/
│   │   └── Face Sketch Elements/    # Sketch builder assets
│   │       ├── eyebrows/
│   │       ├── eyes/
│   │       ├── hair/
│   │       ├── nose/
│   │       └── mouth/
│   └── index.html
│
├── src/
│   ├── components/                  # Reusable components
│   │   ├── AdminLogin.js
│   │   ├── OfficerLogin.js
│   │   ├── Navbar.js
│   │   ├── CriminalCard.js
│   │   └── MatchResultCard.js
│   │
│   ├── pages/                       # Page components
│   │   ├── AdminDashboard.js        # Admin dashboard
│   │   ├── OfficerDashboard.js      # Officer dashboard
│   │   ├── CriminalDatabase.js      # Criminal CRUD
│   │   ├── FaceComparison.js        # Face matching
│   │   ├── SketchBuilder.js         # Sketch creation
│   │   └── ManageOfficers.js        # Officer management
│   │
│   ├── services/                    # API services
│   │   ├── api.js                   # Axios instance
│   │   ├── authService.js           # Authentication
│   │   ├── criminalService.js       # Criminal operations
│   │   └── faceComparisonService.js # Face matching
│   │
│   ├── hooks/                       # Custom React hooks
│   │   ├── useAuth.js               # Authentication hook
│   │   └── useLocalStorage.js       # Local storage hook
│   │
│   ├── layout/                      # Layout components
│   │   ├── MainLayout.js
│   │   └── DashboardLayout.js
│   │
│   ├── theme/                       # Theme configuration
│   │   └── colors.js
│   │
│   ├── styles/                      # Global styles
│   │   └── glassmorphism.css
│   │
│   ├── App.js                       # Main app component
│   ├── index.js                     # Entry point
│   └── config.js                    # Configuration
│
├── package.json
├── .env
└── README.md
```

---

## 🎨 Design System

### Color Palette

```css
/* Primary Colors */
--primary-cyan: #00f0ff
--primary-purple: #b000ff
--primary-pink: #ff00ff

/* Background */
--bg-dark: #0a0a0f
--bg-card: rgba(20, 20, 30, 0.7)

/* Glass Effect */
--glass-bg: rgba(255, 255, 255, 0.05)
--glass-border: rgba(255, 255, 255, 0.1)
--glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3)
```

### Typography

```css
/* Font Family */
font-family: 'Inter', 'Segoe UI', sans-serif

/* Font Sizes */
--text-xs: 0.75rem
--text-sm: 0.875rem
--text-base: 1rem
--text-lg: 1.125rem
--text-xl: 1.25rem
--text-2xl: 1.5rem
--text-3xl: 1.875rem
```

### Glassmorphism Effect

```css
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
```

---

## 🔧 Available Scripts

### `npm start`

Runs the app in development mode.
- Opens: http://localhost:3000
- Hot reload enabled
- Shows lint errors in console

### `npm test`

Launches test runner in interactive watch mode.

### `npm run build`

Builds the app for production to the `build` folder.
- Optimized bundle
- Minified code
- Hashed filenames
- Ready for deployment

### `npm run eject`

**Warning**: This is a one-way operation!

Ejects from Create React App, giving full control over configuration.

---

## 📱 Pages & Features

### Admin Dashboard

**Features:**
- System statistics overview
- Recent activity feed
- Quick actions panel
- Officer management
- Database statistics

**Route:** `/admin/dashboard`

### Officer Dashboard

**Features:**
- Personal statistics
- Recent searches
- Quick access to tools
- Case history

**Route:** `/officer/dashboard`

### Criminal Database

**Features:**
- View all criminals
- Add new criminal
- Edit criminal details
- Delete criminal
- Upload photos
- Search and filter

**Route:** `/criminals`

### Face Comparison

**Features:**
- Upload sketch image
- Upload photo image
- Real-time comparison
- Confidence scoring
- Multi-region analysis
- Match visualization

**Route:** `/compare`

### Sketch Builder

**Features:**
- Drag-and-drop interface
- Face element library:
  - Hair styles (12 options)
  - Eyebrows (24 options)
  - Eyes (24 options)
  - Nose (12 options)
  - Mouth (12 options)
- Canvas manipulation
- Export sketch
- Search with sketch

**Route:** `/sketch-builder`

### Manage Officers

**Features:**
- View all officers
- Add new officer
- Reset officer password
- Delete officer
- View officer activity

**Route:** `/admin/officers`

---

## 🔌 API Integration

### Authentication

```javascript
import { authService } from './services/authService';

// Admin login
const { user, token } = await authService.adminLogin(email, password, otp);

// Officer login
const { user, token } = await authService.officerLogin(email, password);

// Verify token
const user = await authService.verifyToken();

// Logout
authService.logout();
```

### Criminal Operations

```javascript
import { criminalService } from './services/criminalService';

// Get all criminals
const criminals = await criminalService.getAllCriminals();

// Add criminal
const criminal = await criminalService.addCriminal(formData);

// Update criminal
await criminalService.updateCriminal(id, formData);

// Delete criminal
await criminalService.deleteCriminal(id);

// Get criminal photo
const photoUrl = criminalService.getCriminalPhotoUrl(id);
```

### Face Comparison

```javascript
import { faceComparisonService } from './services/faceComparisonService';

// Compare two faces
const result = await faceComparisonService.compareFaces(sketch, photo);

// Search database
const matches = await faceComparisonService.searchDatabase(sketchFile);
```

---

## 🎭 Custom Hooks

### useAuth

```javascript
import { useAuth } from './hooks/useAuth';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();
  
  if (!isAuthenticated) {
    return <LoginPage />;
  }
  
  return <Dashboard user={user} />;
}
```

### useLocalStorage

```javascript
import { useLocalStorage } from './hooks/useLocalStorage';

function MyComponent() {
  const [value, setValue] = useLocalStorage('key', defaultValue);
  
  return (
    <input 
      value={value} 
      onChange={(e) => setValue(e.target.value)} 
    />
  );
}
```

---

## 🛠️ Configuration

### Environment Variables

All environment variables must be prefixed with `REACT_APP_`:

```env
REACT_APP_API_URL=http://localhost:5001
REACT_APP_VERSION=1.0.0
REACT_APP_ENV=development
```

Access in code:

```javascript
const apiUrl = process.env.REACT_APP_API_URL;
```

### API Configuration

Edit `src/config.js`:

```javascript
export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';
export const API_TIMEOUT = 30000;
export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
```

---

## 🎨 Styling

### Global Styles

Located in `src/index.css`:
- CSS reset
- Global variables
- Base typography
- Utility classes

### Component Styles

Each component has inline styles or CSS modules:

```javascript
// Inline styles
const styles = {
  container: {
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(10px)',
    borderRadius: '16px'
  }
};

// CSS modules
import styles from './Component.module.css';
```

---

## 📦 Dependencies

### Core
- **react**: ^18.3.1 - UI framework
- **react-dom**: ^18.3.1 - React DOM renderer
- **react-router-dom**: ^6.30.1 - Routing

### HTTP & Data
- **axios**: ^1.11.0 - HTTP client

### UI Components
- **react-draggable**: ^4.5.0 - Drag-and-drop
- **recharts**: ^3.7.0 - Charts and graphs
- **three**: ^0.160.0 - 3D graphics

### Utilities
- **html2canvas**: ^1.4.1 - Screenshot capture

### Development
- **react-scripts**: 5.0.1 - Build tools
- **fast-check**: ^4.5.3 - Property-based testing

---

## 🧪 Testing

### Run Tests

```bash
npm test
```

### Test Coverage

```bash
npm test -- --coverage
```

### Test Structure

```
src/
├── __tests__/
│   ├── components/
│   ├── pages/
│   └── services/
└── setupTests.js
```

---

## 🚀 Production Build

### Build

```bash
npm run build
```

Output: `build/` folder

### Serve Locally

```bash
npm install -g serve
serve -s build -p 3000
```

### Deploy

**Netlify:**
```bash
npm run build
netlify deploy --prod --dir=build
```

**Vercel:**
```bash
npm run build
vercel --prod
```

**AWS S3:**
```bash
npm run build
aws s3 sync build/ s3://your-bucket-name
```

---

## 🔧 Troubleshooting

### Build Fails

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install
npm run build
```

### API Connection Issues

- Check `REACT_APP_API_URL` in `.env`
- Verify backend is running
- Check browser console for CORS errors

### Styling Issues

- Clear browser cache
- Check CSS specificity
- Verify glassmorphism browser support

---

## 🌐 Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Note:** Glassmorphism requires `backdrop-filter` support.

---

## 📞 Support

For issues:
1. Check browser console for errors
2. Verify API connectivity
3. Review environment configuration
4. Check network tab for failed requests

---

**Designed for Forensic Excellence** 🎨
