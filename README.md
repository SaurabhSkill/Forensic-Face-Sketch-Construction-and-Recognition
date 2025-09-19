# Forensic Face Sketch Construction and Recognition

This repository contains a React frontend and a Python backend for forensic face similarity and recognition using AI-powered facial recognition technology.

## 🚀 Quick Start

**For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

### Prerequisites
- Node.js (LTS 18.x or 20.x)
- Python 3.9+
- PostgreSQL
- Git

### Quick Setup
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd "Forensic Face Sketch Construction and Recognition"
   ```

2. **Run setup script:**
   ```bash
   # Windows
   setup.bat
   
   # macOS/Linux
   ./setup.sh
   ```

3. **Set up environment files:**
   ```bash
   # Copy example files
   copy backend.env.example face-similarity-app\python-backend\.env
   copy frontend.env.example face-similarity-app\frontend\.env
   
   # Edit .env files with your database credentials
   ```

4. **Start the application:**
   ```bash
   npm run dev
   ```

## 📁 Repository Structure

- `face-similarity-app/frontend` — React app (Create React App)
- `face-similarity-app/python-backend` — Python backend (Flask API)
- `SETUP_GUIDE.md` — Comprehensive setup instructions
- `setup.bat` / `setup.sh` — Automated setup scripts
- `backend.env.example` / `frontend.env.example` — Environment file templates

## 🔧 Features

- **Face Comparison:** Compare sketches with photos using AI
- **Criminal Database:** Manage criminal records with photos
- **Sketch Search:** Search criminals using sketch-based queries
- **Similarity Scoring:** Get accurate similarity scores and verification results

## 🌐 Access

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:5001

## 📚 Documentation

- [Complete Setup Guide](SETUP_GUIDE.md) - Detailed installation and configuration instructions
- [Troubleshooting](SETUP_GUIDE.md#-troubleshooting) - Common issues and solutions

## 🔐 Security

- Environment variables are stored in local `.env` files
- Database credentials should be kept secure
- No sensitive data is committed to the repository

## 🛠️ Technology Stack

- **Frontend:** React 19, Axios
- **Backend:** Flask, DeepFace, OpenCV, ONNX Runtime
- **Database:** PostgreSQL with SQLAlchemy
- **AI/ML:** DeepFace with Facenet512 model
