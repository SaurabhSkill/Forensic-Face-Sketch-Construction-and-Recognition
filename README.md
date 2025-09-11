<<<<<<< HEAD
# Forensic-Face-Sketch-Construction-and-Recognition
=======
# Forensic Face Sketch Construction and Recognition

This repository contains a React frontend and a Python backend for forensic face similarity and recognition.

## Repository Structure

- `face-similarity-app/frontend` — React app (Create React App)
- `face-similarity-app/python-backend` — Python backend (Flask or similar)

## Prerequisites

- Node.js (LTS) and npm
- Python 3.9+ and pip

## Get the project locally

Download or copy the project files to your machine (e.g., via shared drive or archive). Then proceed with the environment setup below.

## Environment setup (no secrets included)

Secrets are not included. Copy the example files in each app, rename locally, and set your values.

### Backend (.env)

1. Copy the example inside backend folder:
   ```bash
   copy face-similarity-app\python-backend\.env.example face-similarity-app\python-backend\.env  # Windows PowerShell
   # or
   # cp face-similarity-app/python-backend/.env.example face-similarity-app/python-backend/.env   # macOS/Linux
   ```
2. Edit `face-similarity-app/python-backend/.env` and set values:
   - `SECRET_KEY`
   - `DATABASE_URL`
   - `CORS_ORIGINS`
   - Any API keys needed

### Frontend (.env)

1. Copy the example inside frontend folder:
   ```bash
   copy face-similarity-app\frontend\.env.example face-similarity-app\frontend\.env  # Windows PowerShell
   # or
   # cp face-similarity-app/frontend/.env.example face-similarity-app/frontend/.env   # macOS/Linux
   ```
2. Edit `face-similarity-app/frontend/.env` and set values:
   - `REACT_APP_API_BASE_URL`
   - `REACT_APP_API_KEY` (if required)

## Run the project locally

### Backend
```bash
cd face-similarity-app/python-backend
# (optional) create and activate virtual env
# python -m venv .venv
# .venv\Scripts\Activate.ps1  # Windows PowerShell
# source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
# Run the app (adjust if your app entry differs)
python app.py
```

### Frontend
```bash
cd face-similarity-app/frontend
npm install
npm start
```

## Security & Secrets

- Real secrets live only in local `.env` files within each app directory.
- Do not upload or share API keys, database credentials, certificates, or tokens.
- If a secret is accidentally exposed, rotate it immediately.

## Notes

- Frontend environment variables must be prefixed with `REACT_APP_` to be available in the browser.
- Ensure the backend `CORS_ORIGINS` allows the frontend origin when running locally (e.g., `http://localhost:3000`).
>>>>>>> e8cbbbb (Initial commit)
