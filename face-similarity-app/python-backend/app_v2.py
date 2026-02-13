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
            # Pre-load ArcFace model
            print("Loading ArcFace model...")
            DeepFace.represent(
                img_path=dummy_path,
                model_name='ArcFace',
                enforce_detection=False,
                align=True
            )
            print("[OK] ArcFace model loaded successfully")
            
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


# ============================================================================
# STEP 2: EDGE-BASED DEEP FEATURE PREPROCESSING (TEST/VALIDATION)
# ============================================================================
# NOTE: These functions are used by test endpoints (/api/test/*)
# The main production flow uses preprocess_for_cross_domain_matching() instead
# Keep these for testing and validation purposes
# ============================================================================

def preprocess_for_edge_based_matching(image_path: str, is_sketch: bool = False) -> str:
    """
    STEP 2: Edge-based preprocessing to reduce sketch-photo domain gap
    
    **USAGE:** Test endpoints only (/api/test/edge-preprocessing, /api/test/compare-edges)
    **PRODUCTION:** Main flow uses preprocess_for_cross_domain_matching() instead
    
    For PHOTOS: Extract edges to make them look more like sketches
    For SKETCHES: Minimal processing (just enhancement)
    
    This reduces the domain gap by converting both to edge-based representations.
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
    
    Returns:
        str: Path to preprocessed image file
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if not is_sketch:
            # PHOTO PREPROCESSING: Convert to sketch-like representation
            print("  [STEP 2] Photo → Edge extraction (sketch-like)")
            
            # 1. Reduce noise while preserving edges
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # 2. Extract edges using Canny
            edges = cv2.Canny(gray, 30, 100)
            
            # 3. Invert edges (white background, black lines like sketch)
            edges = cv2.bitwise_not(edges)
            
            # 4. Blend edges with original for structure preservation
            # 50% edges + 50% original
            result = cv2.addWeighted(gray, 0.5, edges, 0.5, 0)
            
        else:
            # SKETCH PREPROCESSING: Minimal enhancement
            print("  [STEP 2] Sketch → Minimal enhancement")
            
            # Just apply histogram equalization for consistent brightness
            result = cv2.equalizeHist(gray)
        
        # Convert back to BGR for DeepFace compatibility
        result_bgr = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        
        # Save with deterministic filename
        file_hash = hashlib.md5(image_path.encode()).hexdigest()[:8]
        mode = "sketch" if is_sketch else "photo"
        processed_path = os.path.join(tempfile.gettempdir(), f'edge_{mode}_{file_hash}.jpg')
        cv2.imwrite(processed_path, result_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        return processed_path
        
    except Exception as e:
        print(f"Edge preprocessing error: {e}")
        return image_path


def compare_with_edge_preprocessing(sketch_path: str, photo_path: str) -> dict:
    """
    STEP 2: Compare two images using edge-based preprocessing + ArcFace
    
    **USAGE:** Test endpoint only (/api/test/compare-edges)
    **PRODUCTION:** Main flow uses forensic_face_comparison() instead
    
    Applies edge preprocessing to both images, then uses ArcFace for comparison.
    
    Args:
        sketch_path: Path to sketch image
        photo_path: Path to photo image
    
    Returns:
        dict with similarity score and metadata
    """
    # Detect if images are sketches
    is_img1_sketch = is_sketch_image(sketch_path)
    is_img2_sketch = is_sketch_image(photo_path)
    
    print(f"  Image 1 is sketch: {is_img1_sketch}")
    print(f"  Image 2 is sketch: {is_img2_sketch}")
    
    processed_img1 = None
    processed_img2 = None
    
    try:
        # Apply edge-based preprocessing
        processed_img1 = preprocess_for_edge_based_matching(sketch_path, is_sketch=is_img1_sketch)
        processed_img2 = preprocess_for_edge_based_matching(photo_path, is_sketch=is_img2_sketch)
        
        # Run ArcFace on preprocessed images
        print("  [STEP 2] Running ArcFace on edge-preprocessed images...")
        result = DeepFace.verify(
            img1_path=processed_img1,
            img2_path=processed_img2,
            model_name='ArcFace',
            distance_metric='cosine',
            enforce_detection=False,
            align=True
        )
        
        distance = float(result['distance'])
        similarity = max(0.0, 1.0 - distance)
        
        return {
            'success': True,
            'distance': distance,
            'similarity': similarity,
            'threshold': float(result['threshold']),
            'model_verified': bool(result['verified']),
            'error': None
        }
        
    except Exception as e:
        print(f"Edge-based comparison error: {e}")
        return {
            'success': False,
            'distance': 1.0,
            'similarity': 0.0,
            'threshold': 0.4,
            'model_verified': False,
            'error': str(e)
        }
    
    finally:
        # Cleanup preprocessed images
        if processed_img1 and processed_img1 != sketch_path:
            try:
                os.remove(processed_img1)
            except:
                pass
        if processed_img2 and processed_img2 != photo_path:
            try:
                os.remove(processed_img2)
            except:
                pass


# ============================================================================
# PRODUCTION PREPROCESSING (USED BY MAIN FLOW)
# ============================================================================
# This function is used by forensic_face_comparison() which powers:
# - /api/compare endpoint
# - /api/criminals/search endpoint
# ============================================================================

def preprocess_for_cross_domain_matching(image_path: str, is_sketch: bool = False) -> str:
    """
    Cross-domain preprocessing for sketch-to-photo matching
    
    **USAGE:** Production endpoints (/api/compare, /api/criminals/search)
    **CALLED BY:** forensic_face_comparison()
    
    FORENSIC APPROACH:
    - Sketches and photos are different modalities (cross-domain problem)
    - Reduce texture/color dependence, focus on facial structure
    - Convert both to edge-based representations for fair comparison
    
    DETERMINISTIC: All operations use fixed parameters for consistent results
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        
        # Resize to standard size for consistent processing
        height, width = img.shape[:2]
        target_size = 512  # Standard size for processing
        
        if height != target_size or width != target_size:
            # Maintain aspect ratio, pad if needed
            scale = target_size / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            
            # Pad to square
            delta_w = target_size - new_width
            delta_h = target_size - new_height
            top, bottom = delta_h // 2, delta_h - (delta_h // 2)
            left, right = delta_w // 2, delta_w - (delta_w // 2)
            img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[255, 255, 255])
        
        # Convert to grayscale (removes color/texture dependence)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply histogram equalization for consistent brightness
        gray = cv2.equalizeHist(gray)
        
        # For photos: extract edges to match sketch representation
        if not is_sketch:
            # Apply Gaussian blur to reduce noise
            gray = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Extract edges using Canny (makes photo look more like sketch)
            edges = cv2.Canny(gray, 30, 100)
            
            # Invert edges (white background, black lines like sketch)
            edges = cv2.bitwise_not(edges)
            
            # Blend edges with original for structure preservation
            gray = cv2.addWeighted(gray, 0.6, edges, 0.4, 0)
        
        # For sketches: enhance edges
        else:
            # Apply bilateral filter to reduce noise while preserving edges
            gray = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Convert back to BGR for DeepFace compatibility
        processed = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        
        # Save with deterministic filename
        file_hash = hashlib.md5(image_path.encode()).hexdigest()[:8]
        mode = "sketch" if is_sketch else "photo"
        processed_path = os.path.join(tempfile.gettempdir(), f'forensic_{mode}_{file_hash}.jpg')
        cv2.imwrite(processed_path, processed, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        print(f"  Cross-domain preprocessing applied ({mode} mode)")
        return processed_path
        
    except Exception as e:
        print(f"Cross-domain preprocessing warning: {e}")
        return image_path


def is_sketch_image(image_path: str) -> bool:
    """
    Detect if an image is a sketch based on characteristics:
    - Low color saturation (mostly grayscale)
    - High edge density
    
    DETERMINISTIC: Uses fixed thresholds for consistent classification
    NOTE: This is for logging/debugging only - does NOT affect preprocessing
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to HSV to check saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        avg_saturation = float(np.mean(saturation))
        
        # Sketches have very low saturation (< 30)
        # Photos have higher saturation (> 50)
        is_low_saturation = avg_saturation < 30
        
        # Check edge density (sketches have more edges)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0)) / float(edges.size)
        
        # Sketches have higher edge density (> 0.05)
        is_high_edges = edge_density > 0.05
        
        # Debug output
        print(f"  Sketch detection: saturation={avg_saturation:.2f}, edge_density={edge_density:.4f}")
        print(f"  Classification: low_sat={is_low_saturation}, high_edges={is_high_edges}")
        
        # Both conditions must be met
        result = is_low_saturation and is_high_edges
        print(f"  Final: is_sketch={result}")
        
        return result
        
    except Exception as e:
        print(f"Sketch detection warning: {e}")
        return False


# ============================================================================
# PRODUCTION FACE COMPARISON (MAIN FLOW)
# ============================================================================
# This function powers the main production endpoints:
# - /api/compare (direct comparison)
# - /api/criminals/search (database search)
# ============================================================================

def forensic_face_comparison(sketch_path: str, photo_path: str, use_cache: bool = True) -> dict:
    """
    Forensic-grade face comparison for sketch-to-photo matching
    
    **USAGE:** Production endpoints (/api/compare, /api/criminals/search)
    **PREPROCESSING:** Uses preprocess_for_cross_domain_matching()
    
    CROSS-DOMAIN APPROACH:
    - Treats sketch and photo as different modalities
    - Applies domain-bridging preprocessing
    - Provides realistic confidence levels
    - Returns ranked results, not binary decisions
    
    DETERMINISTIC: All operations use fixed parameters for consistent results
    """
    global RESULT_CACHE
    
    # Ensure models are initialized
    initialize_models()
    
    start_time = time.time()
    print(f"\n{'='*60}")
    print("FORENSIC FACE COMPARISON")
    print(f"{'='*60}")
    print(f"  Query Image: {os.path.basename(sketch_path)}")
    print(f"  Reference Image: {os.path.basename(photo_path)}")
    
    # Detect if images are sketches
    is_img1_sketch = is_sketch_image(sketch_path)
    is_img2_sketch = is_sketch_image(photo_path)
    
    print(f"  Query is sketch: {is_img1_sketch}")
    print(f"  Reference is sketch: {is_img2_sketch}")
    
    # Determine comparison type
    is_cross_domain = is_img1_sketch != is_img2_sketch
    comparison_type = "cross-domain (sketch-to-photo)" if is_cross_domain else "same-domain"
    print(f"  Comparison type: {comparison_type}")
    
    # Check result cache
    cache_key = None
    if use_cache:
        hash1 = get_file_hash(sketch_path)
        hash2 = get_file_hash(photo_path)
        if hash1 and hash2:
            cache_key = f"{hash1}_{hash2}_{is_img1_sketch}_{is_img2_sketch}"
            if cache_key in RESULT_CACHE:
                cached_result = RESULT_CACHE[cache_key].copy()
                cached_result['from_cache'] = True
                cached_result['processing_time'] = round(time.time() - start_time, 3)
                print(f"[CACHE] Result retrieved from cache")
                print(f"{'='*60}\n")
                return cached_result
    
    processed_img1 = None
    processed_img2 = None
    
    try:
        # Apply cross-domain preprocessing
        print(f"[PREPROCESSING] Applying cross-domain preprocessing...")
        processed_img1 = preprocess_for_cross_domain_matching(sketch_path, is_sketch=is_img1_sketch)
        processed_img2 = preprocess_for_cross_domain_matching(photo_path, is_sketch=is_img2_sketch)
        
        # Use DeepFace.verify with ArcFace model
        print(f"[MATCHING] Running ArcFace model...")
        result = DeepFace.verify(
            img1_path=processed_img1,
            img2_path=processed_img2,
            model_name='ArcFace',
            distance_metric='cosine',
            enforce_detection=False,
            align=True
        )
        
        # Extract results
        distance = float(result['distance'])
        model_threshold = float(result['threshold'])
        
        # Calculate similarity score (0-1 range)
        similarity = max(0.0, min(1.0, 1.0 - distance))
        
        # Forensic confidence assessment
        # Cross-domain matching has inherently lower confidence
        if is_cross_domain:
            # Sketch-to-photo: realistic confidence levels
            if distance <= 0.30:
                confidence_level = 'possible_match'
                confidence_score = 75.0
                match_quality = 'Strong candidate - requires verification'
            elif distance <= 0.45:
                confidence_level = 'weak_match'
                confidence_score = 55.0
                match_quality = 'Weak candidate - low confidence'
            elif distance <= 0.60:
                confidence_level = 'uncertain'
                confidence_score = 35.0
                match_quality = 'Uncertain - insufficient similarity'
            else:
                confidence_level = 'unlikely'
                confidence_score = 15.0
                match_quality = 'Unlikely match'
        else:
            # Same-domain (photo-to-photo): higher confidence possible
            if distance <= model_threshold * 0.5:
                confidence_level = 'high'
                confidence_score = 95.0
                match_quality = 'Strong match'
            elif distance <= model_threshold * 0.7:
                confidence_level = 'medium'
                confidence_score = 80.0
                match_quality = 'Good match'
            elif distance <= model_threshold:
                confidence_level = 'low'
                confidence_score = 60.0
                match_quality = 'Weak match'
            else:
                confidence_level = 'very_low'
                confidence_score = 30.0
                match_quality = 'Poor match'
        
        # Model's binary decision (for reference only)
        model_verified = bool(result['verified'])
        
        elapsed_time = time.time() - start_time
        
        print(f"[RESULTS]")
        print(f"  Distance: {distance:.4f}")
        print(f"  Similarity: {similarity:.4f} ({similarity*100:.1f}%)")
        print(f"  Confidence: {confidence_level} ({confidence_score:.1f}%)")
        print(f"  Quality: {match_quality}")
        print(f"  Model threshold: {model_threshold:.4f}")
        print(f"  Model decision: {'Match' if model_verified else 'No match'}")
        print(f"  Processing time: {elapsed_time:.3f}s")
        print(f"{'='*60}\n")
        
        result_dict = {
            'distance': float(distance),
            'similarity': float(similarity),
            'confidence_level': confidence_level,
            'confidence_score': float(confidence_score),
            'match_quality': match_quality,
            'is_cross_domain': bool(is_cross_domain),
            'comparison_type': comparison_type,
            'model_verified': bool(model_verified),
            'model_threshold': float(model_threshold),
            'model_used': 'ArcFace',
            'metric_used': 'cosine',
            'processing_time': round(elapsed_time, 3),
            'from_cache': False,
            'forensic_note': 'Cross-domain matching has inherent limitations. Results should be used for investigation leads, not absolute identification.' if is_cross_domain else 'Same-domain comparison with higher reliability.'
        }
        
        # Cache the result
        if use_cache and cache_key:
            if len(RESULT_CACHE) >= CACHE_MAX_SIZE:
                RESULT_CACHE.pop(next(iter(RESULT_CACHE)))
            RESULT_CACHE[cache_key] = result_dict.copy()
        
        return result_dict
        
    except Exception as e:
        print(f"[ERROR] Comparison failed: {e}")
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        elapsed_time = time.time() - start_time
        return {
            'distance': 1.0,
            'similarity': 0.0,
            'confidence_level': 'error',
            'confidence_score': 0.0,
            'match_quality': 'Comparison failed',
            'is_cross_domain': False,
            'comparison_type': 'error',
            'model_verified': False,
            'model_threshold': 0.4,
            'model_used': 'failed',
            'metric_used': 'none',
            'processing_time': round(elapsed_time, 3),
            'error': str(e),
            'from_cache': False,
            'forensic_note': 'Comparison failed due to technical error.'
        }
    
    finally:
        # Cleanup processed temporary images
        if processed_img1 and processed_img1 != sketch_path:
            try:
                os.remove(processed_img1)
            except:
                pass
        if processed_img2 and processed_img2 != photo_path:
            try:
                os.remove(processed_img2)
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
                        # Use forensic face comparison (no cache for search to ensure fresh results)
                        result = forensic_face_comparison(sketch_path, criminal_photo_path, use_cache=False)
                        
                        similarity_score = result.get('similarity', 0.0)
                        distance = result.get('distance', 1.0)
                        confidence_level = result.get('confidence_level', 'uncertain')
                        confidence_score = result.get('confidence_score', 0.0)
                        match_quality = result.get('match_quality', 'Unknown')
                        
                        # Debug logging
                        print(f"  {criminal.full_name}: distance={distance:.4f}, similarity={similarity_score:.2f}, confidence={confidence_level}")
                        
                        # Add all matches for ranking
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
                                "confidence_level": confidence_level,
                                "confidence_score": float(confidence_score),
                                "match_quality": match_quality,
                                "model_used": result.get('model_used', 'ArcFace'),
                                "is_cross_domain": result.get('is_cross_domain', True)
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
            
            # Return top 3 matches as ranked candidates
            top_matches = matches[:3]
            
            # Add rank to each match
            for idx, match in enumerate(top_matches, 1):
                match['rank'] = idx
            
            print(f"\n[OK] Search completed. Found {len(matches)} total matches, returning top {len(top_matches)}")
            for match in top_matches:
                print(f"  Rank {match['rank']}: {match['criminal']['full_name']} - Similarity: {match['similarity_score']*100:.1f}%, Confidence: {match['confidence_level']}")
            
            return jsonify({
                "matches": top_matches,
                "total_matches": len(matches),
                "showing_top": min(3, len(matches)),
                "threshold_used": threshold,
                "forensic_note": "These are POSSIBLE MATCHES ranked by similarity. Cross-domain sketch-to-photo matching has inherent limitations. Results should be used as investigation leads, not absolute identification. Manual verification is required.",
                "interpretation_guide": {
                    "possible_match": "Strong candidate - worth investigating further",
                    "weak_match": "Weak candidate - low confidence",
                    "uncertain": "Insufficient similarity for reliable matching",
                    "unlikely": "Unlikely to be the same person"
                }
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
    """Compare two face images (sketch vs photo) - Forensic comparison"""
    try:
        if 'sketch' not in request.files or 'photo' not in request.files:
            return jsonify({"error": "Both 'sketch' and 'photo' files are required"}), 400

        sketch_file = request.files['sketch']
        photo_file = request.files['photo']

        sketch_path = save_temp_file(sketch_file)
        photo_path = save_temp_file(photo_file)

        try:
            # Use forensic face comparison
            result = forensic_face_comparison(sketch_path, photo_path, use_cache=True)
            
            return jsonify({
                "distance": result.get('distance', 1.0),
                "similarity": result.get('similarity', 0.0),
                "confidence_level": result.get('confidence_level', 'uncertain'),
                "confidence_score": result.get('confidence_score', 0.0),
                "match_quality": result.get('match_quality', 'Unknown'),
                "is_cross_domain": result.get('is_cross_domain', False),
                "comparison_type": result.get('comparison_type', 'unknown'),
                "model_verified": result.get('model_verified', False),
                "model_threshold": result.get('model_threshold', 0.4),
                "model_used": result.get('model_used', 'ArcFace'),
                "metric_used": result.get('metric_used', 'cosine'),
                "processing_time": result.get('processing_time', 0),
                "from_cache": result.get('from_cache', False),
                "forensic_note": result.get('forensic_note', ''),
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


# ============================================================================
# TEST ENDPOINTS FOR STEP 2
# ============================================================================

@app.route('/api/test/edge-preprocessing', methods=['POST'])
def test_edge_preprocessing():
    """
    TEST ENDPOINT: Test Step 2 - Edge-based preprocessing
    
    Upload an image to see the edge-preprocessed result
    Returns the preprocessed image
    """
    try:
        if 'image' not in request.files:
            return jsonify({"error": "Image file is required"}), 400
        
        image_file = request.files['image']
        is_sketch = request.form.get('is_sketch', 'false').lower() == 'true'
        
        image_path = save_temp_file(image_file)
        
        try:
            print(f"\n[TEST STEP 2] Edge preprocessing: {image_file.filename} (is_sketch={is_sketch})")
            
            # Apply edge preprocessing
            processed_path = preprocess_for_edge_based_matching(image_path, is_sketch=is_sketch)
            
            # Read processed image
            with open(processed_path, 'rb') as f:
                processed_data = f.read()
            
            # Cleanup
            if processed_path != image_path:
                try:
                    os.remove(processed_path)
                except:
                    pass
            
            # Return processed image
            return send_file(
                io.BytesIO(processed_data),
                mimetype='image/jpeg',
                as_attachment=False
            )
            
        finally:
            try:
                os.remove(image_path)
            except:
                pass
                
    except Exception as e:
        print(f"/api/test/edge-preprocessing error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/test/compare-edges', methods=['POST'])
def test_compare_edges():
    """
    TEST ENDPOINT: Test Step 2 - Compare using edge-based preprocessing
    """
    try:
        if 'image1' not in request.files or 'image2' not in request.files:
            return jsonify({"error": "Both image1 and image2 are required"}), 400
        
        image1_file = request.files['image1']
        image2_file = request.files['image2']
        
        image1_path = save_temp_file(image1_file)
        image2_path = save_temp_file(image2_file)
        
        try:
            print(f"\n[TEST STEP 2] Comparing with edge preprocessing:")
            print(f"  Image 1: {image1_file.filename}")
            print(f"  Image 2: {image2_file.filename}")
            
            # Compare using edge preprocessing
            result = compare_with_edge_preprocessing(image1_path, image2_path)
            
            if result['success']:
                print(f"  Deep similarity (edge-based): {result['similarity']:.3f}")
                
                return jsonify({
                    "success": True,
                    "deep_similarity": result['similarity'],
                    "distance": result['distance'],
                    "threshold": result['threshold'],
                    "model_verified": result['model_verified'],
                    "message": f"Deep similarity (edge-based): {result['similarity']:.1%}"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result['error']
                }), 400
            
        finally:
            try:
                os.remove(image1_path)
                os.remove(image2_path)
            except:
                pass
                
    except Exception as e:
        print(f"/api/test/compare-edges error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all caches"""
    global RESULT_CACHE
    result_count = len(RESULT_CACHE)
    RESULT_CACHE.clear()
    return jsonify({
        "message": "Caches cleared successfully",
        "result_cache_cleared": result_count
    })


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Get cache statistics"""
    return jsonify({
        "result_cache_size": len(RESULT_CACHE),
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

