# Forensic Face Sketch Construction and Recognition - Project Analysis

## 📋 Project Overview

This is a **full-stack AI-powered forensic face recognition application** that allows law enforcement to:
- Compare facial sketches with photographs
- Manage a criminal database with detailed forensic profiles
- Search for criminals using sketch-based queries
- Get AI-powered similarity scores and verification results

---

## 🏗️ Architecture

### **Frontend** (React 18)
- **Location**: `face-similarity-app/frontend/`
- **Framework**: Create React App (CRA)
- **Port**: http://localhost:3000

### **Backend** (Python Flask)
- **Location**: `face-similarity-app/python-backend/`
- **Framework**: Flask with Flask-CORS
- **Port**: http://localhost:5001
- **AI Engine**: DeepFace with Facenet512 model

### **Database**
- **Type**: SQLite (no setup required)
- **File**: `criminal_database.db` (auto-created on first run)
- **ORM**: SQLAlchemy

---

## 🔧 Technology Stack

### Frontend Dependencies
```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^6.30.1",
  "axios": "^1.11.0",
  "react-draggable": "^4.5.0",
  "html2canvas": "^1.4.1",
  "react-scripts": "5.0.1"
}
```

### Backend Dependencies
```
flask==3.0.3
flask-cors==4.0.1
deepface==0.0.93
opencv-python-headless==4.10.0.84
numpy>=1.24,<2.0
onnxruntime==1.18.0
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
```

### Workspace Dependencies
```json
{
  "concurrently": "^8.2.2",
  "dotenv": "^16.4.5"
}
```

---

## 📦 Prerequisites

Before running this project, ensure you have:

1. **Node.js** (LTS version 18.x or 20.x)
   - Check: `node --version`
   - Download: https://nodejs.org/

2. **Python 3.9+**
   - Check: `python --version` or `python3 --version`
   - Download: https://www.python.org/downloads/

3. **Git**
   - Check: `git --version`
   - Download: https://git-scm.com/

4. **pip** (Python package manager)
   - Usually comes with Python
   - Check: `pip --version`

---

## 🚀 Setup Instructions

### Option 1: Automated Setup (Recommended)

**For Windows:**
```cmd
cd setup
setup.bat
```

**For macOS/Linux:**
```bash
cd setup
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

#### Step 1: Backend Setup
```cmd
cd face-similarity-app\python-backend
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 2: Frontend Setup
```cmd
cd ..\frontend
npm install
```

#### Step 3: Workspace Setup
```cmd
cd ..\..
npm install
```

---

## ⚙️ Configuration

### Backend Configuration (.env)
**File**: `face-similarity-app/python-backend/.env`

```env
# Database (SQLite - auto-created)
DATABASE_URL=sqlite:///criminal_database.db

# Flask Configuration
SECRET_KEY=your_very_long_and_secure_secret_key_here
CORS_ORIGINS=http://localhost:3000
PORT=5001
```

### Frontend Configuration (.env)
**File**: `face-similarity-app/frontend/.env`

```env
# API Configuration
REACT_APP_API_BASE_URL=http://localhost:5001
```

**Note**: Environment files are optional. The app uses sensible defaults if not configured.

---

## 🎯 Running the Application

### Start Both Frontend & Backend Together
```cmd
npm run dev
```

This command uses `concurrently` to run both servers simultaneously.

### Start Individually

**Backend Only:**
```cmd
cd face-similarity-app\python-backend
.venv\Scripts\activate
python app.py
```

**Frontend Only:**
```cmd
cd face-similarity-app\frontend
npm start
```

---

## 🌐 Access Points

- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:5001
- **API Health Check**: http://localhost:5001/api/criminals

---

## 📡 API Endpoints

### Face Comparison
- `POST /api/compare` - Compare sketch with photo
- `POST /api/cache/clear` - Clear AI model caches
- `GET /api/cache/stats` - Get cache statistics

### Criminal Database
- `GET /api/criminals` - Get all criminals
- `POST /api/criminals` - Add new criminal
- `GET /api/criminals/<id>` - Get criminal by ID
- `PUT /api/criminals/<id>` - Update criminal
- `DELETE /api/criminals/<id>` - Delete criminal
- `GET /api/criminals/<id>/photo` - Get criminal photo
- `POST /api/criminals/search` - Search using sketch

---

## 🗄️ Database Schema

### Criminal Table
```python
{
  "id": Integer (Primary Key),
  "criminal_id": String (Unique, e.g., "CR-0001-TST"),
  "status": String (e.g., "Suspect", "Convicted"),
  "full_name": String,
  "aliases": JSON Array,
  "dob": String,
  "sex": String,
  "nationality": String,
  "ethnicity": String,
  "photo_data": Binary,
  "photo_filename": String,
  "appearance": JSON {height, weight, build, hair, eyes, marks},
  "locations": JSON {city, state, country, lastSeen},
  "summary": JSON {charges, modus, risk, priorConvictions},
  "forensics": JSON {fingerprintId, dnaProfile, gait},
  "evidence": JSON Array,
  "witness": JSON {statements, credibility},
  "created_at": DateTime,
  "updated_at": DateTime
}
```

---

## 🤖 AI/ML Features

### Face Recognition Model
- **Model**: Facenet512 (DeepFace)
- **Metric**: Cosine similarity
- **Optimizations**:
  - Model pre-initialization
  - Image normalization (CLAHE)
  - Embedding caching
  - Result caching
  - Consistent similarity calculation

### Image Processing
- Automatic face detection
- Image normalization for consistent results
- CLAHE (Contrast Limited Adaptive Histogram Equalization)
- Brightness and contrast enhancement
- Sharpening filters

---

## 📁 Project Structure

```
Forensic Face Sketch Construction and Recognition/
├── face-similarity-app/
│   ├── frontend/                    # React application
│   │   ├── public/                  # Static assets
│   │   ├── src/
│   │   │   ├── assets/              # Images and sketch elements
│   │   │   ├── components/          # React components
│   │   │   │   ├── AddCriminalForm.js
│   │   │   │   ├── Canvas.js
│   │   │   │   ├── ComponentLibrary.js
│   │   │   │   ├── ControlsPanel.js
│   │   │   │   ├── CriminalDetailModal.js
│   │   │   │   ├── CriminalList.js
│   │   │   │   ├── LayersPanel.js
│   │   │   │   ├── ScanningAnimation.js
│   │   │   │   └── SketchCanvas.js
│   │   │   ├── pages/
│   │   │   │   └── SketchPage.js
│   │   │   ├── App.js
│   │   │   ├── config.js
│   │   │   └── index.js
│   │   ├── .env.example
│   │   └── package.json
│   │
│   └── python-backend/              # Flask API
│       ├── .venv/                   # Python virtual environment
│       ├── app.py                   # Main Flask application
│       ├── database.py              # SQLAlchemy models
│       ├── criminal_database.db     # SQLite database (auto-created)
│       ├── .env.example
│       └── requirements.txt
│
├── setup/                           # Setup scripts
│   ├── setup.bat                    # Windows setup
│   └── setup.sh                     # macOS/Linux setup
│
├── .gitignore
├── package.json                     # Workspace configuration
└── README.md
```

---

## 🔐 Security Considerations

1. **Environment Variables**: Never commit `.env` files to Git
2. **Secret Keys**: Generate strong random keys for production
3. **Database**: SQLite is for development; use PostgreSQL for production
4. **CORS**: Configure proper origins in production
5. **File Uploads**: Validate and sanitize all uploaded images
6. **API Authentication**: Add authentication for production use

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Python Virtual Environment Not Activating
**Windows:**
```cmd
cd face-similarity-app\python-backend
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
cd face-similarity-app/python-backend
source .venv/bin/activate
```

#### 2. Port Already in Use
- Frontend (3000): Change in `package.json` or set `PORT=3001`
- Backend (5001): Change in `.env` file or `app.py`

#### 3. DeepFace Model Download Issues
- First run downloads AI models (~100MB)
- Ensure stable internet connection
- Models are cached in `~/.deepface/weights/`

#### 4. SQLite Database Locked
- Close all database connections
- Delete `criminal_database.db` and restart (data will be lost)

#### 5. npm/pip Installation Failures
- Clear caches: `npm cache clean --force` or `pip cache purge`
- Update package managers: `npm install -g npm@latest` or `pip install --upgrade pip`

---

## 🧪 Testing the Application

### 1. Test Backend API
```cmd
cd face-similarity-app\python-backend
.venv\Scripts\activate
python app.py
```
Visit: http://localhost:5001/api/criminals

### 2. Test Frontend
```cmd
cd face-similarity-app\frontend
npm start
```
Visit: http://localhost:3000

### 3. Test Face Comparison
1. Upload a sketch image
2. Upload a photo image
3. Click "Compare"
4. View similarity score and verification result

---

## 👥 Collaboration Setup

### For Your Friend to Set Up:

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "Forensic Face Sketch Construction and Recognition"
   ```

2. **Run setup script**
   ```cmd
   # Windows
   setup\setup.bat
   
   # macOS/Linux
   ./setup/setup.sh
   ```

3. **Start the application**
   ```cmd
   npm run dev
   ```

4. **Access the app**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:5001

### Sharing Database Data

The SQLite database (`criminal_database.db`) can be:
- Committed to Git (if data is not sensitive)
- Shared via cloud storage
- Exported/imported using SQLite tools

**Note**: For production collaboration, consider using PostgreSQL with a shared server.

---

## 📚 Additional Resources

- **DeepFace Documentation**: https://github.com/serengil/deepface
- **React Documentation**: https://react.dev/
- **Flask Documentation**: https://flask.palletsprojects.com/
- **SQLAlchemy Documentation**: https://www.sqlalchemy.org/

---

## 🎓 Learning Points

This project demonstrates:
- Full-stack development (React + Flask)
- AI/ML integration (DeepFace, OpenCV)
- RESTful API design
- Database modeling with SQLAlchemy
- Image processing and computer vision
- Caching strategies for performance
- File upload handling
- CORS configuration
- Environment-based configuration

---

## ✅ Quick Checklist

Before starting development, ensure:
- [ ] Node.js 18+ installed
- [ ] Python 3.9+ installed
- [ ] Git installed
- [ ] Setup script executed successfully
- [ ] Both frontend and backend running
- [ ] Can access http://localhost:3000
- [ ] Can access http://localhost:5001/api/criminals
- [ ] Database file created (`criminal_database.db`)

---

**Ready to collaborate!** 🚀
