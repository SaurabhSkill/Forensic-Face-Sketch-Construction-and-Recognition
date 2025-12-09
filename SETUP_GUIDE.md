# 🚀 Complete Setup Guide for FaceFind Forensics

This guide will walk you through setting up the project from scratch on a new computer.

---

## ✅ Step-by-Step Setup

### Step 1: Install Required Software

#### 1.1 Install Python 3.10+

**Windows:**
1. Download from https://www.python.org/downloads/
2. Run installer
3. ✅ **IMPORTANT**: Check "Add Python to PATH"
4. Click "Install Now"
5. Verify: Open CMD and type `python --version`

**Mac:**
```bash
brew install python@3.10
```

**Linux:**
```bash
sudo apt update
sudo apt install python3.10 python3-pip
```

#### 1.2 Install Node.js 16+

**Windows/Mac:**
1. Download from https://nodejs.org/
2. Run installer
3. Verify: Open terminal and type `node --version`

**Linux:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### 1.3 Install Git

**Windows:**
- Download from https://git-scm.com/

**Mac:**
```bash
brew install git
```

**Linux:**
```bash
sudo apt install git
```

---

### Step 2: Clone the Repository

```bash
# Clone the project
git clone <repository-url>

# Navigate to project directory
cd forensic-face-sketch-avishkar
```

---

### Step 3: Install Node Dependencies

```bash
# Install root dependencies
npm install

# Install frontend dependencies
cd face-similarity-app/frontend
npm install

# Go back to root
cd ../..
```

---

### Step 4: Install Python Dependencies

```bash
# Navigate to backend
cd face-similarity-app/python-backend

# Install all Python packages
pip install -r requirements.txt
```

**If you get errors, try:**
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Common packages that might need manual installation:**
```bash
pip install opencv-python-headless
pip install deepface
pip install tf-keras
pip install bcrypt
pip install pyjwt
```

---

### Step 5: Configure Environment Variables

#### 5.1 Backend Configuration

```bash
# Navigate to backend folder
cd face-similarity-app/python-backend

# Copy example env file
# Windows:
copy .env.example .env

# Mac/Linux:
cp .env.example .env
```

#### 5.2 Edit Backend .env File

Open `face-similarity-app/python-backend/.env` and configure:

```env
# SMTP Configuration (for OTP emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=FaceFind Forensics

# JWT Secret (change to random string)
JWT_SECRET=change-this-to-random-secret-key-12345

# Database
DATABASE_URL=sqlite:///criminal_database.db
```

#### 5.3 Get Gmail App Password

1. Go to https://myaccount.google.com/
2. Click "Security"
3. Enable "2-Step Verification" (if not already enabled)
4. Search for "App Passwords"
5. Select "Mail" and "Windows Computer" (or your device)
6. Click "Generate"
7. Copy the 16-character password (format: xxxx xxxx xxxx xxxx)
8. Paste it in `.env` as `SMTP_PASSWORD` (remove spaces)

#### 5.4 Frontend Configuration

```bash
# Navigate to frontend folder
cd face-similarity-app/frontend

# Copy example env file
# Windows:
copy .env.example .env

# Mac/Linux:
cp .env.example .env
```

The default should work:
```env
REACT_APP_API_BASE_URL=http://localhost:5001
```

---

### Step 6: Initialize Database

```bash
# Navigate to backend
cd face-similarity-app/python-backend

# Create admin user
python create_admin_auto.py
```

You should see:
```
============================================================
ADMIN CREDENTIALS:
============================================================
Email: nickrichard292@gmail.com
Password: Admin123!
============================================================
```

---

### Step 7: Start the Application

```bash
# Go back to project root
cd ../..

# Start both frontend and backend
npm run dev
```

You should see:
```
[dev:backend] ============================================================
[dev:backend] FaceFind Forensics API v2 - Complete System
[dev:backend] ============================================================
[dev:backend] [OK] Server ready on http://localhost:5001
[dev:frontend] Compiled successfully!
[dev:frontend] You can now view frontend in the browser.
[dev:frontend]   Local:            http://localhost:3000
```

---

### Step 8: Access the Application

1. Open browser: http://localhost:3000
2. Click "Admin Login"
3. Enter:
   - Email: nickrichard292@gmail.com
   - Password: Admin123!
4. Check your email for OTP
5. Enter OTP
6. You're in! 🎉

---

## 🔧 Verification Checklist

Before running, verify:

- [ ] Python 3.10+ installed (`python --version`)
- [ ] Node.js 16+ installed (`node --version`)
- [ ] Git installed (`git --version`)
- [ ] All npm packages installed (`npm install` completed)
- [ ] All Python packages installed (`pip install -r requirements.txt` completed)
- [ ] Backend `.env` file created and configured
- [ ] Frontend `.env` file created
- [ ] Gmail App Password obtained and added to `.env`
- [ ] Admin user created (`python create_admin_auto.py`)
- [ ] Both servers start without errors (`npm run dev`)

---

## 🐛 Common Issues & Solutions

### Issue 1: "ModuleNotFoundError: No module named 'cv2'"

**Solution:**
```bash
pip install opencv-python-headless
```

### Issue 2: "ModuleNotFoundError: No module named 'tf_keras'"

**Solution:**
```bash
pip install tf-keras
```

### Issue 3: "UnicodeEncodeError" on Windows

**Solution:** Already fixed in code. If you see this, pull latest changes.

### Issue 4: Backend won't start - Port 5001 in use

**Solution:**
```bash
# Windows
netstat -ano | findstr :5001
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:5001 | xargs kill -9
```

### Issue 5: Frontend can't connect to backend

**Check:**
1. Backend is running (you should see "Server ready on http://localhost:5001")
2. No firewall blocking port 5001
3. `.env` in frontend has correct API URL

### Issue 6: OTP emails not arriving

**Check:**
1. SMTP credentials in `.env` are correct
2. Using App Password (not regular Gmail password)
3. 2-Step Verification enabled in Google Account
4. Check spam folder
5. Try generating new App Password

### Issue 7: Database errors

**Solution:**
```bash
cd face-similarity-app/python-backend
python recreate_database.py
```
**Warning:** This deletes all data!

---

## 📝 Testing the System

### Test 1: Admin Login
1. Go to http://localhost:3000
2. Click "Admin Login"
3. Enter credentials
4. Verify OTP email arrives
5. Enter OTP
6. Should redirect to Admin Dashboard

### Test 2: Create Officer
1. Login as Admin
2. Click "Add New Officer"
3. Fill form with test data
4. Submit
5. Check email for temporary password

### Test 3: Officer Login
1. Logout from Admin
2. Click "Officer Login"
3. Enter officer email and temporary password
4. Should redirect to Change Password page
5. Change password
6. Should redirect to main app

### Test 4: Face Comparison
1. Login (Admin or Officer)
2. Go to "Face Comparison" tab
3. Upload a sketch image
4. Upload a photo image
5. Click "Compare Faces"
6. Should see similarity score

### Test 5: Criminal Database
1. Go to "Criminal Database" tab
2. Click "Add Criminal"
3. Fill form and upload photo
4. Submit
5. Should see criminal in list

---

## 🎯 Next Steps After Setup

1. **Change Admin Password**: Login and change default password
2. **Update JWT Secret**: Change `JWT_SECRET` in `.env` to random string
3. **Add Test Data**: Add some criminal records for testing
4. **Test Face Comparison**: Upload test images and verify accuracy
5. **Create Officer Accounts**: Add officers for your team

---

## 📞 Need Help?

If you're stuck:

1. Read error messages carefully
2. Check this guide's troubleshooting section
3. Verify all dependencies are installed
4. Ensure `.env` files are configured correctly
5. Try restarting the servers

---

## ✅ Success Indicators

You'll know setup is successful when:

- ✅ `npm run dev` starts both servers without errors
- ✅ Frontend loads at http://localhost:3000
- ✅ Backend responds at http://localhost:5001
- ✅ Admin login works with OTP
- ✅ Officer creation sends email
- ✅ Face comparison returns results
- ✅ Criminal database operations work

---

**Congratulations! Your FaceFind Forensics system is ready! 🎉**
