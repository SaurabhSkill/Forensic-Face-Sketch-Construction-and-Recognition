#!/bin/bash

echo "========================================"
echo "Forensic Face Sketch Recognition Setup"
echo "========================================"
echo

echo "Step 1: Setting up Python backend..."
cd face-similarity-app/python-backend

if [ -d ".venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf .venv
fi

echo "Creating virtual environment with Python 3.11..."
python3.11 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing Python dependencies..."
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
echo "1. Copy .env.example to .env and fill in your credentials"
echo "2. Run: npm run dev"
echo "3. Access frontend at http://localhost:3000"
echo "4. Access backend API at http://localhost:5001"
echo
