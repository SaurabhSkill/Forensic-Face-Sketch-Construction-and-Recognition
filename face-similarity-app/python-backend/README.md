# 🔧 FaceFind Forensics - Backend API

Flask-based REST API with dual AI models (InsightFace + Facenet512) for forensic face matching.

---

## 🎯 Features

- **Dual Embedding System**: InsightFace ArcFace R50 + Facenet512
- **AWS S3 Integration**: Automatic model download and image storage
- **FAISS Vector Search**: Lightning-fast similarity search
- **PostgreSQL Database**: Supabase-hosted production database
- **Role-Based Auth**: Admin (OTP) + Officer authentication
- **Caching System**: Embedding and result caching
- **Multi-Region Analysis**: Eyes, nose, mouth similarity scoring

---

## 📋 Prerequisites

- Python 3.10+
- PostgreSQL (Supabase)
- AWS S3 account
- SMTP server (Gmail)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env  # Mac/Linux
copy .env.example .env  # Windows
```

Edit `.env`:

```env
# Database
DATABASE_URL=postgresql://postgres.[project]:[password]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# AWS S3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=ap-south-1
AWS_S3_BUCKET_NAME=criminal-images-bucket

# Model S3 (separate bucket)
MODEL_S3_BUCKET=forensic-models
FACENET_S3_KEY=facenet512_weights.h5
INSIGHTFACE_S3_KEY=w600k_r50.onnx

# JWT
JWT_SECRET=your-random-secret-key

# SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Server
PORT=5001
```

### 3. Upload Models to S3

```bash
aws s3 cp facenet512_weights.h5 s3://forensic-models/
aws s3 cp w600k_r50.onnx s3://forensic-models/
```

### 4. Initialize Database

```bash
python create_admin_auto.py
```

### 5. Start Server

```bash
python app_v2.py
```

Server runs on: **http://localhost:5001**

---

## 📁 Project Structure

```
python-backend/
├── models/                          # ML model wrappers
│   ├── insightface_model.py         # InsightFace ArcFace R50 (ONNX)
│   └── facenet_model.py             # Facenet512 (TensorFlow)
│
├── services/                        # Business logic
│   ├── embedding_service.py         # Embedding extraction
│   ├── face_comparison_service.py   # Face matching logic
│   ├── faiss_service.py             # Vector similarity search
│   ├── s3_service.py                # AWS S3 operations
│   └── region_analysis_service.py   # Facial region analysis
│
├── preprocessing/                   # Image preprocessing
│   └── sketch_photo_preprocess.py   # Sketch/photo preprocessing
│
├── utils/                           # Utilities
│   ├── s3_model_loader.py           # S3 model download
│   ├── file_utils.py                # File operations
│   ├── cache_utils.py               # Caching utilities
│   └── similarity_utils.py          # Similarity metrics
│
├── app_v2.py                        # Main Flask application
├── auth_v2.py                       # Authentication logic
├── database.py                      # Database models (SQLAlchemy)
├── requirements.txt                 # Python dependencies
└── .env                             # Environment configuration
```

---

## 🤖 AI Models

### InsightFace ArcFace R50 (Primary)

- **Architecture**: ResNet-50
- **Training**: MS1MV3 (5.2M images)
- **Embedding**: 512-D L2-normalized
- **Format**: ONNX (onnxruntime)
- **Size**: 166 MB
- **Location**: `~/.insightface/models/buffalo_l/w600k_r50.onnx`

### Facenet512 (Secondary)

- **Architecture**: Inception-ResNet-v1
- **Training**: VGGFace2
- **Embedding**: 512-D
- **Framework**: TensorFlow 2.13 + Keras 2.13
- **Size**: 90 MB
- **Location**: `~/.deepface/weights/facenet512_weights.h5`

### Model Loading

Models are automatically downloaded from S3 on first startup:

```python
# In app_v2.py
setup_models()           # Download from S3 if missing
initialize_models()      # Load into memory
precompute_database_embeddings()  # Cache embeddings
```

---

## 📚 API Endpoints

### Authentication

```
POST   /api/auth/admin/login-step1      Admin login (email + password)
POST   /api/auth/admin/login-step2      Admin OTP verification
POST   /api/auth/admin/resend-otp       Resend OTP
POST   /api/auth/officer/login          Officer login
POST   /api/auth/change-password        Change password
GET    /api/auth/verify                 Verify JWT token
```

### Admin Management

```
GET    /api/admin/officers              List all officers
POST   /api/admin/officers              Create officer
POST   /api/admin/officers/:id/reset-password  Reset password
DELETE /api/admin/officers/:id          Delete officer
```

### Criminal Database

```
GET    /api/criminals                   Get all criminals
POST   /api/criminals                   Add criminal
GET    /api/criminals/:id               Get criminal by ID
PUT    /api/criminals/:id               Update criminal
DELETE /api/criminals/:id               Delete criminal
GET    /api/criminals/:id/photo         Get criminal photo
POST   /api/criminals/search            Search by sketch
```

### Face Comparison

```
POST   /api/compare                     Compare two faces
POST   /api/criminals/search            Match sketch vs database
GET    /api/cache/stats                 Cache statistics
POST   /api/cache/clear                 Clear caches
```

### Health Check

```
GET    /api/health                      Server health status
```

---

## 🔍 Face Comparison Algorithm

### Hybrid Scoring

```python
# Dual embedding extraction
insightface_emb = extract_insightface_embedding(image)
facenet_emb = extract_facenet_embedding(image)

# Cosine similarity
insightface_score = cosine_similarity(emb1, emb2)
facenet_score = cosine_similarity(emb1, emb2)

# Hybrid score
base_score = (0.5 * insightface_score) + (0.5 * facenet_score)

# Multi-region analysis
region_scores = {
    'eyes': compute_region_similarity(eyes1, eyes2),
    'nose': compute_region_similarity(nose1, nose2),
    'mouth': compute_region_similarity(mouth1, mouth2)
}

# Geometric similarity
geometric_score = compute_geometric_similarity(landmarks1, landmarks2)

# Final score
final_score = base_score + region_weights + geometric_bonus
```

### Confidence Levels

- **High**: score ≥ 0.75 (Strong match)
- **Medium**: 0.60 ≤ score < 0.75 (Possible match)
- **Low**: score < 0.60 (Unlikely match)

---

## 🚀 Performance Optimizations

### 1. FAISS Vector Search

```python
# Build index from all criminal embeddings
index = faiss.IndexFlatIP(512)  # Inner product (cosine)
index.add(embeddings)

# Search top-k candidates
distances, indices = index.search(query_embedding, k=10)
```

### 2. Embedding Cache

```python
# Precompute embeddings for all criminals
EMBEDDING_CACHE = {
    criminal_id: {
        'insightface': np.array(...),
        'facenet': np.array(...)
    }
}
```

### 3. Result Cache

```python
# LRU cache for repeated queries
RESULT_CACHE = {
    hash(sketch_image): {
        'matches': [...],
        'timestamp': ...
    }
}
```

---

## 🗄️ Database Schema

### User Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255),
    department_name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    officer_id VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(50),  -- 'admin' or 'officer'
    is_temp_password BOOLEAN,
    last_login TIMESTAMP,
    created_at TIMESTAMP
);
```

### Criminal Table

```sql
CREATE TABLE criminals (
    id SERIAL PRIMARY KEY,
    criminal_id VARCHAR(100) UNIQUE,
    name VARCHAR(255),
    aliases TEXT,
    age INTEGER,
    gender VARCHAR(50),
    height VARCHAR(50),
    weight VARCHAR(50),
    build VARCHAR(100),
    complexion VARCHAR(100),
    identifying_marks TEXT,
    criminal_history TEXT,
    evidence TEXT,
    known_locations TEXT,
    known_associates TEXT,
    photo_key VARCHAR(500),  -- S3 key
    photo_filename VARCHAR(255),
    face_embedding JSONB,  -- {insightface: [...], facenet: [...]}
    embedding_version INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### OTP Table

```sql
CREATE TABLE otps (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    otp_code VARCHAR(6),
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_used BOOLEAN
);
```

---

## 🔒 Security

### Password Hashing

```python
import bcrypt

# Hash password
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Verify password
bcrypt.checkpw(password.encode(), password_hash)
```

### JWT Tokens

```python
import jwt

# Generate token
token = jwt.encode({
    'user_id': user.id,
    'email': user.email,
    'role': user.role,
    'exp': datetime.utcnow() + timedelta(hours=24)
}, JWT_SECRET, algorithm='HS256')

# Verify token
payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
```

### OTP Generation

```python
import random

# Generate 6-digit OTP
otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

# Expires in 10 minutes
expires_at = datetime.utcnow() + timedelta(minutes=10)
```

---

## 🛠️ Troubleshooting

### Models Not Loading

```bash
# Check S3 configuration
python -c "from utils.s3_model_loader import setup_models; setup_models()"

# Verify models exist locally
ls ~/.deepface/weights/facenet512_weights.h5
ls ~/.insightface/models/buffalo_l/w600k_r50.onnx
```

### TensorFlow Errors

```bash
# Ensure correct versions
pip uninstall tensorflow keras tf-keras
pip install tensorflow==2.13.0 keras==2.13.1
```

### Database Connection Issues

```bash
# Test connection
python -c "from database import get_db; next(get_db())"
```

### S3 Access Denied

```bash
# Verify AWS credentials
aws s3 ls s3://forensic-models/

# Check IAM permissions
aws iam get-user
```

---

## 📦 Dependencies

### Core Framework
- flask==3.0.3
- flask-cors==4.0.1

### Database
- sqlalchemy==2.0.23
- psycopg2-binary==2.9.9

### AWS
- boto3==1.34.0

### Authentication
- bcrypt==4.1.2
- pyjwt==2.8.0

### AI/ML
- tensorflow==2.13.0
- keras==2.13.1
- deepface==0.0.93
- onnxruntime==1.18.0
- opencv-python-headless==4.10.0.84
- numpy>=1.24,<2.0
- faiss-cpu==1.7.4

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_face_comparison.py
```

---

## 📊 Monitoring

### Cache Statistics

```bash
curl http://localhost:5001/api/cache/stats
```

Response:
```json
{
  "embedding_cache_size": 150,
  "result_cache_size": 45,
  "faiss_index_ready": true,
  "total_criminals": 150
}
```

### Health Check

```bash
curl http://localhost:5001/api/health
```

Response:
```json
{
  "status": "healthy",
  "service": "FaceFind Forensics API v2",
  "timestamp": "2026-03-30T22:00:00Z"
}
```

---

## 🚀 Production Deployment

### Environment Variables

```bash
export FLASK_ENV=production
export TF_CPP_MIN_LOG_LEVEL=2
export TF_ENABLE_ONEDNN_OPTS=0
```

### Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app_v2:app
```

### Systemd Service

```ini
[Unit]
Description=FaceFind Forensics API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/path/to/python-backend
Environment="PATH=/usr/bin/python3"
ExecStart=/usr/bin/python3 app_v2.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📞 Support

For issues:
1. Check logs in console output
2. Verify environment configuration
3. Test S3 and database connectivity
4. Review error messages

---

**Built for Forensic Excellence** 🔍
