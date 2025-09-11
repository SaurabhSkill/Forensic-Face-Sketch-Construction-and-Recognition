# PostgreSQL Database Setup Guide

## Prerequisites
- PostgreSQL installed on your system
- Python virtual environment activated

## Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 2: Create PostgreSQL Database
1. Open PostgreSQL command line or pgAdmin
2. Create a new database:
```sql
CREATE DATABASE criminal_database;
```

## Step 3: Configure Connection via .env
Create a `.env` file in `python-backend` (you can copy from the example at the repo root):
```bash
# Windows PowerShell
copy ..\..\backend.env.example .env
# macOS/Linux
# cp ../../backend.env.example .env
```
Then edit `.env` and set:
- `DATABASE_URL=postgresql://db_user:db_password@localhost:5432/criminal_database`
- `SECRET_KEY=your_secure_secret`
- Optionally adjust `CORS_ORIGINS`

Alternatively, set the environment variable directly (without `.env`):
```bash
# Windows PowerShell
$env:DATABASE_URL = "postgresql://db_user:db_password@localhost:5432/criminal_database"
# macOS/Linux
# export DATABASE_URL="postgresql://db_user:db_password@localhost:5432/criminal_database"
```

## Step 4: Run the Application
```bash
python app.py
```

The application will automatically create the required tables on first run.

## Database Schema
The `criminals` table includes:
- `id` (Primary Key)
- `name` (VARCHAR)
- `crime` (VARCHAR)
- `description` (TEXT)
- `photo_data` (BYTEA - Binary data)
- `photo_filename` (VARCHAR)
- `created_at` (TIMESTAMP)

## Troubleshooting
1. Connection Error: Check PostgreSQL is running and credentials are correct
2. Permission Error: Ensure your user has CREATE TABLE permissions
3. Port Error: Verify PostgreSQL is running on port 5432

## Testing the Setup
1. Start the backend: `python app.py`
2. Open frontend: `npm start` (in frontend directory)
3. Go to "Criminal Database" tab
4. Try adding a criminal record
5. Go to "Sketch Search" tab
6. Upload a sketch to test search functionality
