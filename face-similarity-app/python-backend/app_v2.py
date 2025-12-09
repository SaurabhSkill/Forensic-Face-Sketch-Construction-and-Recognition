"""
Enhanced Flask Application with Role-Based Authentication + Face Comparison
Admin (with OTP) and Officer roles + DeepFace Integration
"""

import os
import tempfile
import json
import traceback
import io
import cv2
import numpy as np
import hashlib
import time
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from deepface import DeepFace
from database import User, OTP, Criminal, get_db, create_tables
from auth_v2 import (
    hash_password,
    verify_password,
    generate_token,
    generate_otp,
    generate_temp_password,
    send_otp_email,
    send_temp_password_email,
    store_otp,
    verify_otp,
    validate_officer_email_domain,
    admin_only,
    officer_only,
    authenticated
)
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Create database tables
create_tables()

# ============================================================================
# GLOBAL VARIABLES FOR FACE COMPARISON OPTIMIZATION
# ============================================================================

MODEL_INITIALIZED = False
EMBEDDING_CACHE = {}
RESULT_CACHE = {}
CACHE_MAX_SIZE = 100


# ============================================================================
# FACE COMPARISON HELPER FUNCTIONS
# ============================================================================

def initialize_models():
    """Pre-load DeepFace models to ensure consistent performance"""
    global MODEL_INITIALIZED
    if MODEL_INITIALIZED:
        return
    
    print("=" * 60)
    print("Initializing DeepFace models for consistent results...")
    print("=" * 60)
    
    try:
        # Create a dummy image to trigger model loading
        dummy_img = np.ones((224, 224, 3), dtype=np.uint8) * 128
        dummy_path = tempfile.mktemp(suffix='.jpg')
        cv2.imwrite(dummy_path, dummy_img)
        
        try:
            # Pre-load Facenet512 model
            print("Loading Facenet512 model...")
            DeepFace.represent(
                img_path=dummy_path,
                model_name='Facenet512',
                enforce_detection=False
            )
            print("[OK] Facenet512 model loaded successfully")
            
        except Exception as e:
            print(f"Warning during model initialization: {e}")
        
        finally:
            try:
                os.remove(dummy_path)
            except:
                pass
        
        MODEL_INITIALIZED = True
        print("=" * 60)
        print("Model initialization complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Model initialization error: {e}")
        MODEL_INITIALIZED = True  # Continue anyway


def get_file_hash(file_path: str) -> str:
    """Generate MD5 hash of file content for caching"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return None


def normalize_image(image_path: str, is_sketch: bool = False) -> str:
    """
    Gentle normalization for better sketch-photo matching
    - Resize to standard dimensions
    - Apply CLAHE for brightness normalization
    - Subtle contrast enhancement
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        
        # Resize to standard size (max 800px)
        height, width = img.shape[:2]
        max_dim = 800
        if max(height, width) > max_dim:
            scale = max_dim / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # Convert to LAB color space (preserve color info)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel only (slightly stronger for sketches)
        clahe_clip = 3.5 if is_sketch else 3.0
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge channels back
        lab = cv2.merge([l, a, b])
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Very gentle sharpening (don't over-process)
        kernel = np.array([[0,-1,0], 
                         [-1, 5,-1], 
                         [0,-1,0]])
        img = cv2.filter2D(img, -1, kernel)
        
        # Subtle contrast boost
        img = cv2.convertScaleAbs(img, alpha=1.1, beta=5)
        
        # Save normalized image
        normalized_path = tempfile.mktemp(suffix='_normalized.jpg')
        cv2.imwrite(normalized_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        return normalized_path
        
    except Exception as e:
        print(f"Image normalization warning: {e}")
        return image_path


def get_face_embedding(image_path: str, use_cache: bool = True) -> np.ndarray:
    """
    Get face embedding with caching to ensure consistency
    """
    global EMBEDDING_CACHE
    
    # Check cache
    if use_cache:
        file_hash = get_file_hash(image_path)
        if file_hash and file_hash in EMBEDDING_CACHE:
            print(f"[OK] Using cached embedding")
            return EMBEDDING_CACHE[file_hash]
    
    # Generate embedding
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name='Facenet512',
            enforce_detection=False,
            align=True
        )
        
        if isinstance(result, list) and len(result) > 0:
            embedding = np.array(result[0]['embedding'])
        else:
            embedding = np.array(result['embedding'])
        
        # Cache the embedding
        if use_cache and file_hash:
            if len(EMBEDDING_CACHE) >= CACHE_MAX_SIZE:
                # Remove oldest entry
                EMBEDDING_CACHE.pop(next(iter(EMBEDDING_CACHE)))
            EMBEDDING_CACHE[file_hash] = embedding
        
        return embedding
        
    except Exception as e:
        print(f"Embedding generation error: {e}")
        raise


def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """Calculate cosine similarity between two embeddings"""
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    return float(similarity)


def is_sketch_image(image_path: str) -> bool:
    """
    Detect if an image is a sketch based on characteristics:
    - Low color saturation (mostly grayscale)
    - High edge density
    - Limited color palette
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to HSV to check saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        avg_saturation = np.mean(saturation)
        
        # Sketches typically have very low saturation (< 30)
        # Photos typically have higher saturation (> 50)
        is_low_saturation = avg_saturation < 40
        
        # Check edge density (sketches have more edges)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        # Sketches typically have higher edge density (> 0.05)
        is_high_edges = edge_density > 0.03
        
        # If both conditions met, likely a sketch
        return is_low_saturation and is_high_edges
        
    except Exception as e:
        print(f"Sketch detection warning: {e}")
        return False


def optimized_face_comparison(sketch_path: str, photo_path: str, use_cache: bool = True) -> dict:
    """
    Enhanced face comparison with sketch-aware preprocessing for forensic accuracy
    """
    global RESULT_CACHE
    
    # Ensure models are initialized
    initialize_models()
    
    start_time = time.time()
    print(f"\nStarting enhanced face comparison...")
    
    # Check result cache
    cache_key = None
    if use_cache:
        hash1 = get_file_hash(sketch_path)
        hash2 = get_file_hash(photo_path)
        if hash1 and hash2:
            cache_key = f"{hash1}_{hash2}"
            if cache_key in RESULT_CACHE:
                cached_result = RESULT_CACHE[cache_key].copy()
                cached_result['from_cache'] = True
                cached_result['processing_time'] = round(time.time() - start_time, 3)
                print(f"[OK] Result retrieved from cache")
                return cached_result
    
    normalized_img1 = None
    normalized_img2 = None
    
    try:
        # Detect if images are sketches
        is_img1_sketch = is_sketch_image(sketch_path)
        is_img2_sketch = is_sketch_image(photo_path)
        
        print(f"Image 1 is sketch: {is_img1_sketch}")
        print(f"Image 2 is sketch: {is_img2_sketch}")
        
        # Apply enhanced preprocessing
        print("Applying forensic-grade preprocessing...")
        normalized_img1 = normalize_image(sketch_path, is_sketch=is_img1_sketch)
        normalized_img2 = normalize_image(photo_path, is_sketch=is_img2_sketch)
        
        # Use DeepFace.verify with preprocessed images
        print("Running DeepFace verification with enhanced images...")
        result = DeepFace.verify(
            img1_path=normalized_img1,
            img2_path=normalized_img2,
            model_name='Facenet512',
            distance_metric='cosine',
            enforce_detection=False,
            align=True
        )
        
        # Extract results
        distance = float(result['distance'])
        verified = bool(result['verified'])
        threshold = float(result['threshold'])
        
        # Calculate similarity score (0-100%)
        # For cosine distance: 0 = identical, 1 = completely different
        # Convert to similarity percentage
        raw_similarity = max(0.0, min(1.0, 1.0 - distance))
        
        # Apply sketch-specific score normalization
        # Since sketch-to-photo naturally maxes at ~85%, normalize to use full 0-100% range
        is_sketch_comparison = is_img1_sketch or is_img2_sketch
        
        if is_sketch_comparison:
            # Boost sketch scores to utilize full range (80% -> 96%, 60% -> 72%)
            # Formula: normalized = min(1.0, raw * 1.20)
            similarity = min(1.0, raw_similarity * 1.20)
            print(f"  Sketch normalization applied: {raw_similarity*100:.2f}% -> {similarity*100:.2f}%")
        else:
            similarity = raw_similarity
        
        # Determine confidence based on normalized similarity
        if verified:
            if distance < threshold * 0.7:
                confidence = 'high'
            else:
                confidence = 'medium'
        else:
            if distance < threshold * 1.2:
                confidence = 'low'
            else:
                confidence = 'very_low'
        
        elapsed_time = time.time() - start_time
        print(f"[OK] Comparison completed in {elapsed_time:.3f} seconds")
        print(f"  Distance: {distance:.4f} (threshold: {threshold:.4f})")
        print(f"  Raw Similarity: {raw_similarity:.4f} ({raw_similarity*100:.2f}%)")
        print(f"  Display Similarity: {similarity:.4f} ({similarity*100:.2f}%)")
        print(f"  Verified: {verified}")
        print(f"  Confidence: {confidence}")
        
        result_dict = {
            'distance': float(distance),
            'similarity': float(similarity),  # Normalized score (displayed to user)
            'raw_similarity': float(raw_similarity),  # Original score (for reference)
            'is_sketch_comparison': bool(is_sketch_comparison),
            'verified': bool(verified),
            'threshold': float(threshold),
            'model_used': 'Facenet512',
            'metric_used': 'cosine',
            'confidence': confidence,
            'processing_time': round(elapsed_time, 3),
            'from_cache': False
        }
        
        # Cache the result
        if use_cache and cache_key:
            if len(RESULT_CACHE) >= CACHE_MAX_SIZE:
                RESULT_CACHE.pop(next(iter(RESULT_CACHE)))
            RESULT_CACHE[cache_key] = result_dict.copy()
        
        return result_dict
        
    except Exception as e:
        print(f"Comparison error: {e}")
        traceback.print_exc()
        
        elapsed_time = time.time() - start_time
        return {
            'distance': 1.0,
            'similarity': 0.0,
            'verified': False,
            'threshold': 0.4,
            'model_used': 'failed',
            'metric_used': 'none',
            'confidence': 'error',
            'processing_time': round(elapsed_time, 3),
            'error': str(e),
            'from_cache': False
        }
    
    finally:
        # Cleanup normalized temporary images
        if normalized_img1 and normalized_img1 != sketch_path:
            try:
                os.remove(normalized_img1)
            except:
                pass
        if normalized_img2 and normalized_img2 != photo_path:
            try:
                os.remove(normalized_img2)
            except:
                pass


def save_temp_file(file_storage) -> str:
    """Save uploaded file to temporary location"""
    fd, path = tempfile.mkstemp(suffix='_' + file_storage.filename)
    os.close(fd)
    file_storage.save(path)
    return path


def save_bytes_to_temp(data: bytes, original_filename: str) -> str:
    """Save bytes data to temporary file"""
    fd, path = tempfile.mkstemp(suffix='_' + original_filename)
    os.close(fd)
    with open(path, 'wb') as f:
        f.write(data)
    return path


# ============================================================================
# AUTHENTICATION API ENDPOINTS
# ============================================================================

@app.route('/api/auth/admin/login-step1', methods=['POST'])
def admin_login_step1():
    """
    Admin Login Step 1: Verify email and password, then send OTP
    """
    db = None
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400
        
        email = data.get('email').lower().strip()
        password = data.get('password')
        
        db = next(get_db())
        
        # Find admin user
        user = db.query(User).filter(User.email == email, User.role == 'admin').first()
        
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP in database
        if not store_otp(user.id, otp, db):
            return jsonify({"error": "Failed to generate OTP. Please try again."}), 500
        
        # Send OTP via email
        email_sent = send_otp_email(user.email, otp)
        
        if not email_sent:
            # For development: return OTP in response if email fails
            print(f"DEV MODE: OTP for {email} is: {otp}")
            return jsonify({
                "message": "OTP generated (email not configured)",
                "user_id": user.id,
                "otp_dev": otp,  # Remove this in production
                "requires_otp": True
            }), 200
        
        return jsonify({
            "message": "OTP sent to your email",
            "user_id": user.id,
            "requires_otp": True
        }), 200
        
    except Exception as e:
        print(f"/api/auth/admin/login-step1 error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/auth/admin/login-step2', methods=['POST'])
def admin_login_step2():
    """
    Admin Login Step 2: Verify OTP and return JWT token
    """
    db = None
    try:
        data = request.get_json()
        
        if not data.get('user_id') or not data.get('otp'):
            return jsonify({"error": "User ID and OTP are required"}), 400
        
        user_id = data.get('user_id')
        otp = data.get('otp').strip()
        
        db = next(get_db())
        
        # Verify OTP
        if not verify_otp(user_id, otp, db):
            return jsonify({"error": "Invalid or expired OTP"}), 401
        
        # Get user
        user = db.query(User).filter(User.id == user_id, User.role == 'admin').first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Generate JWT token
        token = generate_token(user.id, user.email, user.role)
        
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "department_name": user.department_name,
                "email": user.email,
                "officer_id": user.officer_id,
                "role": user.role,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        }), 200
        
    except Exception as e:
        print(f"/api/auth/admin/login-step2 error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/auth/admin/resend-otp', methods=['POST'])
def admin_resend_otp():
    """Resend OTP to admin"""
    db = None
    try:
        data = request.get_json()
        
        if not data.get('user_id'):
            return jsonify({"error": "User ID is required"}), 400
        
        user_id = data.get('user_id')
        
        db = next(get_db())
        
        # Get user
        user = db.query(User).filter(User.id == user_id, User.role == 'admin').first()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Generate new OTP
        otp = generate_otp()
        
        # Store OTP
        if not store_otp(user.id, otp, db):
            return jsonify({"error": "Failed to generate OTP"}), 500
        
        # Send OTP
        email_sent = send_otp_email(user.email, otp)
        
        if not email_sent:
            print(f"DEV MODE: New OTP for {user.email} is: {otp}")
            return jsonify({
                "message": "OTP generated (email not configured)",
                "otp_dev": otp  # Remove in production
            }), 200
        
        return jsonify({"message": "OTP resent successfully"}), 200
        
    except Exception as e:
        print(f"/api/auth/admin/resend-otp error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/auth/officer/login', methods=['POST'])
def officer_login():
    """
    Officer Login: Email and password only (no OTP)
    """
    db = None
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400
        
        email = data.get('email').lower().strip()
        password = data.get('password')
        
        db = next(get_db())
        
        # Find officer user
        user = db.query(User).filter(User.email == email, User.role == 'officer').first()
        
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Generate JWT token
        token = generate_token(user.id, user.email, user.role)
        
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "department_name": user.department_name,
                "email": user.email,
                "officer_id": user.officer_id,
                "role": user.role,
                "is_temp_password": bool(user.is_temp_password),
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "requires_password_change": bool(user.is_temp_password)
        }), 200
        
    except Exception as e:
        print(f"/api/auth/officer/login error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/auth/change-password', methods=['POST'])
@authenticated
def change_password():
    """Change password (for officers with temporary password)"""
    db = None
    try:
        data = request.get_json()
        user = request.current_user
        
        if not data.get('new_password'):
            return jsonify({"error": "New password is required"}), 400
        
        new_password = data.get('new_password')
        
        # Validate password strength
        if len(new_password) < 8:
            return jsonify({"error": "Password must be at least 8 characters long"}), 400
        
        db = next(get_db())
        
        # Get user from database
        db_user = db.query(User).filter(User.id == user.id).first()
        
        if not db_user:
            return jsonify({"error": "User not found"}), 404
        
        # Update password
        db_user.password_hash = hash_password(new_password)
        db_user.is_temp_password = 0
        
        db.commit()
        
        return jsonify({"message": "Password changed successfully"}), 200
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/auth/change-password error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/auth/verify', methods=['GET'])
@authenticated
def verify_token():
    """Verify if token is valid and return user info"""
    try:
        user = request.current_user
        return jsonify({
            "valid": True,
            "user": {
                "id": user.id,
                "full_name": user.full_name,
                "department_name": user.department_name,
                "email": user.email,
                "officer_id": user.officer_id,
                "role": user.role,
                "is_temp_password": bool(user.is_temp_password),
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/api/admin/officers', methods=['GET'])
@admin_only
def get_all_officers():
    """Admin: Get list of all officers"""
    db = None
    try:
        db = next(get_db())
        
        officers = db.query(User).filter(User.role == 'officer').all()
        
        officers_list = []
        for officer in officers:
            officers_list.append({
                "id": officer.id,
                "full_name": officer.full_name,
                "department_name": officer.department_name,
                "email": officer.email,
                "officer_id": officer.officer_id,
                "is_temp_password": bool(officer.is_temp_password),
                "created_at": officer.created_at.isoformat(),
                "last_login": officer.last_login.isoformat() if officer.last_login else None
            })
        
        return jsonify({"officers": officers_list}), 200
        
    except Exception as e:
        print(f"/api/admin/officers GET error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/admin/officers', methods=['POST'])
@admin_only
def add_officer():
    """Admin: Add a new officer (auto-generate temporary password)"""
    db = None
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['full_name', 'department_name', 'email', 'officer_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400
        
        full_name = data.get('full_name').strip()
        department_name = data.get('department_name').strip()
        email = data.get('email').lower().strip()
        officer_id = data.get('officer_id').strip()
        
        # Get admin's email from current user
        admin_email = request.current_user.email
        
        # Validate email domain (skip validation if email matches admin's email)
        if email != admin_email:
            if not validate_officer_email_domain(email):
                return jsonify({
                    "error": "Invalid email domain. Only government forensic/police emails are allowed.",
                    "allowed_domains": ["@forensic.gov.in", "@police.gov.in", "@stateforensic.gov.in"]
                }), 400
        
        db = next(get_db())
        
        # Check if officer with this email already exists (allow same email for different roles)
        existing_officer = db.query(User).filter(User.email == email, User.role == 'officer').first()
        if existing_officer:
            return jsonify({"error": "Officer with this email already exists"}), 400
        
        # Generate temporary password
        temp_password = generate_temp_password()
        password_hash = hash_password(temp_password)
        
        # Create new officer
        new_officer = User(
            full_name=full_name,
            department_name=department_name,
            email=email,
            officer_id=officer_id,
            password_hash=password_hash,
            role='officer',
            is_temp_password=1
        )
        
        db.add(new_officer)
        db.commit()
        db.refresh(new_officer)
        
        # Send temporary password via email
        email_sent = send_temp_password_email(email, full_name, temp_password)
        
        if not email_sent:
            print(f"DEV MODE: Temp password for {email} is: {temp_password}")
        
        return jsonify({
            "message": "Officer added successfully",
            "officer": {
                "id": new_officer.id,
                "full_name": new_officer.full_name,
                "department_name": new_officer.department_name,
                "email": new_officer.email,
                "officer_id": new_officer.officer_id,
                "created_at": new_officer.created_at.isoformat()
            },
            "temp_password_dev": temp_password if not email_sent else None  # Remove in production
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/admin/officers POST error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/admin/officers/<int:officer_id>/reset-password', methods=['POST'])
@admin_only
def reset_officer_password(officer_id):
    """Admin: Reset officer password (generate new temporary password)"""
    db = None
    try:
        db = next(get_db())
        
        # Get officer
        officer = db.query(User).filter(User.id == officer_id, User.role == 'officer').first()
        
        if not officer:
            return jsonify({"error": "Officer not found"}), 404
        
        # Generate new temporary password
        temp_password = generate_temp_password()
        password_hash = hash_password(temp_password)
        
        # Update officer
        officer.password_hash = password_hash
        officer.is_temp_password = 1
        
        db.commit()
        
        # Send new password via email
        email_sent = send_temp_password_email(officer.email, officer.full_name, temp_password)
        
        if not email_sent:
            print(f"DEV MODE: New temp password for {officer.email} is: {temp_password}")
        
        return jsonify({
            "message": "Password reset successfully",
            "temp_password_dev": temp_password if not email_sent else None  # Remove in production
        }), 200
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/admin/officers/{officer_id}/reset-password error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/admin/officers/<int:officer_id>', methods=['DELETE'])
@admin_only
def delete_officer(officer_id):
    """Admin: Delete an officer account"""
    db = None
    try:
        db = next(get_db())
        
        # Get officer
        officer = db.query(User).filter(User.id == officer_id, User.role == 'officer').first()
        
        if not officer:
            return jsonify({"error": "Officer not found"}), 404
        
        # Delete officer
        db.delete(officer)
        db.commit()
        
        return jsonify({"message": "Officer deleted successfully"}), 200
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/admin/officers/{officer_id} DELETE error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================================================
# CRIMINAL DATABASE ENDPOINTS
# ============================================================================

@app.route('/api/criminals', methods=['GET'])
@authenticated
def get_criminals():
    """Get all criminals from the database"""
    db = None
    try:
        db = next(get_db())
        criminals = db.query(Criminal).all()
        
        criminals_list = []
        for criminal in criminals:
            criminals_list.append({
                "id": criminal.id,
                "criminal_id": criminal.criminal_id,
                "status": criminal.status,
                "full_name": criminal.full_name,
                "aliases": criminal.aliases,
                "dob": criminal.dob,
                "sex": criminal.sex,
                "nationality": criminal.nationality,
                "ethnicity": criminal.ethnicity,
                "photo_filename": criminal.photo_filename,
                "appearance": criminal.appearance,
                "locations": criminal.locations,
                "summary": criminal.summary,
                "forensics": criminal.forensics,
                "evidence": criminal.evidence,
                "witness": criminal.witness,
                "created_at": criminal.created_at.isoformat(),
                "updated_at": criminal.updated_at.isoformat() if criminal.updated_at else None
            })
        
        return jsonify({"criminals": criminals_list}), 200
    except Exception as e:
        print(f"/api/criminals GET error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals', methods=['POST'])
@authenticated
def add_criminal():
    """Add a new criminal to the database"""
    db = None
    try:
        # Validate photo file
        if 'photo' not in request.files:
            return jsonify({"error": "Photo file is required"}), 400
        
        photo_file = request.files['photo']
        
        # Get the JSON data from the 'data' field
        data_json = request.form.get('data', '').strip()
        
        if not data_json:
            return jsonify({"error": "Profile data is required"}), 400
        
        # Parse the JSON data
        try:
            profile_data = json.loads(data_json)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Invalid JSON data: {str(e)}"}), 400
        
        # Validate required fields
        if not profile_data.get('criminal_id'):
            return jsonify({"error": "criminal_id is required"}), 400
        if not profile_data.get('full_name'):
            return jsonify({"error": "full_name is required"}), 400
        if not profile_data.get('status'):
            return jsonify({"error": "status is required"}), 400
        
        # Read photo data
        photo_data = photo_file.read()
        
        # Create new criminal record
        db = next(get_db())
        new_criminal = Criminal(
            criminal_id=profile_data.get('criminal_id'),
            status=profile_data.get('status'),
            full_name=profile_data.get('full_name'),
            aliases=profile_data.get('aliases'),
            dob=profile_data.get('dob'),
            sex=profile_data.get('sex'),
            nationality=profile_data.get('nationality'),
            ethnicity=profile_data.get('ethnicity'),
            photo_data=photo_data,
            photo_filename=photo_file.filename,
            appearance=profile_data.get('appearance'),
            locations=profile_data.get('locations'),
            summary=profile_data.get('summary'),
            forensics=profile_data.get('forensics'),
            evidence=profile_data.get('evidence'),
            witness=profile_data.get('witness')
        )
        
        db.add(new_criminal)
        db.commit()
        db.refresh(new_criminal)
        
        return jsonify({
            "message": "Criminal added successfully",
            "criminal": {
                "id": new_criminal.id,
                "criminal_id": new_criminal.criminal_id,
                "full_name": new_criminal.full_name
            }
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/criminals POST error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/<int:criminal_id>/photo', methods=['GET'])
def get_criminal_photo(criminal_id):
    """Get criminal photo by ID (public endpoint for img tags)"""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        return send_file(
            io.BytesIO(criminal.photo_data),
            mimetype='image/jpeg',
            as_attachment=False
        )
        
    except Exception as e:
        print(f"/api/criminals/{criminal_id}/photo error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/<int:criminal_id>', methods=['GET'])
@authenticated
def get_criminal_by_id(criminal_id):
    """Get a single criminal's detailed profile by ID"""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        return jsonify({
            "criminal": {
                "id": criminal.id,
                "criminal_id": criminal.criminal_id,
                "status": criminal.status,
                "full_name": criminal.full_name,
                "aliases": criminal.aliases,
                "dob": criminal.dob,
                "sex": criminal.sex,
                "nationality": criminal.nationality,
                "ethnicity": criminal.ethnicity,
                "photo_filename": criminal.photo_filename,
                "appearance": criminal.appearance,
                "locations": criminal.locations,
                "summary": criminal.summary,
                "forensics": criminal.forensics,
                "evidence": criminal.evidence,
                "witness": criminal.witness,
                "created_at": criminal.created_at.isoformat(),
                "updated_at": criminal.updated_at.isoformat() if criminal.updated_at else None
            }
        }), 200
        
    except Exception as e:
        print(f"/api/criminals/{criminal_id} GET error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/<int:criminal_id>', methods=['DELETE'])
@authenticated
def delete_criminal(criminal_id):
    """Delete a criminal from the database"""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        db.delete(criminal)
        db.commit()
        
        return jsonify({"message": "Criminal deleted successfully"}), 200
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/criminals/{criminal_id} DELETE error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/search', methods=['POST'])
@authenticated
def search_criminals():
    """Search for criminals using a sketch"""
    import sys
    print("\n" + "="*60, flush=True)
    print("CRIMINAL SEARCH STARTED", flush=True)
    print("="*60, flush=True)
    sys.stdout.flush()
    
    db = None
    try:
        if 'sketch' not in request.files:
            return jsonify({"error": "Sketch file is required"}), 400
        
        sketch_file = request.files['sketch']
        threshold = float(request.form.get('threshold', 0.4))  # Distance threshold (lower = more similar)
        
        print(f"Sketch file received: {sketch_file.filename}")
        print(f"Distance threshold: {threshold}")
        
        # Save sketch to temporary file
        sketch_path = save_temp_file(sketch_file)
        print(f"Sketch saved to: {sketch_path}")
        
        try:
            # Get all criminals from database
            db = next(get_db())
            criminals = db.query(Criminal).all()
            
            matches = []
            
            # Compare sketch with each criminal
            for criminal in criminals:
                try:
                    # Save criminal photo bytes to a temporary file
                    criminal_photo_path = save_bytes_to_temp(
                        criminal.photo_data,
                        criminal.photo_filename or 'criminal.jpg'
                    )
                    
                    try:
                        # Use face comparison (no cache for search to ensure fresh results)
                        result = optimized_face_comparison(sketch_path, criminal_photo_path, use_cache=False)
                        
                        similarity_score = result.get('similarity', 0.0)
                        distance = result.get('distance', 1.0)
                        verified = result.get('verified', False)
                        
                        # Debug logging
                        print(f"Comparing with {criminal.full_name}: distance={distance:.4f}, similarity={similarity_score:.4f} ({similarity_score*100:.1f}%)")
                        
                        # Add to matches if similarity is reasonable (above 30%)
                        if similarity_score >= 0.30:
                            matches.append({
                                "criminal": {
                                    "id": criminal.id,
                                    "criminal_id": criminal.criminal_id,
                                    "status": criminal.status,
                                    "full_name": criminal.full_name,
                                    "aliases": criminal.aliases,
                                    "dob": criminal.dob,
                                    "sex": criminal.sex,
                                    "nationality": criminal.nationality,
                                    "ethnicity": criminal.ethnicity,
                                    "appearance": criminal.appearance,
                                    "locations": criminal.locations,
                                    "summary": criminal.summary,
                                    "forensics": criminal.forensics,
                                    "evidence": criminal.evidence,
                                    "witness": criminal.witness,
                                    "created_at": criminal.created_at.isoformat()
                                },
                                "similarity_score": float(similarity_score),
                                "distance": float(distance),
                                "verified": bool(verified),
                                "model_used": result.get('model_used', 'unknown'),
                                "confidence": result.get('confidence', 'low')
                            })
                    
                    finally:
                        # Clean up criminal photo temp file
                        try:
                            os.remove(criminal_photo_path)
                        except:
                            pass
                            
                except Exception as e:
                    print(f"Error comparing with criminal {criminal.id}: {e}")
                    continue
            
            # Sort by similarity score (highest first)
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return jsonify({
                "matches": matches,
                "total_matches": len(matches),
                "threshold_used": threshold
            })
            
        finally:
            # Clean up sketch temp file
            try:
                os.remove(sketch_path)
            except:
                pass
                
    except Exception as e:
        print("/api/criminals/search error:\n" + traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================================================
# FACE COMPARISON ENDPOINT
# ============================================================================

@app.route('/api/compare', methods=['POST'])
def compare_faces():
    """Compare two face images (sketch vs photo)"""
    try:
        if 'sketch' not in request.files or 'photo' not in request.files:
            return jsonify({"error": "Both 'sketch' and 'photo' files are required"}), 400

        sketch_file = request.files['sketch']
        photo_file = request.files['photo']

        sketch_path = save_temp_file(sketch_file)
        photo_path = save_temp_file(photo_file)

        try:
            # Use optimized face comparison
            result = optimized_face_comparison(sketch_path, photo_path, use_cache=True)
            
            return jsonify({
                "distance": result.get('distance', 1.0),
                "similarity": result.get('similarity', 0.0),
                "verified": result.get('verified', False),
                "model_used": result.get('model_used', 'unknown'),
                "confidence": result.get('confidence', 'low'),
                "metric_used": result.get('metric_used', 'unknown'),
                "processing_time": result.get('processing_time', 0),
                "from_cache": result.get('from_cache', False),
                "success": True
            })
        finally:
            # Cleanup temp files
            try:
                os.remove(sketch_path)
            except Exception:
                pass
            try:
                os.remove(photo_path)
            except Exception:
                pass
    except Exception as e:
        print("/api/compare error:\n" + traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all caches"""
    global RESULT_CACHE, EMBEDDING_CACHE
    result_count = len(RESULT_CACHE)
    embedding_count = len(EMBEDDING_CACHE)
    RESULT_CACHE.clear()
    EMBEDDING_CACHE.clear()
    return jsonify({
        "message": "Caches cleared successfully",
        "result_cache_cleared": result_count,
        "embedding_cache_cleared": embedding_count
    })


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    return jsonify({
        "result_cache_size": len(RESULT_CACHE),
        "embedding_cache_size": len(EMBEDDING_CACHE),
        "max_cache_size": CACHE_MAX_SIZE,
        "model_initialized": MODEL_INITIALIZED
    })


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "FaceFind Forensics API v2",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    # Disable output buffering for immediate console output
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    
    print("\n" + "=" * 60)
    print("FaceFind Forensics API v2 - Complete System")
    print("=" * 60)
    print("[OK] Role-Based Authentication (Admin OTP + Officer)")
    print("[OK] Criminal Database Management")
    print("[OK] Face Comparison with DeepFace")
    print("=" * 60)
    
    # Initialize DeepFace models on startup
    initialize_models()
    
    port = int(os.environ.get('PORT', '5001'))
    print(f"\n[OK] Server ready on http://localhost:{port}")
    print("=" * 60 + "\n")
    sys.stdout.flush()
    
    app.run(debug=True, host='0.0.0.0', port=port)
