# 🚀 Forensic Face Sketch Construction and Recognition - Complete Setup Guide

## 📋 Project Overview

This is a **Forensic Face Sketch Construction and Recognition** system that allows users to:
- Compare face sketches with photos using AI-powered facial recognition
- Maintain a criminal database with photos and information
- Search for criminals using sketch-based queries
- Get similarity scores and verification results

## 🛠️ Required Software & Tools

### **Essential Software (Must Install)**

1. **Node.js** (LTS version 18.x or 20.x)
   - Download from: https://nodejs.org/
   - Includes npm package manager
   - **Verify installation:** `node --version` and `npm --version`

2. **Python** (3.9 or higher)
   - Download from: https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation
   - **Verify installation:** `python --version`

3. **PostgreSQL Database**
   - Download from: https://www.postgresql.org/download/
   - Or use PostgreSQL installer for Windows: https://www.postgresql.org/download/windows/
   - **Verify installation:** `psql --version`

4. **Git** (for cloning the repository)
   - Download from: https://git-scm.com/downloads
   - **Verify installation:** `git --version`

### **Optional but Recommended**
- **Visual Studio Code** (for code editing)
- **pgAdmin** (PostgreSQL GUI tool)

## 📦 Project Dependencies

### **Frontend Dependencies (React App)**
```json
{
  "react": "^19.1.1",
  "react-dom": "^19.1.1", 
  "react-scripts": "5.0.1",
  "axios": "^1.11.0",
  "@testing-library/react": "^16.3.0",
  "@testing-library/jest-dom": "^6.8.0",
  "@testing-library/user-event": "^13.5.0",
  "web-vitals": "^2.1.4"
}
```

### **Backend Dependencies (Python)**
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

## 🚀 Step-by-Step Installation Guide

### **Step 1: Clone the Repository**
```bash
git clone <your-repository-url>
cd "Forensic Face Sketch Construction and Recognition"
```

### **Step 2: Set Up PostgreSQL Database**

1. **Install PostgreSQL** (if not already installed)
2. **Start PostgreSQL service**
3. **Create a new database:**
   ```sql
   -- Connect to PostgreSQL (using psql or pgAdmin)
   CREATE DATABASE criminal_database;
   ```
4. **Note your PostgreSQL credentials** (username, password, port - usually 5432)

### **Step 3: Set Up Python Backend**

1. **Navigate to backend directory:**
   ```bash
   cd face-similarity-app/python-backend
   ```

2. **Create virtual environment:**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Create environment file:**
   Create a `.env` file in `face-similarity-app/python-backend/` with:
   ```env
   DATABASE_URL=postgresql://your_username:your_password@localhost:5432/criminal_database
   SECRET_KEY=your_secure_secret_key_here_make_it_long_and_random
   CORS_ORIGINS=http://localhost:3000
   PORT=5001
   ```

### **Step 4: Set Up React Frontend**

1. **Navigate to frontend directory:**
   ```bash
   cd face-similarity-app/frontend
   ```

2. **Install Node.js dependencies:**
   ```bash
   npm install
   ```

3. **Create environment file (optional):**
   Create a `.env` file in `face-similarity-app/frontend/` with:
   ```env
   REACT_APP_API_BASE_URL=http://localhost:5001
   ```

### **Step 5: Set Up Root Workspace**

1. **Navigate to project root:**
   ```bash
   cd ../../
   ```

2. **Install workspace dependencies:**
   ```bash
   npm install
   ```

## ▶️ Running the Project

### **Option 1: Run Everything Together (Recommended)**
From the project root directory:
```bash
npm run dev
```
This will start both backend (port 5001) and frontend (port 3000) simultaneously.

### **Option 2: Run Separately**

**Backend only:**
```bash
cd face-similarity-app/python-backend
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
python app.py
```

**Frontend only:**
```bash
cd face-similarity-app/frontend
npm start
```

## 🌐 Access the Application

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:5001

## 🔧 Project Features

### **1. Face Comparison**
- Upload a sketch and a photo
- Get similarity score and verification result
- Uses DeepFace with Facenet512 model
- Supports various image formats (JPG, PNG, etc.)

### **2. Criminal Database Management**
- Add criminals with photos and details (name, crime, description)
- View all criminals in the database
- Delete criminal records
- Store photos as binary data in PostgreSQL

### **3. Sketch Search**
- Upload a sketch to search against criminal database
- Get ranked results by similarity score
- Configurable similarity threshold
- Real-time face matching using AI

## ⚠️ Important Notes

1. **Database Connection:** Make sure PostgreSQL is running and the connection string in `.env` is correct
2. **File Uploads:** The app handles image files (JPG, PNG, etc.)
3. **AI Models:** DeepFace will download required models on first run (may take time and internet)
4. **Memory Usage:** The app uses computer vision libraries that may require significant RAM (4GB+ recommended)
5. **No C++ Build Tools Required:** All dependencies use pre-compiled binaries
6. **First Run:** Initial model downloads may take 5-10 minutes

## 🐛 Troubleshooting

### **Common Issues:**

1. **PostgreSQL Connection Error:**
   ```
   Error: connection to server at "localhost" (127.0.0.1), port 5432 failed
   ```
   **Solutions:**
   - Check if PostgreSQL service is running
   - Verify database credentials in `.env`
   - Ensure database `criminal_database` exists
   - Check if port 5432 is available

2. **Python Dependencies Error:**
   ```
   ERROR: Could not find a version that satisfies the requirement
   ```
   **Solutions:**
   - Make sure virtual environment is activated
   - Try: `pip install --upgrade pip`
   - Then: `pip install -r requirements.txt`
   - For Windows: `pip install --upgrade setuptools wheel`

3. **Node.js Dependencies Error:**
   ```
   npm ERR! peer dep missing
   ```
   **Solutions:**
   - Delete `node_modules` and `package-lock.json`
   - Run `npm install` again
   - Try: `npm install --legacy-peer-deps`

4. **Port Already in Use:**
   ```
   Error: listen EADDRINUSE: address already in use :::3000
   ```
   **Solutions:**
   - Kill processes using ports 3000 or 5001
   - Change ports in `.env` files if needed
   - Windows: `netstat -ano | findstr :3000` then `taskkill /PID <PID> /F`

5. **DeepFace Model Download Issues:**
   ```
   ModuleNotFoundError: No module named 'tensorflow'
   ```
   **Solutions:**
   - Ensure all requirements are installed
   - Check internet connection for model downloads
   - Try: `pip install tensorflow` separately

## 📁 Project Structure
```
Forensic Face Sketch Construction and Recognition/
├── face-similarity-app/
│   ├── frontend/                    # React application
│   │   ├── src/                    # Source code
│   │   ├── public/                 # Static files
│   │   ├── package.json           # Frontend dependencies
│   │   └── .env                   # Frontend environment (create this)
│   └── python-backend/            # Flask API server
│       ├── app.py                 # Main Flask application
│       ├── database.py            # Database models and connection
│       ├── requirements.txt       # Python dependencies
│       └── .env                   # Backend environment (create this)
├── package.json                   # Workspace configuration
├── package-lock.json             # Dependency lock file
├── README.md                     # Project documentation
├── SETUP_GUIDE.md               # This setup guide
└── .gitignore                   # Git ignore rules
```

## 🔐 Environment Variables Reference

### **Backend (.env)**
```env
# Database connection
DATABASE_URL=postgresql://username:password@localhost:5432/criminal_database

# Flask configuration
SECRET_KEY=your_very_long_and_secure_secret_key_here
CORS_ORIGINS=http://localhost:3000
PORT=5001
```

### **Frontend (.env)**
```env
# API configuration
REACT_APP_API_BASE_URL=http://localhost:5001
```

## 🎯 Quick Start Commands

```bash
# 1. Clone and navigate
git clone <repository-url>
cd "Forensic Face Sketch Construction and Recognition"

# 2. Set up database (PostgreSQL)
# Create database: criminal_database

# 3. Set up backend
cd face-similarity-app/python-backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
# Create .env file with database credentials

# 4. Set up frontend
cd ../frontend
npm install
# Create .env file (optional)

# 5. Run everything
cd ../../
npm run dev
```

## 🎉 Success!

Once everything is set up, you should be able to:
1. Access the web interface at http://localhost:3000
2. Upload images for face comparison
3. Manage the criminal database
4. Search for criminals using sketches

The application uses AI-powered facial recognition to provide accurate similarity scores between sketches and photos, making it perfect for forensic applications!

## 📞 Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Verify all software requirements are installed
3. Ensure PostgreSQL is running
4. Check that all environment variables are set correctly
5. Make sure ports 3000 and 5001 are available

---

**Happy coding! 🚀**
