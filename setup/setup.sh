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
echo "1. Set up PostgreSQL database: criminal_database"
echo "2. Copy backend.env.example to face-similarity-app/python-backend/.env"
echo "3. Copy frontend.env.example to face-similarity-app/frontend/.env"
echo "4. Update .env files with your database credentials"
echo "5. Run: npm run dev"
echo
echo "For detailed instructions, see SETUP_GUIDE.md"
