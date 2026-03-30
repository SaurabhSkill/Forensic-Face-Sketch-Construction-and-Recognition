# 🔍 FaceFind Forensics - AI-Powered Face Recognition System

A production-ready forensic face matching system with role-based authentication, criminal database management, and advanced AI-powered face comparison using dual embedding models (InsightFace + Facenet512).

![System Status](https://img.shields.io/badge/status-production--ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![React](https://img.shields.io/badge/react-18.x-blue)
![TensorFlow](https://img.shields.io/badge/tensorflow-2.13.0-orange)
![DeepFace](https://img.shields.io/badge/deepface-0.0.93-orange)

---

## 🎯 Key Features

### 🔐 Advanced Authentication System
- **Admin Login**: Two-factor authentication with OTP via email
- **Officer Login**: Secure email + password authentication
- **Role-Based Access Control**: Granular permissions for Admin and Officer roles
- **JWT Token Security**: Industry-standard token-based authentication
- **Password Management**: Forced password change on first login for officers
- **Session Management**: Automatic token refresh and secure logout

### 👤 Criminal Database Management
- **Complete CRUD Operations**: Add, view, update, and delete criminal records
- **AWS S3 Photo Storage**: Scalable cloud storage for criminal photos
- **Comprehensive Profiles**: Detailed forensic data including:
  - Personal information (name, aliases, age, gender)
  - Physical appearance (height, weight, build, complexion)
  - Identifying marks (scars, tattoos, birthmarks)
  - Criminal history and evidence
  - Known locations and associates
- **Advanced Search**: Multi-criteria search and filtering
- **Photo Management**: Secure upload, retrieval, and deletion

### 🤖 AI-Powered Face Comparison
- **Dual Embedding System**: 
  - InsightFace ArcFace R50 (ONNX) - Primary model
  - Facenet512 (DeepFace) - Secondary model
  - Hybrid scoring for maximum accuracy
- **Sketch-to-Photo Matching**: Advanced cross-domain face matching
- **Multi-Region Analysis**: Separate scoring for eyes, nose, mouth
- **Geometric Similarity**: Facial landmark-based comparison
- **Database Search**: Match uploaded sketches against entire criminal database
- **FAISS Integration**: Lightning-fast vector similarity search
- **Performance Optimization**: 
  - Embedding caching system
  - Result caching for repeated queries
  - Precomputed database embeddings
- **Confidence Scoring**: High/Medium/Low confidence levels with detailed metrics

### 🎨 Modern Premium UI
- **Glassmorphism Design**: Modern glass-effect UI with dark theme
- **Neon Accents**: Professional forensic/security aesthetic
- **Responsive Layout**: Optimized for desktop, tablet, and mobile
- **Smooth Animations**: Professional transitions and micro-interactions
- **Interactive Components**: Drag-and-drop, real-time updates
- **Data Visualization**: Charts and graphs for match results

### ☁️ Cloud Infrastructure
- **AWS S3 Integration**: 
  - Separate buckets for criminal images and ML models
  - Automatic model download on deployment
  - Signed URLs for secure access
- **PostgreSQL Database**: Supabase-hosted production database
- **Scalable Architecture**: Ready for horizontal scaling

---

## 📋 Prerequisites

Ensure you have the following installed:

- **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 16+** - [Download Node.js](https://nodejs.org/)
- **Git** - [Download Git](https://git-scm.com/)
- **AWS Account** (for S3 storage) - [AWS Console](https://aws.amazon.com/)
- **Supabase Account** (for PostgreSQL) - [Supabase](https://supabase.com/)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/SaurabhSkill/Forensic-Face-Sketch-Construction-and-Recognition.git
cd Forensic-Face-Sketch-Construction-and-Recognition
```

### 2. Install Dependencies

#### Root Dependencies (Concurrently)
```bash
npm install
```

#### Backend Dependencies
```bash
cd face-similarity-app/python-backend
pip install -r requirements.txt
```

**Note:** On Windows, if `pip` fails, try:
```bash
python -m pip install -r requirements.txt
```

#### Frontend Dependencies
```bash
cd face-similarity-app/frontend
npm install
```

### 3. Configure Environment Variables

#### Backend Configuration

Create `.env` in `face-similarity-app/python-backend/`:

```bash
cd face-similarity-app/python-backend
cp .env.example .env  # Mac/Linux
# OR
copy .env.example .env  # Windows
```

Edit `.env` with your credentials:

```env
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=ap-south-1
AWS_S3_BUCKET_NAME=criminal-images-bucket-name

# Model S3 Configuration (separate bucket)
MODEL_S3_BUCKET=forensic-models
FACENET_S3_KEY=facenet512_weights.h5
INSIGHTFACE_S3_KEY=w600k_r50.onnx

# JWT Secret (change to random string)
JWT_SECRET=your-secret-key-change-this

# SMTP Configuration (for OTP emails)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password

# Server Port
PORT=5001
```

**Getting Gmail App Password:**
1. Enable 2-Step Verification in Google Account
2. Go to Security → App Passwords
3. Generate password for "Mail"
4. Copy 16-character password to `SMTP_PASSWORD`

#### Frontend Configuration

Create `.env` in `face-similarity-app/frontend/`:

```bash
cd face-similarity-app/frontend
cp .env.example .env  # Mac/Linux
# OR
copy .env.example .env  # Windows
```

Default configuration:
```env
REACT_APP_API_URL=http://localhost:5001
```

### 4. Upload Models to S3 (One-Time Setup)

Upload the ML model files to your S3 bucket:

```bash
# Upload Facenet512 model (~90 MB)
aws s3 cp facenet512_weights.h5 s3://forensic-models/

# Upload InsightFace model (~166 MB)
aws s3 cp w600k_r50.onnx s3://forensic-models/
```

**Note:** Models will be automatically downloaded from S3 on first backend startup.

### 5. Initialize Database

Create the admin user:

```bash
cd face-similarity-app/python-backend
python create_admin_auto.py
```

Default admin credentials:
- **Email**: admin@forensic.gov.in
- **Password**: Admin123!

**⚠️ Change these credentials after first login!**

### 6. Start the Application

From the project root:

```bash
npm run dev
```

This starts:
- **Backend** (Flask) → http://localhost:5001
- **Frontend** (React) → http://localhost:3000

### 7. Access the Application

Open browser: **http://localhost:3000**

**Admin Login:**
1. Click "Admin Login"
2. Enter email and password
3. Check email for OTP code
4. Enter OTP to complete login

**Officer Login:**
1. Admin creates officer account
2. Officer receives temporary password via email
3. Officer logs in and changes password

---

## 📁 Project Structure

```
Forensic-Face-Sketch-Construction-and-Recognition/
├── face-similarity-app/
│   ├── frontend/                          # React Frontend
│   │   ├── public/
│   │   │   └── assets/                    # Face sketch elements
│   │   ├── src/
│   │   │   ├── components/                # Reusable UI components
│   │   │   ├── pages/                     # Page components
│   │   │   │   ├── AdminDashboard.js
│   │   │   │   ├── OfficerDashboard.js
│   │   │   │   ├── CriminalDatabase.js
│   │   │   │   ├── FaceComparison.js
│   │   │   │   └── SketchBuilder.js
│   │   │   ├── services/                  # API services
│   │   │   ├── hooks/                     # Custom React hooks
│   │   │   ├── layout/                    # Layout components
│   │   │   ├── theme/                     # Theme configuration
│   │   │   └── App.js
│   │   ├── package.json
│   │   └── .env
│   │
│   └── python-backend/                    # Flask Backend
│       ├── models/                        # ML model wrappers
│       │   ├── insightface_model.py       # InsightFace ArcFace R50
│       │   └── facenet_model.py           # Facenet512
│       ├── services/                      # Business logic
│       │   ├── embedding_service.py       # Embedding extraction
│       │   ├── face_comparison_service.py # Face matching logic
│       │   ├── faiss_service.py           # Vector search
│       │   ├── s3_service.py              # AWS S3 operations
│       │   └── region_analysis_service.py # Facial region analysis
│       ├── preprocessing/                 # Image preprocessing
│       │   └── sketch_photo_preprocess.py
│       ├── utils/                         # Utility functions
│       │   ├── s3_model_loader.py         # S3 model download
│       │   ├── file_utils.py
│       │   ├── cache_utils.py
│       │   └── similarity_utils.py
│       ├── app_v2.py                      # Main Flask application
│       ├── auth_v2.py                     # Authentication logic
│       ├── database.py                    # Database models
│       ├── requirements.txt               # Python dependencies
│       └── .env
│
├── package.json                           # Root package (npm run dev)
├── .gitignore
└── README.md
```

---

## 🔧 Available Scripts

### Root Directory

```bash
npm run dev              # Start both frontend and backend
npm run dev:frontend     # Start only frontend
npm run dev:backend      # Start only backend
```

### Backend Directory

```bash
python app_v2.py                    # Start Flask server
python create_admin_auto.py         # Create admin user
```

### Frontend Directory

```bash
npm start                # Development server
npm run build            # Production build
npm test                 # Run tests
```

---

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/admin/login-step1` | Admin login (email + password) |
| POST | `/api/auth/admin/login-step2` | Admin OTP verification |
| POST | `/api/auth/admin/resend-otp` | Resend OTP code |
| POST | `/api/auth/officer/login` | Officer login |
| POST | `/api/auth/change-password` | Change password |
| GET | `/api/auth/verify` | Verify JWT token |

### Admin Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/officers` | List all officers |
| POST | `/api/admin/officers` | Create new officer |
| POST | `/api/admin/officers/:id/reset-password` | Reset officer password |
| DELETE | `/api/admin/officers/:id` | Delete officer |

### Criminal Database

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/criminals` | Get all criminals |
| POST | `/api/criminals` | Add new criminal |
| GET | `/api/criminals/:id` | Get criminal by ID |
| PUT | `/api/criminals/:id` | Update criminal |
| DELETE | `/api/criminals/:id` | Delete criminal |
| GET | `/api/criminals/:id/photo` | Get criminal photo |
| POST | `/api/criminals/search` | Search by sketch |

### Face Comparison

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/compare` | Compare two faces |
| POST | `/api/criminals/search` | Match sketch against database |
| GET | `/api/cache/stats` | Get cache statistics |
| POST | `/api/cache/clear` | Clear all caches |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Server health status |

---

## 🤖 AI Models & Technology

### Dual Embedding System

**Primary Model: InsightFace ArcFace R50**
- Architecture: ResNet-50 backbone
- Training: MS1MV3 dataset (5.2M images)
- Embedding: 512-dimensional L2-normalized vectors
- Format: ONNX (onnxruntime)
- Size: 166 MB
- Accuracy: State-of-the-art on LFW, CFP-FP, AgeDB

**Secondary Model: Facenet512**
- Architecture: Inception-ResNet-v1
- Training: VGGFace2 dataset
- Embedding: 512-dimensional vectors
- Framework: TensorFlow 2.13 + Keras 2.13
- Size: 90 MB
- Purpose: Cross-validation and ensemble scoring

### Hybrid Scoring Algorithm

```
Final Score = (0.5 × InsightFace) + (0.5 × Facenet512)
            + Region Weights × (Eyes + Nose + Mouth)
            + Geometric Similarity Bonus
```

### Performance Optimizations

- **FAISS Vector Search**: Sub-millisecond similarity search
- **Embedding Cache**: Precomputed embeddings for all criminals
- **Result Cache**: LRU cache for repeated queries
- **Batch Processing**: Parallel embedding extraction
- **S3 Model Loading**: Automatic download on deployment

---

## 🛠️ Troubleshooting

### Backend Issues

**ModuleNotFoundError: No module named 'cv2'**
```bash
pip install opencv-python-headless
```

**TensorFlow/Keras version conflicts**
```bash
pip uninstall tensorflow keras tf-keras
pip install tensorflow==2.13.0 keras==2.13.1
```

**Models not downloading from S3**
```bash
# Check S3 configuration
python -c "from utils.s3_model_loader import setup_models; setup_models()"

# Verify AWS credentials
aws s3 ls s3://forensic-models/
```

### Frontend Issues

**Cannot connect to backend**
- Ensure backend is running on port 5001
- Check `.env` has correct `REACT_APP_API_URL`
- Verify CORS is enabled in Flask

**Build fails**
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Database Issues

**Connection refused**
- Check DATABASE_URL in `.env`
- Verify Supabase project is active
- Test connection: `psql $DATABASE_URL`

**Table doesn't exist**
```bash
python create_admin_auto.py  # Creates tables automatically
```

### Port Already in Use

**Windows:**
```bash
netstat -ano | findstr :5001
taskkill /PID <PID> /F
```

**Mac/Linux:**
```bash
lsof -ti:5001 | xargs kill -9
```

---

## 🔒 Security Best Practices

1. **Change Default Credentials**: Update admin email/password immediately
2. **Strong JWT Secret**: Use cryptographically random string (32+ characters)
3. **Environment Variables**: Never commit `.env` files
4. **HTTPS in Production**: Use SSL/TLS certificates
5. **Database Security**: Use connection pooling and prepared statements
6. **S3 Bucket Policies**: Restrict access with IAM policies
7. **Rate Limiting**: Implement API rate limiting in production
8. **Input Validation**: All inputs are sanitized and validated
9. **Password Hashing**: bcrypt with salt rounds
10. **Token Expiration**: JWT tokens expire after 24 hours

---

## 📦 Technology Stack

### Backend
- **Framework**: Flask 3.0.3
- **Database**: PostgreSQL (Supabase)
- **ORM**: SQLAlchemy 2.0.23
- **AI/ML**: 
  - TensorFlow 2.13.0
  - DeepFace 0.0.93
  - ONNX Runtime 1.18.0
  - FAISS 1.7.4
- **Cloud**: AWS S3 (boto3)
- **Auth**: bcrypt, PyJWT
- **Image Processing**: OpenCV 4.10

### Frontend
- **Framework**: React 18.3.1
- **Routing**: React Router 6.30
- **HTTP Client**: Axios 1.11
- **Charts**: Recharts 3.7
- **3D Graphics**: Three.js 0.160
- **UI**: Custom CSS with Glassmorphism

### DevOps
- **Version Control**: Git
- **Package Manager**: npm, pip
- **Process Manager**: Concurrently
- **Environment**: dotenv

---

## 🚀 Deployment

### AWS EC2 Deployment

1. **Launch EC2 Instance**
   - Ubuntu 22.04 LTS
   - t3.medium or larger (4GB+ RAM)
   - Security group: Allow ports 80, 443, 5001, 3000

2. **Install Dependencies**
   ```bash
   sudo apt update
   sudo apt install python3.10 python3-pip nodejs npm nginx
   ```

3. **Clone and Setup**
   ```bash
   git clone <repo-url>
   cd Forensic-Face-Sketch-Construction-and-Recognition
   npm install
   cd face-similarity-app/python-backend
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   - Copy `.env.example` to `.env`
   - Update with production credentials
   - Set `REACT_APP_API_URL` to EC2 public IP

5. **Setup Nginx**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:3000;
       }
       
       location /api {
           proxy_pass http://localhost:5001;
       }
   }
   ```

6. **Start Services**
   ```bash
   # Use PM2 or systemd for production
   npm run dev
   ```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

This project is for educational and forensic purposes only.

---

## 👥 Authors

Developed for forensic face matching and criminal identification.

---

## 🙏 Acknowledgments

- **DeepFace** - Face recognition framework
- **InsightFace** - State-of-the-art face recognition models
- **TensorFlow** - Deep learning platform
- **FAISS** - Efficient similarity search
- **React** - UI framework
- **Flask** - Web framework

---

## 📞 Support

For issues and questions:
- Check [Troubleshooting](#-troubleshooting) section
- Review error messages carefully
- Ensure all dependencies are installed
- Verify environment configuration

---

**Built with ❤️ for Forensic Science**
