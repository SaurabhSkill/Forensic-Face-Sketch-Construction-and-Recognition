# FaceFind Forensics - AI-Powered Face Recognition System

A complete forensic face matching system with role-based authentication, criminal database management, and AI-powered face comparison using DeepFace.

![System Status](https://img.shields.io/badge/status-production--ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.10-blue)
![React](https://img.shields.io/badge/react-18.x-blue)
![DeepFace](https://img.shields.io/badge/deepface-0.0.96-orange)

## 🎯 Features

### Authentication System
- **Admin Login**: Two-step authentication with OTP via email
- **Officer Login**: Simple email + password authentication
- **Role-Based Access Control**: Admin and Officer roles with different permissions
- **JWT Token Security**: Secure token-based authentication
- **Password Management**: First-time password change for officers

### Criminal Database
- **CRUD Operations**: Add, view, update, and delete criminal records
- **Photo Management**: Store and retrieve criminal photos
- **Detailed Profiles**: Comprehensive forensic data including appearance, locations, evidence, etc.
- **Search Functionality**: Find criminals by various criteria

### Face Comparison (AI-Powered)
- **DeepFace Integration**: Uses Facenet512 model for accurate face recognition
- **Sketch-to-Photo Matching**: Compare forensic sketches with criminal photos
- **Database Search**: Match uploaded sketches against entire criminal database
- **Performance Optimization**: Caching system for faster comparisons
- **Confidence Scoring**: High/Medium/Low confidence levels for matches

### Modern UI
- **Premium Design**: Glassmorphism with dark theme and neon accents
- **Responsive Layout**: Works on desktop and mobile devices
- **Smooth Animations**: Professional transitions and effects
- **Forensic Theme**: Professional government/security aesthetic

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 16+** - [Download Node.js](https://nodejs.org/)
- **Git** - [Download Git](https://git-scm.com/)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd forensic-face-sketch-avishkar
```

### 2. Install Dependencies

#### Install Node Dependencies (Root)
```bash
npm install
```

#### Install Python Dependencies
```bash
cd face-similarity-app/python-backend
pip install -r requirements.txt
```

**Note:** If you encounter issues with `pip`, try:
```bash
python -m pip install -r requirements.txt
```

### 3. Configure Environment Variables

#### Backend Configuration
Create `.env` file in `face-similarity-app/python-backend/`:

```bash
cd face-similarity-app/python-backend
copy .env.example .env  # Windows
# OR
cp .env.example .env    # Mac/Linux
```

Edit `.env` and add your SMTP credentials:

```env
# SMTP Configuration for OTP emails
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=FaceFind Forensics

# JWT Secret (change this to a random string)
JWT_SECRET=your-secret-key-here-change-this

# Database
DATABASE_URL=sqlite:///criminal_database.db
```

**Getting Gmail App Password:**
1. Go to Google Account Settings
2. Security → 2-Step Verification (enable it)
3. App Passwords → Generate new app password
4. Copy the 16-character password to `SMTP_PASSWORD`

#### Frontend Configuration
Create `.env` file in `face-similarity-app/frontend/`:

```bash
cd face-similarity-app/frontend
copy .env.example .env  # Windows
# OR
cp .env.example .env    # Mac/Linux
```

The default configuration should work:
```env
REACT_APP_API_BASE_URL=http://localhost:5001
```

### 4. Initialize Database

Create the admin user:

```bash
cd face-similarity-app/python-backend
python create_admin_auto.py
```

This creates an admin account with:
- **Email**: nickrichard292@gmail.com
- **Password**: Admin123!

**Important:** Change these credentials after first login!

### 5. Start the Application

From the project root directory:

```bash
npm run dev
```

This starts both:
- **Backend** (Python/Flask) on http://localhost:5001
- **Frontend** (React) on http://localhost:3000

### 6. Access the Application

Open your browser and go to:
```
http://localhost:3000
```

**Login as Admin:**
1. Click "Admin Login"
2. Enter email and password
3. Check your email for OTP
4. Enter OTP to complete login

**Login as Officer:**
1. Admin must first create an officer account
2. Officer receives temporary password via email
3. Officer logs in and changes password

---

## 📁 Project Structure

```
forensic-face-sketch-avishkar/
├── face-similarity-app/
│   ├── frontend/                 # React frontend
│   │   ├── public/
│   │   ├── src/
│   │   │   ├── components/      # Reusable components
│   │   │   ├── pages/           # Page components
│   │   │   ├── App.js           # Main app component
│   │   │   └── index.js         # Entry point
│   │   ├── package.json
│   │   └── .env                 # Frontend config
│   │
│   └── python-backend/          # Flask backend
│       ├── app_v2.py            # Main application (USE THIS)
│       ├── auth_v2.py           # Authentication logic
│       ├── database.py          # Database models
│       ├── requirements.txt     # Python dependencies
│       ├── .env                 # Backend config (SMTP, JWT)
│       └── criminal_database.db # SQLite database (auto-created)
│
├── package.json                 # Root package.json (npm run dev)
├── .gitignore
└── README.md
```

---

## 🔧 Available Scripts

### Root Directory

```bash
npm run dev              # Start both frontend and backend
npm run dev:frontend     # Start only frontend
npm run dev:backend      # Start only backend (app_v2.py)
```

### Backend Directory

```bash
python app_v2.py                    # Start backend server
python create_admin_auto.py         # Create admin user
python recreate_database.py         # Reset database (WARNING: deletes all data)
```

### Frontend Directory

```bash
npm start                # Start development server
npm run build            # Create production build
npm test                 # Run tests
```

---

## 🔐 Default Credentials

**Admin Account:**
- Email: nickrichard292@gmail.com
- Password: Admin123!

**Note:** Change these credentials immediately after first login for security!

---

## 📚 API Endpoints

### Authentication
- `POST /api/auth/admin/login-step1` - Admin login (email + password)
- `POST /api/auth/admin/login-step2` - Admin OTP verification
- `POST /api/auth/admin/resend-otp` - Resend OTP
- `POST /api/auth/officer/login` - Officer login
- `POST /api/auth/change-password` - Change password
- `GET /api/auth/verify` - Verify JWT token

### Admin Management
- `GET /api/admin/officers` - List all officers
- `POST /api/admin/officers` - Add new officer
- `POST /api/admin/officers/:id/reset-password` - Reset officer password
- `DELETE /api/admin/officers/:id` - Delete officer

### Criminal Database
- `GET /api/criminals` - Get all criminals
- `POST /api/criminals` - Add criminal
- `GET /api/criminals/:id` - Get criminal by ID
- `GET /api/criminals/:id/photo` - Get criminal photo
- `DELETE /api/criminals/:id` - Delete criminal
- `POST /api/criminals/search` - Search by sketch

### Face Comparison
- `POST /api/compare` - Compare two faces
- `GET /api/cache/stats` - Get cache statistics
- `POST /api/cache/clear` - Clear caches

---

## 🛠️ Troubleshooting

### Backend won't start

**Issue:** `ModuleNotFoundError: No module named 'cv2'`

**Solution:**
```bash
cd face-similarity-app/python-backend
pip install opencv-python-headless deepface tf-keras
```

### Database errors

**Issue:** Database locked or corrupted

**Solution:**
```bash
cd face-similarity-app/python-backend
python recreate_database.py
```

**Warning:** This deletes all data!

### OTP emails not sending

**Issue:** SMTP authentication failed

**Solution:**
1. Check `.env` file has correct Gmail credentials
2. Ensure you're using an App Password (not regular password)
3. Enable 2-Step Verification in Google Account
4. Generate new App Password

### Port already in use

**Issue:** `Address already in use: 5001` or `3000`

**Solution:**

**Windows:**
```bash
# Kill process on port 5001
netstat -ano | findstr :5001
taskkill /PID <PID> /F

# Kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**Mac/Linux:**
```bash
# Kill process on port 5001
lsof -ti:5001 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

### Frontend can't connect to backend

**Issue:** `ERR_CONNECTION_REFUSED`

**Solution:**
1. Ensure backend is running: `cd face-similarity-app/python-backend && python app_v2.py`
2. Check backend is on port 5001
3. Verify `.env` in frontend has correct API URL

---

## 🔒 Security Notes

1. **Change Default Credentials**: Update admin email/password after first login
2. **JWT Secret**: Change `JWT_SECRET` in `.env` to a random string
3. **SMTP Credentials**: Never commit `.env` files to Git
4. **Database**: The `.db` file is gitignored - don't commit it
5. **Production**: Use environment variables, not `.env` files in production

---

## 📦 Dependencies

### Backend (Python)
- Flask 3.0.3 - Web framework
- DeepFace 0.0.96 - Face recognition
- TensorFlow 2.20.0 - Deep learning
- OpenCV - Image processing
- SQLAlchemy - Database ORM
- bcrypt - Password hashing
- PyJWT - JWT tokens

### Frontend (React)
- React 18.x - UI framework
- Axios - HTTP client
- React Router - Navigation
- CSS3 - Styling (no external UI library)

---

## 🤝 Contributing

This is a forensic project. If you want to contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📄 License

This project is for educational and forensic purposes only.

---

## 👥 Team

Developed for forensic face matching and criminal identification.

---

## 📞 Support

If you encounter any issues:

1. Check the Troubleshooting section above
2. Review the error messages carefully
3. Ensure all dependencies are installed
4. Check that `.env` files are configured correctly

---

## 🎉 Acknowledgments

- DeepFace library for face recognition
- TensorFlow and Keras for deep learning
- React community for frontend tools
- Flask for the backend framework

---

**Happy Coding! 🚀**
