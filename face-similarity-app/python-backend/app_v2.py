"""
Enhanced Flask Application with Role-Based Authentication + Face Comparison
Admin (with OTP) and Officer roles + DeepFace Integration
"""

import os
import json
import traceback
import io
import cv2
import numpy as np
import hashlib
import time
import uuid
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
from datetime import datetime, timezone

# Import utility functions from modular structure
from utils.file_utils import (
    generate_temp_filepath,
    cleanup_temp_file,
    get_file_hash,
    save_temp_file,
    save_bytes_to_temp,
    set_temp_uploads_dir
)
from utils.similarity_utils import cosine_similarity
from utils.cache_utils import (
    RESULT_CACHE,
    CACHE_MAX_SIZE,
    get_cached_result,
    set_cached_result,
    clear_cache as clear_result_cache,
    get_cache_stats
)

# Import preprocessing functions from modular structure
from preprocessing.sketch_photo_preprocess import (
    is_sketch_image,
    preprocess_for_edge_based_matching,
    preprocess_for_cross_domain_matching,
    preprocess_with_adaptive_canny
)

# Import embedding service functions from modular structure
from services.s3_service import upload_criminal_photo, delete_criminal_photo, get_signed_url
from services.embedding_service import (
    initialize_models,
    is_models_initialized,
    extract_embedding,
    extract_dual_embeddings,
    extract_embedding_with_tta,
    generate_tta_augmentations
)

# Import face comparison service functions from modular structure
from services.face_comparison_service import (
    forensic_face_comparison,
    extract_facial_regions,
    extract_region_embeddings,
    compute_multi_region_similarity,
    compute_geometric_similarity,
    compute_geometric_similarity_from_aligned
)

app = Flask(__name__)
CORS(app)

# ============================================================================
# TEMP UPLOADS FOLDER SETUP
# ============================================================================

# Create dedicated temp_uploads folder in project directory
TEMP_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'temp_uploads')
set_temp_uploads_dir(TEMP_UPLOADS_DIR)

# Create database tables
create_tables()

# ============================================================================
# GLOBAL VARIABLES FOR FACE COMPARISON OPTIMIZATION
# ============================================================================

# Import MODEL_INITIALIZED from embedding service
from services.embedding_service import MODEL_INITIALIZED

# Import FAISS service functions and variables
from services.faiss_service import (
    get_embedding_cache,
    get_embedding_version,
    set_cached_embedding,
    get_cached_embedding,
    clear_embedding_cache,
    get_cache_size,
    build_faiss_index,
    is_faiss_index_ready,
    get_faiss_index_stats,
    search_top_k_candidates,
    EMBEDDING_CACHE,
    EMBEDDING_VERSION,
    FAISS_INDEX_DIRTY
)


# ============================================================================
# FACE COMPARISON HELPER FUNCTIONS
# ============================================================================
# NOTE: Face comparison functions have been moved to:
# - services/face_comparison_service.py
# Functions moved:
# - extract_facial_regions()
# - extract_region_embeddings()
# - compute_multi_region_similarity()
# - compute_geometric_similarity()
# - compute_geometric_similarity_from_aligned()
# - forensic_face_comparison()
# ============================================================================


def precompute_database_embeddings():
    """
    Precompute and cache dual embeddings (ArcFace + Facenet) for all criminals in database
    Called at startup
    """
    print("\n" + "="*60)
    print("PRECOMPUTING DATABASE DUAL EMBEDDINGS (ArcFace + Facenet)")
    print("="*60)
    
    db = next(get_db())
    try:
        criminals = db.query(Criminal).all()
        print(f"Found {len(criminals)} criminals in database")
        
        updated_count = 0
        cached_count = 0
        failed_count = 0
        
        for criminal in criminals:
            try:
                # Check if embedding already exists and is current version
                if criminal.face_embedding and criminal.embedding_version == EMBEDDING_VERSION:
                    # Load from database (stored as dict with arcface and facenet keys)
                    embedding_data = criminal.face_embedding
                    if isinstance(embedding_data, dict) and 'arcface' in embedding_data and 'facenet' in embedding_data:
                        set_cached_embedding(
                            criminal.criminal_id,
                            np.array(embedding_data['arcface']),
                            np.array(embedding_data['facenet'])
                        )
                        cached_count += 1
                        print(f"  [OK] Loaded cached dual embeddings for {criminal.criminal_id}")
                    else:
                        # Old format, need to recompute
                        print(f"  [INFO] Old embedding format for {criminal.criminal_id}, recomputing...")
                        raise ValueError("Old embedding format")
                else:
                    # Compute new dual embeddings
                    print(f"  Computing dual embeddings for {criminal.criminal_id}...")
                    
                    # Validate photo key exists
                    if not criminal.photo_key:
                        print(f"  [ERROR] No photo_key for {criminal.criminal_id}")
                        failed_count += 1
                        continue
                    
                    # Download photo from S3 to temp file
                    temp_path = generate_temp_filepath(original_filename=criminal.photo_filename or 'criminal.jpg', prefix='criminal')
                    try:
                        signed_url = get_signed_url(criminal.photo_key)
                        if not signed_url:
                            print(f"  [ERROR] Could not generate signed URL for {criminal.criminal_id}")
                            failed_count += 1
                            continue
                        import urllib.request
                        urllib.request.urlretrieve(signed_url, temp_path)
                        
                        # Validate temp file was created
                        if not os.path.exists(temp_path):
                            print(f"  [ERROR] Failed to create temp file for {criminal.criminal_id}")
                            failed_count += 1
                            continue
                        
                        # Validate file can be read by cv2
                        test_img = cv2.imread(temp_path)
                        if test_img is None:
                            print(f"  [ERROR] cv2.imread() failed - photo data is corrupted for {criminal.criminal_id}")
                            failed_count += 1
                            cleanup_temp_file(temp_path)
                            continue
                        
                        # Extract dual embeddings
                        embeddings = extract_dual_embeddings(temp_path, is_sketch=False)
                        
                        if embeddings and embeddings['success']:
                            # Store in cache using FAISS service
                            set_cached_embedding(
                                criminal.criminal_id,
                                embeddings['arcface'],
                                embeddings['facenet']
                            )
                            
                            # Update database (store as dict)
                            criminal.face_embedding = {
                                'arcface': embeddings['arcface'].tolist(),
                                'facenet': embeddings['facenet'].tolist()
                            }
                            criminal.embedding_version = EMBEDDING_VERSION
                            db.commit()
                            
                            updated_count += 1
                            print(f"  [OK] Computed and stored dual embeddings for {criminal.criminal_id}")
                        else:
                            print(f"  [ERROR] Failed to compute dual embeddings for {criminal.criminal_id}")
                            failed_count += 1
                    
                    finally:
                        # Cleanup temp file
                        cleanup_temp_file(temp_path)
                        
            except Exception as e:
                print(f"  [ERROR] Error processing {criminal.criminal_id}: {e}")
                failed_count += 1
                continue
        
        print(f"\n[SUMMARY]")
        print(f"  Cached dual embeddings: {cached_count}")
        print(f"  Newly computed: {updated_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total in cache: {get_cache_size()}")
        print("="*60 + "\n")
        
        # Build FAISS index after all embeddings are cached
        build_faiss_index()
        
    except Exception as e:
        print(f"[ERROR] Precomputation failed: {e}")
        traceback.print_exc()
    finally:
        db.close()


# ============================================================================
# STEP 2: EDGE-BASED DEEP FEATURE PREPROCESSING (TEST/VALIDATION)
# ============================================================================
# NOTE: These functions are used by test endpoints (/api/test/*)
# The main production flow uses preprocess_for_cross_domain_matching() instead
# Keep these for testing and validation purposes
# ============================================================================

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
# NOTE: All preprocessing functions have been moved to:
# - preprocessing/sketch_photo_preprocess.py
# - preprocessing/image_preprocessing.py
# ============================================================================


# ============================================================================
# PRODUCTION FACE COMPARISON (MAIN FLOW)
# ============================================================================
# NOTE: Face comparison function has been moved to:
# - services/face_comparison_service.py
# Function moved:
# - forensic_face_comparison()
# 
# This function powers the main production endpoints:
# - /api/compare (direct comparison)
# - /api/criminals/search (database search)
# ============================================================================


# ============================================================================
# DATABASE EMBEDDING PRECOMPUTATION
# ============================================================================


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

        print("[LOGIN] Admin login-step1 HIT", flush=True)

        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400

        email = data.get('email').lower().strip()
        password = data.get('password')

        print(f"[LOGIN] Admin email: {email}", flush=True)
        
        db = next(get_db())
        
        # Find admin user
        user = db.query(User).filter(User.email == email, User.role == 'admin').first()
        
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not verify_password(password, user.password_hash):
            print(f"[LOGIN] Admin password mismatch for: {email}", flush=True)
            return jsonify({"error": "Invalid email or password"}), 401

        print(f"[LOGIN] Admin password verified for: {email}", flush=True)
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
        user.last_login = datetime.now(timezone.utc)
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

        print("[LOGIN] Officer login HIT", flush=True)

        if not data.get('email') or not data.get('password'):
            return jsonify({"error": "Email and password are required"}), 400

        email = data.get('email').lower().strip()
        password = data.get('password')

        print(f"[LOGIN] Officer email: {email}", flush=True)
        
        db = next(get_db())
        
        # Find officer user
        user = db.query(User).filter(User.email == email, User.role == 'officer').first()
        
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not verify_password(password, user.password_hash):
            print(f"[LOGIN] Officer password mismatch for: {email}", flush=True)
            return jsonify({"error": "Invalid email or password"}), 401

        print(f"[LOGIN] Officer password verified for: {email}", flush=True)
        user.last_login = datetime.now(timezone.utc)
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
        db_user.is_temp_password = False
        
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
            is_temp_password=True
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
        officer.is_temp_password = True
        
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
                "photo_key": criminal.photo_key,
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
        photo_filename = photo_file.filename or "photo.jpg"

        # Upload photo to S3 (private bucket) — store object key, not URL
        photo_key = None
        criminal_id_str = profile_data.get('criminal_id')
        try:
            photo_key = upload_criminal_photo(criminal_id_str, photo_data, photo_filename)
        except Exception as upload_err:
            print(f"  [WARNING] S3 upload failed: {upload_err} — continuing without photo_key")

        # Create new criminal record
        db = next(get_db())
        new_criminal = Criminal(
            criminal_id=criminal_id_str,
            status=profile_data.get('status'),
            full_name=profile_data.get('full_name'),
            aliases=profile_data.get('aliases'),
            dob=profile_data.get('dob'),
            sex=profile_data.get('sex'),
            nationality=profile_data.get('nationality'),
            ethnicity=profile_data.get('ethnicity'),
            photo_key=photo_key,
            photo_filename=photo_filename,
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
        
        # ================================================================
        # AUTOMATIC FAISS INDEX UPDATE
        # ================================================================
        # Extract embeddings and rebuild FAISS index so the new criminal
        # becomes searchable immediately without server restart
        
        try:
            print(f"\n[EMBEDDING EXTRACTION] Processing new criminal: {new_criminal.full_name}")
            
            # Save photo to temporary file for embedding extraction
            temp_photo_path = save_bytes_to_temp(photo_data, photo_file.filename or 'criminal.jpg')
            
            try:
                # Extract dual embeddings (ArcFace + Facenet)
                embeddings = extract_dual_embeddings(
                    image_path=temp_photo_path,
                    is_sketch=False,
                    use_adaptive_canny=False
                )
                
                # Store embeddings in cache
                set_cached_embedding(
                    criminal_id=new_criminal.criminal_id,
                    arcface_embedding=embeddings['arcface'],
                    facenet_embedding=embeddings['facenet']
                )
                
                print(f"  [OK] Embeddings cached for criminal_id: {new_criminal.criminal_id}")
                
                # Rebuild FAISS index (automatically marks as dirty and rebuilds)
                print(f"  [FAISS] Rebuilding index to include new criminal...")
                build_faiss_index()
                print(f"  [OK] FAISS index rebuilt - new criminal is now searchable")
                
            finally:
                # Clean up temporary file
                cleanup_temp_file(temp_photo_path)
                
        except Exception as e:
            # Log error but don't fail the request
            # Criminal is saved, but won't be searchable until manual index rebuild
            print(f"  [WARNING] Failed to update FAISS index: {e}")
            print(f"  [WARNING] Criminal saved but not immediately searchable")
            traceback.print_exc()
        
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
    """Generate a signed URL for the criminal's S3 photo and redirect to it."""
    from flask import redirect
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()
        
        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404
        
        if not criminal.photo_key:
            return jsonify({"error": "No photo available"}), 404

        signed_url = get_signed_url(criminal.photo_key)
        if not signed_url:
            return jsonify({"error": "Failed to generate photo URL"}), 500

        return redirect(signed_url)
        
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
                "photo_key": criminal.photo_key,
                "photo_url": get_signed_url(criminal.photo_key) if criminal.photo_key else None,
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
    """Delete a criminal from the database and remove their photo from S3."""
    db = None
    try:
        db = next(get_db())
        criminal = db.query(Criminal).filter(Criminal.id == criminal_id).first()

        if not criminal:
            return jsonify({"error": "Criminal not found"}), 404

        # --- S3 cleanup (before DB delete so we still have the key) ---
        photo_key = criminal.photo_key
        if photo_key:
            deleted = delete_criminal_photo(criminal.criminal_id, photo_key)
            if deleted:
                print(f"[S3] Deleted photo for {criminal.criminal_id}: {photo_key}", flush=True)
            else:
                # Log but do not abort — DB record must still be removed
                print(f"[S3] WARNING: Could not delete photo for {criminal.criminal_id}: {photo_key}", flush=True)
        else:
            print(f"[S3] No photo_key for {criminal.criminal_id}, skipping S3 delete", flush=True)

        # --- DB delete ---
        db.delete(criminal)
        db.commit()

        return jsonify({"message": "Criminal deleted successfully"}), 200

    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/criminals/{criminal_id} DELETE error: {e}", flush=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/criminals/search', methods=['POST'])
@authenticated
def search_criminals():
    """Search for criminals using a sketch - OPTIMIZED with precomputed embeddings"""
    import sys
    print("\n" + "="*60, flush=True)
    print("CRIMINAL SEARCH STARTED (OPTIMIZED)", flush=True)
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
            # Extract DUAL embeddings for query sketch ONCE
            print(f"\n[QUERY DUAL EMBEDDING] Extracting dual embeddings (ArcFace + Facenet) for sketch...")
            query_embeddings = extract_dual_embeddings(sketch_path, is_sketch=True)
            
            if query_embeddings is None or not query_embeddings['success']:
                return jsonify({"error": "Failed to extract dual embeddings from sketch"}), 400
            
            print(f"  [OK] Query dual embeddings extracted:")
            if query_embeddings['arcface'] is not None:
                print(f"    ArcFace: length={len(query_embeddings['arcface'])}, normalized")
            else:
                print(f"    ArcFace: unavailable (model not loaded)")
            if query_embeddings['facenet'] is not None:
                print(f"    Facenet: length={len(query_embeddings['facenet'])}, normalized")
            else:
                print(f"    Facenet: unavailable (model not loaded)")
            
            # Get all criminals from database
            db = next(get_db())
            criminals = db.query(Criminal).all()
            
            # ================================================================
            # STAGE 1: FAST RETRIEVAL - FAISS-based Embedding Similarity
            # ================================================================
            print(f"\n[STAGE 1: FAST RETRIEVAL]")
            
            # Select Top-K candidates for re-ranking (default K=5, max 50 for FAISS)
            top_k = int(request.form.get('top_k', 5))
            top_k = min(max(top_k, 1), 50)  # Clamp between 1 and 50
            
            # Get all criminal IDs from database
            criminal_ids = [c.criminal_id for c in criminals]
            
            # Use FAISS service for search (automatically falls back to linear search if FAISS not available)
            # Use whichever embedding is available; FAISS service handles None gracefully
            query_arcface = query_embeddings['arcface']
            query_facenet = query_embeddings['facenet']
            # If one model is missing, mirror the other so fusion still works
            if query_arcface is None and query_facenet is not None:
                query_arcface = query_facenet
                print("  [WARN] ArcFace unavailable - using Facenet embedding for FAISS arcface slot")
            elif query_facenet is None and query_arcface is not None:
                query_facenet = query_arcface
                print("  [WARN] Facenet unavailable - using ArcFace embedding for FAISS facenet slot")

            search_results, use_faiss = search_top_k_candidates(
                query_arcface,
                query_facenet,
                criminal_ids,
                top_k
            )
            
            # Convert search results to stage1_candidates format
            criminal_dict = {c.criminal_id: c for c in criminals}  # Quick lookup
            top_k_candidates = []
            
            for result in search_results:
                criminal_id = result['criminal_id']
                if criminal_id in criminal_dict:
                    top_k_candidates.append({
                        'criminal': criminal_dict[criminal_id],
                        'embedding_fusion': result['embedding_fusion'],
                        'arcface_similarity': result['arcface_similarity'],
                        'facenet_similarity': result['facenet_similarity']
                    })
            
            # ================================================================
            # STAGE 2: RE-RANKING - Detailed Comparison
            # ================================================================
            print(f"\n[STAGE 2: RE-RANKING]")
            print(f"  Performing detailed comparison on Top-{len(top_k_candidates)} candidates...")
            
            matches = []
            
            for candidate in top_k_candidates:
                try:
                    criminal = candidate['criminal']
                    embedding_fusion = candidate['embedding_fusion']
                    arcface_similarity = candidate['arcface_similarity']
                    facenet_similarity = candidate['facenet_similarity']
                    
                    # Download criminal photo to temp file via S3 signed URL
                    import urllib.request as _urlreq
                    criminal_photo_path = generate_temp_filepath(
                        original_filename=criminal.photo_filename or 'criminal.jpg', prefix='crim'
                    )
                    _signed = get_signed_url(criminal.photo_key)
                    if not _signed:
                        print(f"    [WARNING] Could not get signed URL for {criminal.full_name}, skipping")
                        continue
                    _urlreq.urlretrieve(_signed, criminal_photo_path)
                    
                    try:
                        # Extract aligned face from criminal photo
                        from deepface.modules import detection
                        
                        criminal_face_objs = detection.extract_faces(
                            img_path=criminal_photo_path,
                            detector_backend='opencv',
                            enforce_detection=True,
                            align=True,
                            grayscale=False
                        )
                        
                        if criminal_face_objs and len(criminal_face_objs) > 0:
                            criminal_aligned_face = criminal_face_objs[0]['face']
                            
                            # Convert to uint8 if needed
                            if criminal_aligned_face.dtype == np.float32 or criminal_aligned_face.dtype == np.float64:
                                criminal_aligned_face = (criminal_aligned_face * 255).astype(np.uint8)
                            
                            # Compute geometric similarity using aligned faces
                            geometric_similarity = compute_geometric_similarity_from_aligned(
                                query_embeddings['aligned_face'],
                                criminal_aligned_face
                            )
                            
                            # Compute multi-region similarity for enhanced matching
                            try:
                                query_regions = extract_region_embeddings(query_embeddings['aligned_face'], is_sketch=True)
                                criminal_regions = extract_region_embeddings(criminal_aligned_face, is_sketch=False)
                                
                                if query_regions['success'] and criminal_regions['success']:
                                    region_results = compute_multi_region_similarity(query_regions, criminal_regions)
                                    region_similarity = region_results['combined_similarity']
                                else:
                                    region_similarity = embedding_fusion  # Fallback to combined embedding
                            except Exception as e:
                                print(f"    [WARNING] Region similarity failed for {criminal.full_name}: {e}")
                                region_similarity = embedding_fusion  # Fallback to combined embedding
                        else:
                            # Fallback if face detection fails
                            geometric_similarity = embedding_fusion  # Fallback to combined embedding
                            region_similarity = embedding_fusion  # Fallback to combined embedding
                            
                    finally:
                        cleanup_temp_file(criminal_photo_path)
                    
                    # Final re-ranking score: 60% embedding + 25% geometric + 15% region
                    final_score = 0.60 * embedding_fusion + 0.25 * geometric_similarity + 0.15 * region_similarity
                    
                    print(f"  {criminal.full_name}:")
                    print(f"    Embedding: {embedding_fusion:.4f}, Geometric: {geometric_similarity:.4f}, Region: {region_similarity:.4f}")
                    print(f"    Final Score: {final_score:.4f}")
                    
                    # Add to matches with full scoring breakdown
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
                        "similarity_score": float(final_score),  # Final re-ranked score
                        "embedding_fusion": float(embedding_fusion),
                        "arcface_similarity": float(arcface_similarity) if arcface_similarity is not None else None,
                        "facenet_similarity": float(facenet_similarity) if facenet_similarity is not None else None,
                        "geometric_similarity": float(geometric_similarity),
                        "region_similarity": float(region_similarity),
                        "distance": float(1.0 - final_score),
                        "model_used": 'Two-Stage Re-Ranking (ArcFace + Facenet + Geometric + Multi-Region)',
                        "metric_used": 'Stage 1: embedding fusion | Stage 2: 60% embedding + 25% geometric + 15% region',
                        "is_cross_domain": True,
                        "stage1_rank": top_k_candidates.index(candidate) + 1,
                        "reranking_applied": True
                    })
                        
                except Exception as e:
                    print(f"  [ERROR] Error re-ranking criminal {candidate['criminal'].id}: {e}")
                    traceback.print_exc()
                    continue
            
            # Sort by final re-ranked score (highest first)
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            print(f"\n[RE-RANKING COMPLETE]")
            print(f"  Final ranking:")
            for idx, match in enumerate(matches, 1):
                print(f"    Rank {idx}: {match['criminal']['full_name']} (Score: {match['similarity_score']:.4f}, Stage1 Rank: {match['stage1_rank']})")
            
            # ================================================================
            # SIMILARITY DISTRIBUTION ANALYSIS
            # ================================================================
            
            distribution_stats = {}
            
            if len(matches) > 0:
                similarities = [m['similarity_score'] for m in matches]
                embedding_fusions = [m['embedding_fusion'] for m in matches]
                arcface_sims = [m['arcface_similarity'] for m in matches]
                facenet_sims = [m['facenet_similarity'] for m in matches]
                geometric_sims = [m['geometric_similarity'] for m in matches]
                
                # Compute statistics
                mean_similarity = float(np.mean(similarities))
                std_similarity = float(np.std(similarities))
                min_similarity = float(np.min(similarities))
                max_similarity = float(np.max(similarities))
                median_similarity = float(np.median(similarities))
                
                distribution_stats = {
                    "mean": mean_similarity,
                    "std_dev": std_similarity,
                    "min": min_similarity,
                    "max": max_similarity,
                    "median": median_similarity,
                    "total_candidates": len(matches),
                    "mean_embedding_fusion": float(np.mean(embedding_fusions)),
                    "mean_arcface": float(np.mean(arcface_sims)),
                    "mean_facenet": float(np.mean(facenet_sims)),
                    "mean_geometric": float(np.mean(geometric_sims))
                }
                
                print(f"\n[SIMILARITY DISTRIBUTION]")
                print(f"  Total candidates: {len(matches)}")
                print(f"  Mean similarity: {mean_similarity:.4f} ({mean_similarity*100:.1f}%)")
                print(f"  Std deviation: {std_similarity:.4f}")
                print(f"  Range: [{min_similarity:.4f}, {max_similarity:.4f}]")
                print(f"  Median: {median_similarity:.4f}")
                
                # Identify candidates significantly above average
                # Using 1 standard deviation above mean as threshold
                above_avg_threshold = mean_similarity + std_similarity
                
                for match in matches:
                    raw_similarity = match['similarity_score']
                    raw_fusion = match['embedding_fusion']
                    raw_arcface = match['arcface_similarity']
                    raw_facenet = match['facenet_similarity']
                    raw_geometric = match['geometric_similarity']
                    
                    # Calculate z-score (how many std devs above/below mean)
                    if std_similarity > 0:
                        z_score = (raw_similarity - mean_similarity) / std_similarity
                    else:
                        z_score = 0.0
                    
                    # Determine if significantly above average
                    is_above_average = raw_similarity > above_avg_threshold
                    
                    # Store analysis
                    match['statistical_analysis'] = {
                        "z_score": float(z_score),
                        "above_average": bool(is_above_average),
                        "deviation_from_mean": float(raw_similarity - mean_similarity),
                        "percentile": float((matches.index(match) + 1) / len(matches) * 100)
                    }
                    
                    # Assign category based on statistical position
                    if z_score >= 1.5:  # 1.5+ std devs above mean
                        match['similarity_category'] = 'HIGH'
                        match['confidence_level'] = 'high_similarity'
                        match['confidence_score'] = 85.0
                        match['match_quality'] = 'Significantly above average - Strong candidate'
                    elif z_score >= 0.5:  # 0.5-1.5 std devs above mean
                        match['similarity_category'] = 'MEDIUM'
                        match['confidence_level'] = 'medium_similarity'
                        match['confidence_score'] = 65.0
                        match['match_quality'] = 'Above average - Possible match'
                    elif z_score >= -0.5:  # Within 0.5 std devs of mean
                        match['similarity_category'] = 'MEDIUM'
                        match['confidence_level'] = 'medium_similarity'
                        match['confidence_score'] = 50.0
                        match['match_quality'] = 'Near average - Requires verification'
                    else:  # Below average
                        match['similarity_category'] = 'LOW'
                        match['confidence_level'] = 'low_similarity'
                        match['confidence_score'] = 35.0
                        match['match_quality'] = 'Below average - Lower priority'
                    
                    # ================================================================
                    # SCORE NORMALIZATION FOR UI PRESENTATION
                    # ================================================================
                    # Apply presentation-level normalization to make scores more interpretable
                    # for sketch-to-photo matching where raw cosine similarities are typically low
                    # 
                    # Formula: display_similarity = min(95, max(5, raw_similarity * 250))
                    # 
                    # This transformation:
                    # - Maps raw similarity [0, 1] to display range [5, 95]
                    # - Amplifies low similarities for better UI presentation
                    # - Maintains relative ordering for ranking
                    # 
                    # Both raw and display values are returned:
                    # - raw_similarity: Used for internal ranking and forensic calculations
                    # - display_similarity: Used for frontend visualization only
                    
                    def normalize_for_display(raw_score):
                        """Convert raw similarity to display percentage"""
                        return min(95.0, max(5.0, raw_score * 250.0))
                    
                    # Apply display normalization to all similarity scores
                    display_hybrid = normalize_for_display(raw_similarity)
                    display_fusion = normalize_for_display(raw_fusion)
                    display_arcface = normalize_for_display(raw_arcface)
                    display_facenet = normalize_for_display(raw_facenet)
                    display_geometric = normalize_for_display(raw_geometric)
                    
                    # Update match with normalized scores
                    match['similarity_score'] = float(display_hybrid)
                    match['raw_similarity_score'] = float(raw_similarity)
                    match['display_similarity'] = float(display_hybrid)
                    match['embedding_fusion'] = float(display_fusion)
                    match['raw_embedding_fusion'] = float(raw_fusion)
                    match['arcface_similarity'] = float(display_arcface)
                    match['raw_arcface_similarity'] = float(raw_arcface)
                    match['facenet_similarity'] = float(display_facenet)
                    match['raw_facenet_similarity'] = float(raw_facenet)
                    match['geometric_similarity'] = float(display_geometric)
                    match['raw_geometric_similarity'] = float(raw_geometric)
                    
                    # Add region similarity if available
                    if 'region_similarity' in match:
                        raw_region = match['region_similarity']
                        display_region = normalize_for_display(raw_region)
                        match['region_similarity'] = float(display_region)
                        match['raw_region_similarity'] = float(raw_region)
                    
                    match['score_normalization'] = 'Presentation-level normalization applied: display = min(95, max(5, raw * 250)). Use raw_similarity_score for ranking.'
                    
                    # Add detailed explanation for each result
                    explanation = {
                        "final_score": {
                            "value": float(display_hybrid),
                            "percentage": f"{display_hybrid:.1f}%",
                            "raw_value": float(raw_similarity),
                            "description": "Two-stage re-ranking score: 60% embedding + 25% geometric + 15% region"
                        },
                        "embedding_fusion": {
                            "value": float(display_fusion),
                            "percentage": f"{display_fusion:.1f}%",
                            "raw_value": float(raw_fusion),
                            "description": "Fused embedding similarity: 50% ArcFace + 50% Facenet512",
                            "weight": "60%"
                        },
                        "arcface_similarity": {
                            "value": float(display_arcface),
                            "percentage": f"{display_arcface:.1f}%",
                            "raw_value": float(raw_arcface),
                            "description": "ArcFace model similarity",
                            "weight": "50% of fusion"
                        },
                        "facenet_similarity": {
                            "value": float(display_facenet),
                            "percentage": f"{display_facenet:.1f}%",
                            "raw_value": float(raw_facenet),
                            "description": "Facenet512 model similarity",
                            "weight": "50% of fusion"
                        },
                        "geometric_similarity": {
                            "value": float(display_geometric),
                            "percentage": f"{display_geometric:.1f}%",
                            "raw_value": float(raw_geometric),
                            "description": "Facial structure and landmark similarity",
                            "weight": "25%"
                        },
                        "statistical_position": {
                            "z_score": float(z_score),
                            "description": f"{'Above' if z_score > 0 else 'Below'} average by {abs(z_score):.2f} standard deviations"
                        }
                    }
                    
                    # Add region similarity to explanation if available
                    if 'region_similarity' in match:
                        explanation["region_similarity"] = {
                            "value": float(match['region_similarity']),
                            "percentage": f"{match['region_similarity']:.1f}%",
                            "raw_value": float(match['raw_region_similarity']),
                            "description": "Multi-region similarity (eyes, nose, mouth)",
                            "weight": "15%"
                        }
                    
                    match['explanation'] = explanation
            
            # Return top 5 matches by default (re-ranked results)
            # Allow configurable top_n via query parameter
            top_n = int(request.form.get('top_n', 5))  # Default to 5 for re-ranked results
            top_n = min(max(top_n, 1), 10)  # Clamp between 1 and 10
            
            top_matches = matches[:top_n]
            
            # Add rank to each match
            for idx, match in enumerate(top_matches, 1):
                match['rank'] = idx
                
                # Add database comparison fields for investigators
                match['database_mean_similarity'] = float(mean_similarity) if len(matches) > 0 else 0.0
                match['similarity_above_average'] = bool(match['statistical_analysis']['above_average'])
                match['similarity_z_score'] = float(match['statistical_analysis']['z_score'])
                
                # Generate rank explanation for investigators
                z_score = match['statistical_analysis']['z_score']
                if idx == 1:
                    if z_score >= 1.5:
                        rank_explanation = f"Rank #{idx} candidate - similarity significantly above database average (top match with strong statistical confidence)"
                    elif z_score >= 0.5:
                        rank_explanation = f"Rank #{idx} candidate - similarity above database average (top match, moderate confidence)"
                    else:
                        rank_explanation = f"Rank #{idx} candidate - highest similarity in database (but near or below average, requires careful verification)"
                elif idx <= 3:
                    if z_score >= 1.5:
                        rank_explanation = f"Rank #{idx} candidate - similarity significantly above database average (strong candidate for investigation)"
                    elif z_score >= 0.5:
                        rank_explanation = f"Rank #{idx} candidate - similarity above database average (worth investigating)"
                    else:
                        rank_explanation = f"Rank #{idx} candidate - near or below database average (lower priority)"
                else:
                    if z_score >= 1.5:
                        rank_explanation = f"Rank #{idx} candidate - similarity significantly above database average"
                    elif z_score >= 0.5:
                        rank_explanation = f"Rank #{idx} candidate - similarity above database average"
                    elif z_score >= -0.5:
                        rank_explanation = f"Rank #{idx} candidate - similarity near database average"
                    else:
                        rank_explanation = f"Rank #{idx} candidate - similarity below database average"
                
                match['rank_explanation'] = rank_explanation
            
            print(f"\n[RESULTS]")
            print(f"  Total matches: {len(matches)}")
            print(f"  Returning top: {len(top_matches)}")
            print(f"  Database mean similarity: {mean_similarity:.4f} ({mean_similarity*100:.1f}%)" if len(matches) > 0 else "  No matches")
            print(f"  Candidates above average: {sum(1 for m in matches if m['statistical_analysis']['above_average'])}")
            
            for match in top_matches[:5]:  # Print first 5 for brevity
                print(f"\n  {match['rank_explanation']}")
                print(f"    Name: {match['criminal']['full_name']}")
                print(f"    Normalized - Hybrid: {match['similarity_score']:.1f}%, "
                      f"Fusion: {match['embedding_fusion']:.1f}% "
                      f"(Arc: {match['arcface_similarity']:.1f}%, Face: {match['facenet_similarity']:.1f}%), "
                      f"Geo: {match['geometric_similarity']:.1f}%")
                print(f"    Raw - Hybrid: {match['raw_similarity_score']:.4f}, "
                      f"Fusion: {match['raw_embedding_fusion']:.4f} "
                      f"(Arc: {match['raw_arcface_similarity']:.4f}, Face: {match['raw_facenet_similarity']:.4f}), "
                      f"Geo: {match['raw_geometric_similarity']:.4f}")
                print(f"    Z-score: {match['statistical_analysis']['z_score']:.2f}, "
                      f"Category: {match['similarity_category']}, "
                      f"Above avg: {match['similarity_above_average']}")
            
            if len(top_matches) > 5:
                print(f"\n  ... and {len(top_matches) - 5} more")
            
            return jsonify({
                "matches": top_matches,
                "total_matches": len(matches),
                "showing_top": len(top_matches),
                "threshold_used": threshold,
                "distribution_analysis": distribution_stats,
                "database_comparison": {
                    "mean_similarity": float(mean_similarity) if len(matches) > 0 else 0.0,
                    "std_deviation": float(std_similarity) if len(matches) > 0 else 0.0,
                    "candidates_above_average": sum(1 for m in matches if m['statistical_analysis']['above_average']),
                    "candidates_significantly_above_average": sum(1 for m in matches if m['statistical_analysis']['z_score'] >= 1.5),
                    "total_candidates_searched": len(search_results),
                    "interpretation": "Candidates with z-score >= 1.5 are significantly above average and should be prioritized for investigation."
                },
                "two_stage_pipeline": {
                    "stage1_method": "FAISS-accelerated fast retrieval" if use_faiss else "Linear search with cached embeddings",
                    "stage1_candidates": len(search_results),
                    "stage1_top_k": len(top_k_candidates),
                    "stage2_method": "Detailed re-ranking with geometric and region similarities",
                    "stage2_formula": "60% embedding + 25% geometric + 15% region",
                    "reranking_applied": True,
                    "faiss_enabled": use_faiss,
                    "faiss_available": is_faiss_index_ready()
                },
                "search_method": "Two-Stage Top-K Re-Ranking with FAISS (Stage 1: FAISS Fast Retrieval | Stage 2: Detailed Re-Ranking)" if use_faiss else "Two-Stage Top-K Re-Ranking (Stage 1: Linear Search | Stage 2: Detailed Re-Ranking)",
                "forensic_note": "Test-Time Augmentation (TTA) with 3 augmentations applied for robust embeddings. FAISS vector index used for fast similarity search. Two-stage re-ranking applied: Stage 1 selects Top-K candidates using FAISS-accelerated embedding comparison. Stage 2 performs detailed analysis with geometric and multi-region similarities. Results are re-ranked for optimal accuracy. Cross-domain sketch-to-photo matching has inherent limitations. Use as investigation leads, not absolute identification. Manual verification required." if use_faiss else "Test-Time Augmentation (TTA) with 3 augmentations applied for robust embeddings. Two-stage re-ranking applied: Stage 1 selects Top-K candidates using linear embedding comparison over cached embeddings. Stage 2 performs detailed analysis with geometric and multi-region similarities. Results are re-ranked for optimal accuracy. Cross-domain sketch-to-photo matching has inherent limitations. Use as investigation leads, not absolute identification. Manual verification required.",
                "interpretation_guide": {
                    "HIGH": "Significantly above average (1.5+ std devs) - Priority investigation",
                    "MEDIUM": "Above or near average (0.5-1.5 std devs) - Worth investigating",
                    "LOW": "Below average - Lower priority, but not excluded"
                },
                "usage_tips": [
                    "Review top 5-10 candidates manually",
                    "Compare embedding vs geometric scores for consistency",
                    "Candidates with high z-scores are statistical outliers (better matches)",
                    "Use explanation field to understand each match's scoring breakdown"
                ]
            })
            
        finally:
            # Clean up sketch temp file
            cleanup_temp_file(sketch_path)
                
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
            
            # Return the complete result with all normalized scores
            return jsonify({
                "distance": result.get('distance', 1.0),
                "similarity": result.get('similarity', 0.0),
                "raw_similarity": result.get('raw_similarity', 0.0),
                "display_similarity": result.get('display_similarity', 0.0),
                "final_embedding_similarity": result.get('final_embedding_similarity', 0.0),
                "embedding_fusion": result.get('embedding_fusion', 0.0),
                "arcface_similarity": result.get('arcface_similarity', 0.0),
                "facenet_similarity": result.get('facenet_similarity', 0.0),
                "geometric_similarity": result.get('geometric_similarity', 0.0),
                "multi_region_similarity": result.get('multi_region_similarity', 0.0),
                "raw_final_embedding_similarity": result.get('raw_final_embedding_similarity', 0.0),
                "raw_embedding_fusion": result.get('raw_embedding_fusion', 0.0),
                "raw_arcface_similarity": result.get('raw_arcface_similarity', 0.0),
                "raw_facenet_similarity": result.get('raw_facenet_similarity', 0.0),
                "raw_geometric_similarity": result.get('raw_geometric_similarity', 0.0),
                "raw_multi_region_similarity": result.get('raw_multi_region_similarity', 0.0),
                "eyes_similarity": result.get('eyes_similarity', 0.0),
                "nose_similarity": result.get('nose_similarity', 0.0),
                "mouth_similarity": result.get('mouth_similarity', 0.0),
                "full_face_similarity": result.get('full_face_similarity', 0.0),
                "confidence_level": result.get('confidence_level', 'uncertain'),
                "confidence_score": result.get('confidence_score', 0.0),
                "match_quality": result.get('match_quality', 'Unknown'),
                "similarity_category": result.get('similarity_category', 'UNKNOWN'),
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
            cleanup_temp_file(sketch_path)
            cleanup_temp_file(photo_path)
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
    result_count = len(RESULT_CACHE)
    clear_result_cache()
    return jsonify({
        "message": "Caches cleared successfully",
        "result_cache_cleared": result_count
    })


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats_endpoint():
    """Get cache statistics"""
    stats = get_cache_stats()
    return jsonify({
        "result_cache_size": stats['size'],
        "max_cache_size": stats['max_size'],
        "model_initialized": MODEL_INITIALIZED
    })

# ============================================================================
# CASE MANAGEMENT API ENDPOINTS
# ============================================================================

from database import Case, CaseNote

@app.route('/api/cases', methods=['GET'])
@authenticated
def get_all_cases():
    """Get a list of all cases"""
    db = None
    try:
        db = next(get_db())
        user = request.current_user
        
        # If admin, fetch all. If officer, you might want to fetch only their cases,
        # but for simplicity, we'll fetch all or filter by officer_id if provided.
        query = db.query(Case)
        
        # Optional: officer-specific filtering
        if user.role != 'admin':
             query = query.filter(Case.officer_id == user.id)
            
        cases = query.order_by(Case.created_at.desc()).all()
        
        cases_list = []
        for c in cases:
            cases_list.append({
                "id": c.id,
                "case_number": c.case_number,
                "title": c.title,
                "status": c.status,
                "description": c.description,
                "priority": c.priority,
                "crime_type": c.crime_type,
                "incident_date": c.incident_date.isoformat() if c.incident_date else None,
                "location": c.location,
                "officer_id": c.officer_id,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            })
            
        return jsonify({"cases": cases_list}), 200
        
    except Exception as e:
        print(f"/api/cases GET error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cases/<int:case_id>', methods=['GET'])
@authenticated
def get_case(case_id):
    """Get details for a specific case"""
    db = None
    try:
        db = next(get_db())
        case = db.query(Case).filter(Case.id == case_id).first()
        
        if not case:
            return jsonify({"error": "Case not found"}), 404
            
        return jsonify({
            "case": {
                "id": case.id,
                "case_number": case.case_number,
                "title": case.title,
                "status": case.status,
                "description": case.description,
                "priority": case.priority,
                "crime_type": case.crime_type,
                "incident_date": case.incident_date.isoformat() if case.incident_date else None,
                "location": case.location,
                "officer_id": case.officer_id,
                "linked_criminals": [c.criminal_id for c in case.criminals],
                "created_at": case.created_at.isoformat(),
                "updated_at": case.updated_at.isoformat() if case.updated_at else None
            }
        }), 200
        
    except Exception as e:
        print(f"/api/cases/{case_id} GET error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/api/cases', methods=['POST'])
@authenticated
def create_case():
    """Create a new case"""
    db = None
    try:
        data = request.get_json()
        
        if not data.get('title'):
            return jsonify({"error": "Title is required"}), 400
            
        db = next(get_db())
        user = request.current_user
        
        # Generate robust unique case number
        year = datetime.now(timezone.utc).year
        case_count = db.query(Case).count() + 1
        case_number = f"CASE-{year}-{case_count:04d}-{str(uuid.uuid4())[:4].upper()}"
        
        # Parse optional dates
        incident_date = None
        if data.get('incident_date'):
            try:
                # Handle basic ISO format YYYY-MM-DD
                incident_date = datetime.fromisoformat(data.get('incident_date').replace('Z', '+00:00'))
            except ValueError:
                pass
        
        new_case = Case(
            case_number=data.get('case_number', case_number),
            title=data.get('title'),
            description=data.get('description', ''),
            status=data.get('status', 'Open'),
            priority=data.get('priority', 'Medium'),
            crime_type=data.get('crime_type'),
            officer_id=user.id,
            incident_date=incident_date,
            location=data.get('location', ''),
        )
        
        db.add(new_case)

        # Link criminals via association table
        criminal_ids = data.get('linked_criminals', [])
        if criminal_ids:
            criminals = db.query(Criminal).filter(Criminal.criminal_id.in_(criminal_ids)).all()
            new_case.criminals.extend(criminals)

        db.commit()
        db.refresh(new_case)
        
        return jsonify({
            "message": "Case created successfully",
            "case_id": new_case.id,
            "case_number": new_case.case_number
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/cases POST error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cases/<int:case_id>', methods=['PUT', 'PATCH'])
@authenticated
def update_case(case_id):
    """Update an existing case"""
    db = None
    try:
        data = request.get_json()
        db = next(get_db())
        
        case = db.query(Case).filter(Case.id == case_id).first()
        
        if not case:
            return jsonify({"error": "Case not found"}), 404
            
        # Update fields if provided
        if 'title' in data:
            case.title = data['title']
        if 'description' in data:
            case.description = data['description']
        if 'status' in data:
            case.status = data['status']
        if 'priority' in data:
            case.priority = data['priority']
        if 'crime_type' in data:
            case.crime_type = data['crime_type']
        if 'location' in data:
            case.location = data['location']
        if 'linked_criminals' in data:
            # Replace association table entries
            criminals = db.query(Criminal).filter(Criminal.criminal_id.in_(data['linked_criminals'])).all()
            case.criminals = criminals
            
        case.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return jsonify({"message": "Case updated successfully"}), 200
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/cases/{case_id} PUT/PATCH error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cases/<int:case_id>', methods=['DELETE'])
@authenticated
def delete_case(case_id):
    """Delete a case"""
    db = None
    try:
        db = next(get_db())
        case = db.query(Case).filter(Case.id == case_id).first()
        
        if not case:
            return jsonify({"error": "Case not found"}), 404
            
        db.delete(case)
        db.commit()
        
        return jsonify({"message": "Case deleted successfully"}), 200
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/cases/{case_id} DELETE error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()

# ============================================================================
# CASE NOTES API ENDPOINTS
# ============================================================================

@app.route('/api/cases/<int:case_id>/notes', methods=['GET'])
@authenticated
def get_case_notes(case_id):
    """Get all notes for a specific case"""
    db = None
    try:
        db = next(get_db())
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return jsonify({"error": "Case not found"}), 404
            
        notes = db.query(CaseNote).filter(CaseNote.case_id == case_id).order_by(CaseNote.created_at.desc()).all()
        
        notes_list = []
        for n in notes:
            notes_list.append({
                "id": n.id,
                "case_id": n.case_id,
                "author_id": n.author_id,
                "author_name": n.author_name,
                "content": n.content,
                "created_at": n.created_at.isoformat()
            })
            
        return jsonify({"notes": notes_list}), 200
        
    except Exception as e:
        print(f"/api/cases/{case_id}/notes GET error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cases/<int:case_id>/notes', methods=['POST'])
@authenticated
def create_case_note(case_id):
    """Create a new note for a specific case"""
    db = None
    try:
        data = request.get_json()
        if not data.get('content'):
            return jsonify({"error": "Content is required"}), 400
            
        db = next(get_db())
        user = request.current_user
        
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return jsonify({"error": "Case not found"}), 404
            
        # Optional: verify user has access to case
        
        new_note = CaseNote(
            case_id=case_id,
            author_id=user.id,
            author_name=data.get('author_name', user.full_name or user.email.split('@')[0]),  # default to full name
            content=data.get('content')
        )
        
        db.add(new_note)
        case.updated_at = datetime.now(timezone.utc) # Update the case's modified time
        db.commit()
        db.refresh(new_note)
        
        return jsonify({
            "message": "Note added successfully",
            "note": {
                "id": new_note.id,
                "case_id": new_note.case_id,
                "author_id": new_note.author_id,
                "author_name": new_note.author_name,
                "content": new_note.content,
                "created_at": new_note.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        print(f"/api/cases/{case_id}/notes POST error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "FaceFind Forensics API v2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


if __name__ == '__main__':
    # Disable output buffering for immediate console output
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    
    print("\n" + "=" * 60)
    print("FaceFind Forensics API v2 - Hybrid Scoring System")
    print("=" * 60)
    print("[OK] Role-Based Authentication (Admin OTP + Officer)")
    print("[OK] Criminal Database Management")
    print("[OK] Face Comparison with Hybrid Scoring")
    print("=" * 60)
    
    # Initialize DeepFace models on startup
    initialize_models()
    
    # Precompute database embeddings on startup
    precompute_database_embeddings()
    
    port = int(os.environ.get('PORT', '5001'))
    print(f"\n[OK] Server ready on http://localhost:{port}")
    print("=" * 60 + "\n")
    sys.stdout.flush()
    
    # Run with debug=False to prevent Werkzeug reloader child-process deadlocks with TensorFlow/Keras
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)

