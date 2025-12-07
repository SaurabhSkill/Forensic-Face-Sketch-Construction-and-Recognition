#!/bin/bash

echo "========================================"
echo "Forensic Face Sketch Recognition Setup"
echo "========================================"
echo

echo "Step 1: Setting up Python backend..."
cd face-similarity-app/python-backend

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Step 2: Setting up React frontend..."
cd ../frontend

echo "Installing Node.js dependencies..."
npm install

echo
echo "Step 3: Setting up workspace..."
cd ../..

echo "Installing workspace dependencies..."
npm install

echo
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo
echo "Next steps:"
echo "1. (Optional) Copy .env.example files to .env if you need custom configuration"
echo "2. Run: npm run dev"
echo "3. Access frontend at http://localhost:3000"
echo "4. Access backend API at http://localhost:5001"
echo
echo "Note: Database (SQLite) will be created automatically on first run"
