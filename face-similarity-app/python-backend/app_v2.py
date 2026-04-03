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

# Import S3 model loader
from utils.s3_model_loader import setup_models

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
# STARTUP INITIALIZATION — GUNICORN --preload SAFE
# ============================================================================
# With Gunicorn --preload, the app module is imported in the MASTER process
# before workers are forked. We run initialization SYNCHRONOUSLY here so it
# completes fully before any fork() happens.
#
# A file-based flag (/tmp/facefind_startup_complete.flag) is written at the
# end of startup. All workers (forked or otherwise) check this file — it is
# visible across all processes on the same host/container.
#
# The in-memory thread approach is intentionally removed: threads do not
# survive fork(), so _STARTUP_DONE / MODEL_INITIALIZED set in the master
# thread are NOT reliably visible in forked workers.
# ============================================================================

from services.embedding_service import MODEL_INITIALIZED, is_models_initialized
from services.embedding_service import warmup_models
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

# File-based readiness flag — visible to all processes on the same host
STARTUP_FLAG_PATH = os.path.join(os.path.dirname(__file__), 'startup_complete.flag')


# ============================================================================
# PRECOMPUTE DATABASE EMBEDDINGS
# ============================================================================
# Defined HERE — above _run_startup() — so it is in scope when _run_startup()
# is called synchronously at module level during Gunicorn --preload import.
# ============================================================================

def precompute_database_embeddings():
    """
    Precompute and cache dual embeddings (InsightFace + Facenet) for all criminals in database.
    Called at startup. Persists embeddings to DB so they survive server restarts.
    Uses enforce_detection=False so imperfect/sketch-style photos don't cause failures.
    """
    print("\n" + "="*60)
    print("PRECOMPUTING DATABASE DUAL EMBEDDINGS (InsightFace + Facenet)")
    print("="*60)

    db = next(get_db())
    try:
        criminals = db.query(Criminal).all()
        print(f"Found {len(criminals)} criminals in database")

        updated_count = 0
        cached_count  = 0
        failed_count  = 0

        for criminal in criminals:
            try:
                # ── Fast path: valid embedding already in DB ──────────────
                if (
                    criminal.face_embedding
                    and isinstance(criminal.face_embedding, dict)
                    and 'insightface' in criminal.face_embedding
                    and criminal.embedding_version == EMBEDDING_VERSION
                ):
                    ins_emb  = np.array(criminal.face_embedding['insightface'])
                    face_emb = np.array(criminal.face_embedding['facenet']) \
                               if 'facenet' in criminal.face_embedding \
                               and criminal.face_embedding['facenet'] is not None \
                               else None
                    set_cached_embedding(criminal.criminal_id, ins_emb, face_emb)
                    cached_count += 1
                    print(f"  [CACHE LOAD] {criminal.criminal_id} — loaded from DB into memory cache")
                    continue

                # ── Slow path: compute embeddings from S3 photo ───────────
                print(f"  [COMPUTE] {criminal.criminal_id} — embedding missing/outdated")

                if not criminal.photo_key:
                    print(f"  [ERROR] No photo_key for {criminal.criminal_id} — skipping")
                    failed_count += 1
                    continue

                signed_url = get_signed_url(criminal.photo_key)
                if not signed_url:
                    print(f"  [ERROR] Could not generate signed URL for {criminal.criminal_id} — skipping")
                    failed_count += 1
                    continue

                temp_path = generate_temp_filepath(
                    original_filename=criminal.photo_filename or 'criminal.jpg',
                    prefix='criminal'
                )
                try:
                    import urllib.request as _urlreq
                    _urlreq.urlretrieve(signed_url, temp_path)

                    if not os.path.exists(temp_path):
                        print(f"  [ERROR] Temp file not created for {criminal.criminal_id} — skipping")
                        failed_count += 1
                        continue

                    test_img = cv2.imread(temp_path)
                    if test_img is None:
                        print(f"  [ERROR] cv2.imread() failed for {criminal.criminal_id} — skipping")
                        failed_count += 1
                        continue

                    # enforce_detection=False — tolerate imperfect/non-frontal photos
                    embeddings = extract_dual_embeddings(
                        temp_path,
                        is_sketch=False,
                        use_adaptive_canny=False
                    )

                    if not embeddings or not embeddings.get('success'):
                        print(f"  [ERROR] extract_dual_embeddings failed for {criminal.criminal_id}: "
                              f"{embeddings.get('error') if embeddings else 'None returned'}")
                        failed_count += 1
                        continue

                    insightface_emb = embeddings['insightface']
                    facenet_emb     = embeddings['facenet']

                    # Mirror missing slot (one model may be unavailable)
                    if insightface_emb is None and facenet_emb is not None:
                        insightface_emb = facenet_emb
                        print(f"  [INFO] InsightFace unavailable — mirroring Facenet for {criminal.criminal_id}")
                    elif facenet_emb is None and insightface_emb is not None:
                        facenet_emb = insightface_emb
                        print(f"  [INFO] Facenet unavailable — mirroring InsightFace for {criminal.criminal_id}")

                    if insightface_emb is None or facenet_emb is None:
                        print(f"  [ERROR] Both embeddings None for {criminal.criminal_id} — skipping")
                        failed_count += 1
                        continue

                    # ── Persist to DB (critical — survives restarts) ──────
                    criminal.face_embedding = {
                        'insightface': insightface_emb.tolist(),
                        'facenet':     facenet_emb.tolist() if facenet_emb is not None else None,
                    }
                    criminal.embedding_version = EMBEDDING_VERSION
                    db.commit()

                    # ── Populate in-memory cache ──────────────────────────
                    set_cached_embedding(criminal.criminal_id, insightface_emb, facenet_emb)

                    updated_count += 1
                    print(f"  [CACHE LOAD] {criminal.criminal_id} — computed + persisted + loaded into memory cache")

                finally:
                    cleanup_temp_file(temp_path)

            except Exception as e:
                print(f"  [ERROR] Unexpected error for {criminal.criminal_id}: {e}")
                traceback.print_exc()
                failed_count += 1
                try:
                    db.rollback()
                except Exception:
                    pass
                continue

        print(f"\n[SUMMARY]")
        print(f"  [CACHE LOAD] Loaded from DB cache : {cached_count}")
        print(f"  [CACHE LOAD] Newly computed       : {updated_count}")
        print(f"  Failed                            : {failed_count}")
        print(f"  Total in memory cache             : {get_cache_size()}")
        print("="*60 + "\n")

        # Build FAISS index after all embeddings are in cache
        build_faiss_index()

    except Exception as e:
        print(f"[ERROR] precompute_database_embeddings() failed: {e}")
        traceback.print_exc()
    finally:
        db.close()


def _is_startup_complete() -> bool:
    """Cross-process readiness check — reads flag file."""
    return os.path.isfile(STARTUP_FLAG_PATH)


def _mark_startup_complete():
    """Write flag file so all workers see startup as done."""
    try:
        with open(STARTUP_FLAG_PATH, 'w') as f:
            f.write(datetime.now(timezone.utc).isoformat())
        print(f"[STARTUP] Flag written: {STARTUP_FLAG_PATH}", flush=True)
    except Exception as e:
        print(f"[STARTUP] [WARNING] Could not write flag file: {e}", flush=True)


def _clear_startup_flag():
    """Remove flag file — called once at process start to force re-init."""
    try:
        if os.path.isfile(STARTUP_FLAG_PATH):
            os.remove(STARTUP_FLAG_PATH)
    except Exception:
        pass


def _run_startup():
    """
    Synchronous full ML pipeline initialization.
    Runs in the Gunicorn master process (before fork) when --preload is used.
    Writes a file-based flag on completion so all forked workers see it.
    """
    import sys
    sys.stdout.reconfigure(line_buffering=True)

    print("\n" + "=" * 60)
    print("FaceFind Forensics API v2 — Startup Initialization")
    print("=" * 60)

    # Step 1: Download models from S3 if not present locally
    print("[STARTUP] Step 1: Checking/downloading ML models from S3...")
    try:
        setup_models()
    except Exception as e:
        print(f"[STARTUP] [ERROR] setup_models() failed: {e}")
        traceback.print_exc()

    # Step 2: Initialize face recognition models (InsightFace + Facenet512)
    print("[STARTUP] Step 2: Initializing face recognition models...")
    try:
        initialize_models()
    except Exception as e:
        print(f"[STARTUP] [ERROR] initialize_models() failed: {e}")
        traceback.print_exc()

    # Step 3: Warmup both models — compiles TF/ONNX graphs before first request
    print("[STARTUP] Step 3: Warming up models (preloading inference graphs)...")
    try:
        warmup_models()
    except Exception as e:
        print(f"[STARTUP] [ERROR] warmup_models() failed: {e}")
        traceback.print_exc()

    # Step 4: Precompute embeddings for all criminals in DB + build FAISS index
    print("[STARTUP] Step 4: Precomputing database embeddings + building FAISS index...")
    print(f"[DEBUG] precompute_database_embeddings available: {callable(precompute_database_embeddings)}")
    try:
        precompute_database_embeddings()
    except Exception as e:
        print(f"[STARTUP] [ERROR] precompute_database_embeddings() failed: {e}")
        traceback.print_exc()

    # Write cross-process flag ONLY after all steps complete
    _mark_startup_complete()

    print(f"[STARTUP] MODEL_INITIALIZED = {is_models_initialized()}")
    print(f"[STARTUP] FAISS ready       = {is_faiss_index_ready()}")
    print(f"[STARTUP] Embedding cache   = {get_cache_size()} entries")
    print(f"[STARTUP] Flag file         = {STARTUP_FLAG_PATH}")
    print("[STARTUP] Initialization complete.")
    print("=" * 60 + "\n")
    sys.stdout.flush()


# Remove stale flag from any previous run so startup always re-runs fresh
_clear_startup_flag()

# Run synchronously — completes before Gunicorn forks workers (--preload)
_run_startup()

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
        print("  [STEP 2] DeepFace removed — test endpoint disabled")
        return {
            'success': False,
            'distance': 1.0,
            'similarity': 0.0,
            'threshold': 0.4,
            'model_verified': False,
            'error': 'DeepFace has been removed. Use /api/compare instead.'
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
                # Extract dual embeddings (InsightFace + Facenet)
                embeddings = extract_dual_embeddings(
                    image_path=temp_photo_path,
                    is_sketch=False,
                    use_adaptive_canny=False
                )

                if embeddings and embeddings.get('success'):
                    insightface_emb = embeddings['insightface']
                    facenet_emb     = embeddings['facenet']

                    # Mirror missing slot if one model is unavailable
                    if insightface_emb is None and facenet_emb is not None:
                        insightface_emb = facenet_emb
                        print(f"  [INFO] InsightFace unavailable — mirroring Facenet")
                    elif facenet_emb is None and insightface_emb is not None:
                        facenet_emb = insightface_emb
                        print(f"  [INFO] Facenet unavailable — mirroring InsightFace")

                    if insightface_emb is not None and facenet_emb is not None:
                        # ── Persist embeddings to DB (survives restarts) ──
                        db2 = next(get_db())
                        try:
                            db_criminal = db2.query(Criminal).filter(
                                Criminal.criminal_id == new_criminal.criminal_id
                            ).first()
                            if db_criminal:
                                db_criminal.face_embedding = {
                                    'insightface': insightface_emb.tolist(),
                                    'facenet':     facenet_emb.tolist()
                                }
                                db_criminal.embedding_version = EMBEDDING_VERSION
                                db2.commit()
                                print(f"  [OK] Embeddings persisted to DB for: {new_criminal.criminal_id}")
                        except Exception as db_err:
                            db2.rollback()
                            print(f"  [WARNING] Failed to persist embeddings to DB: {db_err}")
                        finally:
                            db2.close()

                        # ── Populate in-memory cache ──────────────────────
                        set_cached_embedding(
                            criminal_id=new_criminal.criminal_id,
                            insightface_embedding=insightface_emb,
                            facenet_embedding=facenet_emb
                        )
                        print(f"  [CACHE LOAD] {new_criminal.criminal_id} — new criminal loaded into memory cache")

                        # ── Rebuild FAISS index ───────────────────────────
                        print(f"  [FAISS] Rebuilding index to include new criminal...")
                        build_faiss_index()
                        print(f"  [OK] FAISS index rebuilt — new criminal is now searchable")
                    else:
                        print(f"  [WARNING] Both embeddings None — criminal saved but not searchable")
                else:
                    err = embeddings.get('error') if embeddings else 'None returned'
                    print(f"  [WARNING] Embedding extraction failed: {err}")
                    print(f"  [WARNING] Criminal saved but not immediately searchable")

            finally:
                cleanup_temp_file(temp_photo_path)

        except Exception as e:
            # Log error but don't fail the request — criminal record is already saved
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

    # ── Model readiness guard ─────────────────────────────────────────────
    # Check file-based flag — visible across all Gunicorn worker processes.
    if not _is_startup_complete():
        print(f"[search_criminals] Startup flag missing — system not ready.", flush=True)
        print(f"[search_criminals] MODEL_INITIALIZED = {is_models_initialized()}", flush=True)
        print(f"[search_criminals] Flag path: {STARTUP_FLAG_PATH}", flush=True)
        return jsonify({
            "error": "Face recognition models are still initializing. Please retry in a moment."
        }), 503

    print("\n" + "="*60, flush=True)
    print("CRIMINAL SEARCH STARTED (OPTIMIZED)", flush=True)
    print("="*60, flush=True)
    sys.stdout.flush()

    db = None
    try:
        if 'sketch' not in request.files:
            return jsonify({"error": "Sketch file is required"}), 400

        sketch_file = request.files['sketch']
        threshold = float(request.form.get('threshold', 0.2))  # Lowered for sketch matching

        print(f"Sketch file received: {sketch_file.filename}")
        print(f"Distance threshold: {threshold}")

        # Save sketch to temporary file
        sketch_path = save_temp_file(sketch_file)
        print(f"Sketch saved to: {sketch_path}")

        try:
            # Extract DUAL embeddings for query sketch ONCE
            print(f"\n[QUERY DUAL EMBEDDING] Extracting dual embeddings (InsightFace + Facenet) for sketch...")
            query_embeddings = extract_dual_embeddings(sketch_path, is_sketch=True)

            if query_embeddings is None or not query_embeddings['success']:
                return jsonify({"error": "Failed to extract dual embeddings from sketch"}), 400

            print(f"  [OK] Query dual embeddings extracted:")
            if query_embeddings['insightface'] is not None:
                print(f"    InsightFace: length={len(query_embeddings['insightface'])}, normalized")
            else:
                print(f"    InsightFace: unavailable (model not loaded)")
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
            
            # Select Top-K candidates for re-ranking (default K=10, max 50 for FAISS)
            top_k = int(request.form.get('top_k', 10))
            top_k = min(max(top_k, 1), 50)  # Clamp between 1 and 50
            
            # Get all criminal IDs from database
            criminal_ids = [c.criminal_id for c in criminals]
            
            # Use FAISS service for search (automatically falls back to linear search if FAISS not available)
            # Use whichever embedding is available; FAISS service handles None gracefully
            query_insightface = query_embeddings['insightface']
            query_facenet = query_embeddings['facenet']
            # If one model is missing, mirror the other so fusion still works
            if query_insightface is None and query_facenet is not None:
                query_insightface = query_facenet
                print("  [WARN] InsightFace unavailable - using Facenet embedding for FAISS insightface slot")
            elif query_facenet is None and query_insightface is not None:
                query_facenet = query_insightface
                print("  [WARN] Facenet unavailable - using InsightFace embedding for FAISS facenet slot")

            search_results, use_faiss = search_top_k_candidates(
                query_insightface,
                query_facenet,
                criminal_ids,
                top_k
            )
            
            # Convert search results to stage1_candidates format
            # Recompute fusion score using SAME formula as Stage 2:
            # final = 0.6 * insightface + 0.4 * facenet
            # This ensures Stage 1 ranking is consistent with Stage 2.
            criminal_dict = {c.criminal_id: c for c in criminals}
            top_k_candidates = []

            q_ins_n  = query_insightface / (np.linalg.norm(query_insightface) + 1e-10) \
                       if query_insightface is not None else None
            q_face_n = query_embeddings['facenet'] / (np.linalg.norm(query_embeddings['facenet']) + 1e-10) \
                       if query_embeddings.get('facenet') is not None else None

            for result in search_results:
                criminal_id = result['criminal_id']
                if criminal_id not in criminal_dict:
                    continue

                cached = get_cached_embedding(criminal_id)
                if cached is not None and cached.get("insightface") is not None and q_ins_n is not None:
                    # Recompute InsightFace similarity from cache
                    c_ins_n = cached["insightface"] / (np.linalg.norm(cached["insightface"]) + 1e-10)
                    sim_ins = float(np.dot(q_ins_n, c_ins_n))

                    # Recompute Facenet similarity from cache if available
                    c_face = cached.get("facenet")
                    if q_face_n is not None and c_face is not None:
                        c_face_n = c_face / (np.linalg.norm(c_face) + 1e-10)
                        sim_face = float(np.dot(q_face_n, c_face_n))
                        fused = max(sim_ins, sim_face)
                    else:
                        sim_face = None
                        fused = sim_ins
                else:
                    # Fallback to FAISS score if cache miss
                    sim_ins  = result['insightface_similarity']
                    sim_face = result['facenet_similarity']
                    fused    = result['embedding_fusion']

                top_k_candidates.append({
                    'criminal':              criminal_dict[criminal_id],
                    'embedding_fusion':      fused,
                    'insightface_similarity': sim_ins,
                    'facenet_similarity':    sim_face,
                })

            # Sort Stage 1 candidates by the fused score (same formula as Stage 2)
            top_k_candidates.sort(key=lambda x: x['embedding_fusion'], reverse=True)
            print(f"\n[STAGE 1 FUSED RANKING]")
            for i, c in enumerate(top_k_candidates, 1):
                print(f"  {i}. {c['criminal'].criminal_id}: fused={c['embedding_fusion']:.6f} "
                      f"(ins={c['insightface_similarity']:.4f}, "
                      f"face={c['facenet_similarity'] if c['facenet_similarity'] is not None else 'N/A'})")
            
            # ================================================================
            # STAGE 2: RE-RANKING — uses cached embeddings, NO S3 download,
            # NO TTA recomputation. Query embedding computed once above.
            # ================================================================
            print(f"\n[STAGE 2: RE-RANKING]")
            print(f"  Re-ranking Top-{len(top_k_candidates)} candidates using cached embeddings...")

            matches = []

            for candidate in top_k_candidates:
                try:
                    criminal          = candidate['criminal']
                    embedding_fusion  = candidate['embedding_fusion']
                    insightface_sim   = candidate['insightface_similarity']
                    facenet_sim       = candidate['facenet_similarity']

                    # ── CACHE HIT: compute fusion from both cached embeddings ──
                    cached = get_cached_embedding(criminal.criminal_id)
                    if cached is not None and cached.get("insightface") is not None:
                        print(f"  [CACHE HIT] {criminal.criminal_id} — using stored embeddings")

                        q_ins  = query_embeddings['insightface']
                        q_face = query_embeddings['facenet']

                        # InsightFace similarity
                        c_ins = cached["insightface"]
                        q_ins_n = q_ins  / (np.linalg.norm(q_ins)  + 1e-10)
                        c_ins_n = c_ins  / (np.linalg.norm(c_ins)  + 1e-10)
                        sim_insight = float(np.dot(q_ins_n, c_ins_n))

                        # Facenet similarity (if available in both query and cache)
                        c_face = cached.get("facenet")
                        if q_face is not None and c_face is not None:
                            q_face_n = q_face / (np.linalg.norm(q_face) + 1e-10)
                            c_face_n = c_face / (np.linalg.norm(c_face) + 1e-10)
                            sim_facenet = float(np.dot(q_face_n, c_face_n))
                            final_score = max(sim_insight, sim_facenet)
                        else:
                            sim_facenet = None
                            final_score = sim_insight  # InsightFace only

                        insightface_sim  = sim_insight
                        facenet_sim      = sim_facenet
                        embedding_fusion = final_score

                        print(f"  [DEBUG] Insight: {sim_insight:.6f}, Facenet: {sim_facenet if sim_facenet is not None else 'N/A'}, Final: {final_score:.6f}")
                    else:
                        print(f"  [WARN] {criminal.criminal_id} — no cached embedding, using Stage 1 score")
                        final_score = embedding_fusion

                    embedding_confidence = 1.0
                    geometric_similarity = 0.0
                    region_similarity = 0.0

                    print(f"  {criminal.full_name}:")
                    print(f"    Final Score: {final_score:.6f}")

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
                        "similarity_score":      float(final_score),
                        "embedding_fusion":      float(embedding_fusion),
                        "embedding_confidence":  float(embedding_confidence),
                        "insightface_similarity": float(insightface_sim) if insightface_sim is not None else None,
                        "facenet_similarity":    float(facenet_sim) if facenet_sim is not None else None,
                        "geometric_similarity":  float(geometric_similarity),
                        "region_similarity":     float(region_similarity),
                        "distance":              float(1.0 - final_score),
                        "model_used":            "InsightFace + Facenet (max fusion)",
                        "metric_used":           "final_score = max(cosine(insight_q, insight_db), cosine(facenet_q, facenet_db))",
                        "is_cross_domain":       True,
                        "stage1_rank":           top_k_candidates.index(candidate) + 1,
                        "reranking_applied":     True,
                        "cache_hit":             cached is not None,
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

            # Safe defaults — used even when matches is empty
            mean_similarity   = 0.0
            std_similarity    = 0.0
            min_similarity    = 0.0
            max_similarity    = 0.0
            median_similarity = 0.0
            distribution_stats = {}

            def _safe_float(v):
                """Convert any numeric value (including np types) to Python float. None -> 0.0."""
                if v is None:
                    return 0.0
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return 0.0

            def normalize_for_display(raw_score):
                """
                Convert raw cosine similarity [-1, 1] to display percentage [5, 95].
                Calibrated for InsightFace ArcFace:
                  raw = -1.0  -> display =  5%
                  raw =  0.0  -> display = 30%
                  raw =  0.4  -> display = 50%
                  raw =  0.6  -> display = 65%
                  raw =  0.8  -> display = 80%
                  raw =  1.0  -> display = 95%
                """
                v = _safe_float(raw_score)
                # Map [-1, 1] -> [5, 95]: display = 5 + (v + 1) / 2 * 90
                return min(95.0, max(5.0, 5.0 + (v + 1.0) / 2.0 * 90.0))

            if len(matches) > 0:
                similarities     = [m['similarity_score'] for m in matches]
                embedding_fusions = [m['embedding_fusion'] for m in matches]
                insightface_sims = [m['insightface_similarity'] for m in matches]
                facenet_sims     = [m['facenet_similarity'] for m in matches]
                geometric_sims   = [m['geometric_similarity'] for m in matches]

                mean_similarity   = float(np.mean(similarities))
                std_similarity    = float(np.std(similarities))
                min_similarity    = float(np.min(similarities))
                max_similarity    = float(np.max(similarities))
                median_similarity = float(np.median(similarities))

                distribution_stats = {
                    "mean":                  mean_similarity,
                    "std_dev":               std_similarity,
                    "min":                   min_similarity,
                    "max":                   max_similarity,
                    "median":                median_similarity,
                    "total_candidates":      len(matches),
                    "mean_embedding_fusion": float(np.mean(embedding_fusions)),
                    "mean_arcface":          float(np.mean([s for s in insightface_sims if s is not None])) if any(s is not None for s in insightface_sims) else None,
                    "mean_facenet":          float(np.mean([s for s in facenet_sims if s is not None])) if any(s is not None for s in facenet_sims) else None,
                    "mean_geometric":        float(np.mean(geometric_sims))
                }

                print(f"\n[SIMILARITY DISTRIBUTION]")
                print(f"  Total candidates: {len(matches)}")
                print(f"  Mean similarity: {mean_similarity:.4f} ({mean_similarity*100:.1f}%)")
                print(f"  Std deviation: {std_similarity:.4f}")
                print(f"  Range: [{min_similarity:.4f}, {max_similarity:.4f}]")
                print(f"  Median: {median_similarity:.4f}")

                above_avg_threshold = mean_similarity + std_similarity

                for match in matches:
                    raw_similarity = _safe_float(match['similarity_score'])
                    raw_fusion     = _safe_float(match['embedding_fusion'])
                    raw_arcface    = _safe_float(match['insightface_similarity'])
                    raw_facenet    = _safe_float(match['facenet_similarity'])
                    raw_geometric  = _safe_float(match['geometric_similarity'])

                    z_score = (raw_similarity - mean_similarity) / std_similarity if std_similarity > 0 else 0.0
                    is_above_average = raw_similarity > above_avg_threshold

                    match['statistical_analysis'] = {
                        "z_score":             float(z_score),
                        "above_average":       bool(is_above_average),
                        "deviation_from_mean": float(raw_similarity - mean_similarity),
                        "percentile":          float((matches.index(match) + 1) / len(matches) * 100)
                    }

                    # Absolute threshold classification — independent of
                    # database size or distribution, so a single-criminal DB
                    # doesn't inflate every result to HIGH.
                    if raw_similarity > 0.4:
                        match['similarity_category'] = 'HIGH'
                        match['confidence_level']    = 'high_similarity'
                        match['confidence_score']    = 85.0
                        match['match_quality']       = 'High similarity - Strong candidate for investigation'
                    elif raw_similarity > 0.25:
                        match['similarity_category'] = 'MEDIUM'
                        match['confidence_level']    = 'medium_similarity'
                        match['confidence_score']    = 60.0
                        match['match_quality']       = 'Medium similarity - Possible match, worth investigating'
                    else:
                        match['similarity_category'] = 'LOW'
                        match['confidence_level']    = 'low_similarity'
                        match['confidence_score']    = 30.0
                        match['match_quality']       = 'Low similarity - Unlikely match'

                    # Normalize all scores for display
                    display_hybrid    = normalize_for_display(raw_similarity)
                    display_fusion    = normalize_for_display(raw_fusion)
                    display_arcface   = normalize_for_display(raw_arcface)
                    display_facenet   = normalize_for_display(raw_facenet)
                    display_geometric = normalize_for_display(raw_geometric)

                    match['similarity_score']          = float(display_hybrid)
                    match['raw_similarity_score']      = float(raw_similarity)
                    match['display_similarity']        = float(display_hybrid)
                    match['embedding_fusion']          = float(display_fusion)
                    match['raw_embedding_fusion']      = float(raw_fusion)
                    match['insightface_similarity']    = float(display_arcface)
                    match['raw_insightface_similarity'] = float(raw_arcface)
                    match['facenet_similarity']        = float(display_facenet)
                    match['raw_facenet_similarity']    = float(raw_facenet)
                    match['geometric_similarity']      = float(display_geometric)
                    match['raw_geometric_similarity']  = float(raw_geometric)

                    if 'region_similarity' in match:
                        raw_region = _safe_float(match['region_similarity'])
                        match['region_similarity']     = float(normalize_for_display(raw_region))
                        match['raw_region_similarity'] = float(raw_region)

                    match['score_normalization'] = (
                        'Presentation-level normalization applied: '
                        'display = min(95, max(5, (raw - 0.2) * 150)). '
                        'Use raw_similarity_score for ranking.'
                    )

                    match['explanation'] = {
                        "final_score": {
                            "value":       float(display_hybrid),
                            "percentage":  f"{display_hybrid:.1f}%",
                            "raw_value":   float(raw_similarity),
                            "description": "Two-stage re-ranking score: 60% embedding + 25% geometric + 15% region"
                        },
                        "embedding_fusion": {
                            "value":       float(display_fusion),
                            "percentage":  f"{display_fusion:.1f}%",
                            "raw_value":   float(raw_fusion),
                            "description": "Fused embedding similarity: Max(ArcFace, Facenet512)",
                            "weight":      "100%"
                        },
                        "insightface_similarity": {
                            "value":       float(display_arcface),
                            "percentage":  f"{display_arcface:.1f}%",
                            "raw_value":   float(raw_arcface),
                            "description": "ArcFace model similarity",
                            "weight":      "Considered in Max Fusion"
                        },
                        "facenet_similarity": {
                            "value":       float(display_facenet),
                            "percentage":  f"{display_facenet:.1f}%",
                            "raw_value":   float(raw_facenet),
                            "description": "Facenet512 model similarity",
                            "weight":      "Considered in Max Fusion"
                        },
                        "geometric_similarity": {
                            "value":       float(display_geometric),
                            "percentage":  f"{display_geometric:.1f}%",
                            "raw_value":   float(raw_geometric),
                            "description": "Facial structure and landmark similarity",
                            "weight":      "25%"
                        },
                        "statistical_position": {
                            "z_score":     float(z_score),
                            "description": f"{'Above' if z_score > 0 else 'Below'} average by {abs(z_score):.2f} standard deviations"
                        }
                    }

                    if 'region_similarity' in match:
                        match['explanation']['region_similarity'] = {
                            "value":       float(match['region_similarity']),
                            "percentage":  f"{match['region_similarity']:.1f}%",
                            "raw_value":   float(match['raw_region_similarity']),
                            "description": "Multi-region similarity (eyes, nose, mouth)",
                            "weight":      "15%"
                        }
            
            top_n = int(request.form.get('top_n', 5))
            top_n = min(max(top_n, 1), 10)

            top_matches = matches[:top_n]

            for idx, match in enumerate(top_matches, 1):
                match['rank'] = idx
                match['database_mean_similarity']  = float(mean_similarity)
                match['similarity_above_average']  = bool(match.get('statistical_analysis', {}).get('above_average', False))
                match['similarity_z_score']        = float(match.get('statistical_analysis', {}).get('z_score', 0.0))

                z_score = match.get('statistical_analysis', {}).get('z_score', 0.0)
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
            if len(matches) > 0:
                print(f"  Database mean similarity: {mean_similarity:.4f} ({mean_similarity*100:.1f}%)")
                print(f"  Candidates above average: {sum(1 for m in matches if m.get('statistical_analysis', {}).get('above_average', False))}")

            print(f"[API] Returning response with {len(top_matches)} results", flush=True)
            
            response_payload = {
                "matches":      top_matches,
                "total_matches": len(matches),
                "showing_top":  len(top_matches),
                "threshold_used": float(threshold),
                "distribution_analysis": distribution_stats,
                "database_comparison": {
                    "mean_similarity":    float(mean_similarity),
                    "std_deviation":      float(std_similarity),
                    "candidates_above_average": sum(
                        1 for m in matches
                        if m.get('statistical_analysis', {}).get('above_average', False)
                    ),
                    "candidates_significantly_above_average": sum(
                        1 for m in matches
                        if m.get('statistical_analysis', {}).get('z_score', 0.0) >= 1.5
                    ),
                    "total_candidates_searched": len(search_results),
                    "interpretation": "Candidates with z-score >= 1.5 are significantly above average and should be prioritized for investigation."
                },
                "two_stage_pipeline": {
                    "stage1_method":    "FAISS-accelerated fast retrieval" if use_faiss else "Linear search with cached embeddings",
                    "stage1_candidates": len(search_results),
                    "stage1_top_k":     len(top_k_candidates),
                    "stage2_method":    "Detailed re-ranking with geometric and region similarities",
                    "stage2_formula":   "60% embedding + 25% geometric + 15% region",
                    "reranking_applied": True,
                    "faiss_enabled":    bool(use_faiss),
                    "faiss_available":  bool(is_faiss_index_ready())
                },
                "search_method": (
                    "Two-Stage Top-K Re-Ranking with FAISS" if use_faiss
                    else "Two-Stage Top-K Re-Ranking (Linear Search fallback)"
                ),
                "forensic_note": (
                    "Cross-domain sketch-to-photo matching. Use as investigation leads, "
                    "not absolute identification. Manual verification required."
                ),
                "interpretation_guide": {
                    "HIGH":   "Score > 0.4 — Strong candidate, priority investigation",
                    "MEDIUM": "Score 0.25–0.4 — Possible match, worth investigating",
                    "LOW":    "Score < 0.25 — Unlikely match, lower priority"
                }
            }

            print("[API] RESPONSE SENT SUCCESSFULLY", flush=True)
            return jsonify(response_payload), 200

        finally:
            # Clean up sketch temp file
            cleanup_temp_file(sketch_path)

    except Exception as e:
        print(f"[API] /api/criminals/search UNHANDLED ERROR:\n{traceback.format_exc()}", flush=True)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================================================
# FACE COMPARISON ENDPOINT
# ============================================================================

@app.route('/api/compare', methods=['POST'])
def compare_faces():
    """Compare two face images (sketch vs photo) - Forensic comparison"""
    # ── Model readiness guard ─────────────────────────────────────────────
    # Check file-based flag — visible across all Gunicorn worker processes.
    if not _is_startup_complete():
        print(f"[compare_faces] Startup flag missing — system not ready.", flush=True)
        print(f"[compare_faces] MODEL_INITIALIZED = {is_models_initialized()}", flush=True)
        print(f"[compare_faces] Flag path: {STARTUP_FLAG_PATH}", flush=True)
        return jsonify({
            "error": "Face recognition models are still initializing. Please retry in a moment."
        }), 503

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
                "insightface_similarity": result.get('insightface_similarity', 0.0),
                "facenet_similarity": result.get('facenet_similarity', 0.0),
                "geometric_similarity": result.get('geometric_similarity', 0.0),
                "multi_region_similarity": result.get('multi_region_similarity', 0.0),
                "raw_final_embedding_similarity": result.get('raw_final_embedding_similarity', 0.0),
                "raw_embedding_fusion": result.get('raw_embedding_fusion', 0.0),
                "raw_insightface_similarity": result.get('raw_insightface_similarity', 0.0),
                "raw_facenet_similarity": result.get('raw_facenet_similarity', 0.0),
                "raw_geometric_similarity": result.get('raw_geometric_similarity', 0.0),
                "raw_multi_region_similarity": result.get('raw_multi_region_similarity', 0.0),
                "eyes_similarity": result.get('region_details', {}).get('eyes') or result.get('eyes_similarity', 0.0),
                "nose_similarity": result.get('region_details', {}).get('nose') or result.get('nose_similarity', 0.0),
                "mouth_similarity": result.get('region_details', {}).get('mouth') or result.get('mouth_similarity', 0.0),
                "full_face_similarity": result.get('region_details', {}).get('full_face') or result.get('full_face_similarity', 0.0),
                "region_details": result.get('region_details'),
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
    ready = _is_startup_complete()
    return jsonify({
        "status": "healthy" if ready else "initializing",
        "startup_complete": ready,
        "model_initialized": is_models_initialized(),
        "faiss_ready": is_faiss_index_ready(),
        "embedding_cache_size": get_cache_size(),
        "service": "FaceFind Forensics API v2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(line_buffering=True)

    port = int(os.environ.get('PORT', '5001'))
    print(f"\n[OK] Server ready on http://localhost:{port}")
    print("=" * 60 + "\n")
    sys.stdout.flush()

    # Run with debug=False to prevent Werkzeug reloader child-process deadlocks with TensorFlow/Keras
    app.run(debug=False, host='0.0.0.0', port=port, threaded=True)

