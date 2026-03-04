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
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ============================================================================
# TEMP UPLOADS FOLDER SETUP
# ============================================================================

# Create dedicated temp_uploads folder in project directory
TEMP_UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'temp_uploads')
os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)

def generate_temp_filepath(original_filename: str = None, prefix: str = '') -> str:
    """
    Generate a unique filepath in temp_uploads folder
    
    Args:
        original_filename: Original filename (optional, for extension)
        prefix: Prefix for the filename (e.g., 'sketch', 'photo', 'preprocessed')
    
    Returns:
        str: Full path to temp file
    """
    unique_id = str(uuid.uuid4())
    
    # Extract extension from original filename if provided
    if original_filename:
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.jpg'
    else:
        ext = '.jpg'
    
    # Build filename
    if prefix:
        filename = f"{prefix}_{unique_id}{ext}"
    else:
        filename = f"{unique_id}{ext}"
    
    return os.path.join(TEMP_UPLOADS_DIR, filename)


def cleanup_temp_file(filepath: str):
    """
    Safely delete a temp file
    
    Args:
        filepath: Path to file to delete
    """
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"[WARNING] Failed to cleanup temp file {filepath}: {e}")

# Create database tables
create_tables()

# ============================================================================
# GLOBAL VARIABLES FOR FACE COMPARISON OPTIMIZATION
# ============================================================================

MODEL_INITIALIZED = False
RESULT_CACHE = {}
CACHE_MAX_SIZE = 100

# Precomputed embeddings cache
EMBEDDING_CACHE = {}  # {criminal_id: embedding_vector}
EMBEDDING_VERSION = "arcface_v1"  # Track embedding model version


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
        dummy_path = generate_temp_filepath(prefix='dummy_init')
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
            cleanup_temp_file(dummy_path)
        
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


def extract_embedding(image_path: str) -> np.ndarray:
    """
    Extract ArcFace embedding from image
    
    Returns:
        np.ndarray: 512-dimensional embedding vector, or None if extraction fails
    """
    try:
        # Validate input file exists
        if not os.path.exists(image_path):
            print(f"[ERROR] Input image does not exist: {image_path}")
            return None
        
        # Validate file can be read by cv2
        test_img = cv2.imread(image_path)
        if test_img is None:
            print(f"[ERROR] cv2.imread() failed - image is corrupted or invalid: {image_path}")
            return None
        
        # Preprocess image
        processed_path = preprocess_for_cross_domain_matching(image_path, is_sketch=False)
        
        # Validate preprocessing succeeded
        if processed_path is None:
            print(f"[ERROR] Preprocessing failed for: {image_path}")
            return None
        
        # Validate preprocessed file exists
        if not os.path.exists(processed_path):
            print(f"[ERROR] Preprocessed file does not exist: {processed_path}")
            return None
        
        # Validate preprocessed file can be read
        test_processed = cv2.imread(processed_path)
        if test_processed is None:
            print(f"[ERROR] cv2.imread() failed on preprocessed file: {processed_path}")
            cleanup_temp_file(processed_path)
            return None
        
        # Extract embedding
        result = DeepFace.represent(
            img_path=processed_path,
            model_name='ArcFace',
            enforce_detection=True,
            align=True,
            detector_backend='opencv'
        )
        
        embedding = np.array(result[0]['embedding'])
        
        # Cleanup
        if processed_path != image_path:
            cleanup_temp_file(processed_path)
        
        return embedding
        
    except Exception as e:
        print(f"[ERROR] Embedding extraction failed: {e}")
        traceback.print_exc()
        return None


def compute_geometric_similarity(img1_path: str, img2_path: str) -> float:
    """
    Lightweight geometric scoring based on facial landmarks
    
    Returns:
        float: Geometric similarity score (0-1)
    """
    try:
        # Read images
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        
        if img1 is None or img2 is None:
            return 0.5  # Neutral score if can't read
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Detect faces using Haar Cascade (lightweight)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        faces1 = face_cascade.detectMultiScale(gray1, 1.1, 4)
        faces2 = face_cascade.detectMultiScale(gray2, 1.1, 4)
        
        if len(faces1) == 0 or len(faces2) == 0:
            return 0.5  # Neutral score if no face detected
        
        # Get largest face (assume it's the main face)
        face1 = max(faces1, key=lambda f: f[2] * f[3])  # (x, y, w, h)
        face2 = max(faces2, key=lambda f: f[2] * f[3])
        
        # Extract face regions
        x1, y1, w1, h1 = face1
        x2, y2, w2, h2 = face2
        
        # Compute aspect ratio similarity
        aspect1 = w1 / h1 if h1 > 0 else 1.0
        aspect2 = w2 / h2 if h2 > 0 else 1.0
        aspect_similarity = 1.0 - abs(aspect1 - aspect2) / max(aspect1, aspect2)
        
        # Compute size similarity (normalized)
        size1 = w1 * h1
        size2 = w2 * h2
        size_similarity = min(size1, size2) / max(size1, size2) if max(size1, size2) > 0 else 0.5
        
        # Compute position similarity (center of face)
        center1_x = x1 + w1 / 2
        center1_y = y1 + h1 / 2
        center2_x = x2 + w2 / 2
        center2_y = y2 + h2 / 2
        
        # Normalize by image size
        h_img1, w_img1 = gray1.shape
        h_img2, w_img2 = gray2.shape
        
        center1_x_norm = center1_x / w_img1 if w_img1 > 0 else 0.5
        center1_y_norm = center1_y / h_img1 if h_img1 > 0 else 0.5
        center2_x_norm = center2_x / w_img2 if w_img2 > 0 else 0.5
        center2_y_norm = center2_y / h_img2 if h_img2 > 0 else 0.5
        
        position_similarity = 1.0 - (abs(center1_x_norm - center2_x_norm) + abs(center1_y_norm - center2_y_norm)) / 2.0
        
        # Weighted combination
        geometric_score = (
            0.4 * aspect_similarity +
            0.3 * size_similarity +
            0.3 * position_similarity
        )
        
        return max(0.0, min(1.0, geometric_score))
        
    except Exception as e:
        print(f"[WARNING] Geometric scoring failed: {e}")
        return 0.5  # Neutral score on error


def precompute_database_embeddings():
    """
    Precompute and cache embeddings for all criminals in database
    Called at startup
    """
    global EMBEDDING_CACHE
    
    print("\n" + "="*60)
    print("PRECOMPUTING DATABASE EMBEDDINGS")
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
                    # Load from database
                    embedding = np.array(criminal.face_embedding)
                    EMBEDDING_CACHE[criminal.criminal_id] = embedding
                    cached_count += 1
                    print(f"  [OK] Loaded cached embedding for {criminal.criminal_id}")
                else:
                    # Compute new embedding
                    print(f"  Computing embedding for {criminal.criminal_id}...")
                    
                    # Validate photo data exists
                    if not criminal.photo_data:
                        print(f"  [ERROR] No photo data for {criminal.criminal_id}")
                        failed_count += 1
                        continue
                    
                    # Save photo to temp_uploads folder
                    temp_path = generate_temp_filepath(original_filename=criminal.photo_filename or 'criminal.jpg', prefix='criminal')
                    try:
                        with open(temp_path, 'wb') as f:
                            f.write(criminal.photo_data)
                        
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
                        
                        # Extract embedding
                        embedding = extract_embedding(temp_path)
                        
                        if embedding is not None:
                            # Store in cache
                            EMBEDDING_CACHE[criminal.criminal_id] = embedding
                            
                            # Update database
                            criminal.face_embedding = embedding.tolist()
                            criminal.embedding_version = EMBEDDING_VERSION
                            db.commit()
                            
                            updated_count += 1
                            print(f"  [OK] Computed and stored embedding for {criminal.criminal_id}")
                        else:
                            print(f"  [ERROR] Failed to compute embedding for {criminal.criminal_id}")
                            failed_count += 1
                    
                    finally:
                        # Cleanup temp file
                        cleanup_temp_file(temp_path)
                        
            except Exception as e:
                print(f"  [ERROR] Error processing {criminal.criminal_id}: {e}")
                failed_count += 1
                continue
        
        print(f"\n[SUMMARY]")
        print(f"  Cached embeddings: {cached_count}")
        print(f"  Newly computed: {updated_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Total in cache: {len(EMBEDDING_CACHE)}")
        print("="*60 + "\n")
        
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
            print("  [STEP 2] Photo -> Edge extraction (sketch-like)")
            
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
            print("  [STEP 2] Sketch -> Minimal enhancement")
            
            # Just apply histogram equalization for consistent brightness
            result = cv2.equalizeHist(gray)
        
        # Convert back to BGR for DeepFace compatibility
        result_bgr = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        
        # Save to temp_uploads folder with deterministic filename
        file_hash = hashlib.md5(image_path.encode()).hexdigest()[:8]
        mode = "sketch" if is_sketch else "photo"
        processed_path = generate_temp_filepath(prefix=f'edge_{mode}_{file_hash}')
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

def preprocess_for_cross_domain_matching(image_path: str, is_sketch: bool = False, 
                                         canny_threshold: tuple = None) -> str:
    """
    EDGE-BASED: Preprocessing to reduce sketch-to-photo domain gap
    
    **USAGE:** Production endpoints (/api/compare, /api/criminals/search)
    **CALLED BY:** forensic_face_comparison()
    
    APPROACH:
    - For PHOTOS: Convert to grayscale → Apply Canny edge detection → Create sketch-like representation
    - For SKETCHES: Convert to grayscale only → Keep sketch intact (no edge detection)
    - Both: Convert to 3-channel BGR → Resize to 112x112 (ArcFace native size)
    
    This approach converts photos into edge-based representations to match sketches,
    while keeping original sketches intact, reducing the domain gap.
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
        canny_threshold: Tuple of (threshold1, threshold2) for Canny edge detection
                        If None, uses default (50, 150)
    
    DETERMINISTIC: All operations use fixed parameters for consistent results
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"  [ERROR] Failed to read image: {image_path}")
            return None
        
        # Use default thresholds if not specified
        if canny_threshold is None:
            canny_threshold = (50, 150)
        
        print(f"  [PREPROCESSING] {'Sketch' if is_sketch else 'Photo'} - Input size: {img.shape}")
        
        # STEP 1: Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        print(f"    [OK] Step 1: Converted to grayscale")
        
        if is_sketch:
            # SKETCH: Keep intact, no edge detection
            print(f"    [OK] Step 2: Sketch - keeping original (no edge detection)")
            processed = gray
        else:
            # PHOTO: Apply Canny edge detection to create sketch-like representation
            edges = cv2.Canny(gray, threshold1=canny_threshold[0], threshold2=canny_threshold[1])
            print(f"    [OK] Step 2: Photo - applied Canny edge detection with thresholds {canny_threshold}")
            processed = edges
        
        # STEP 3: Convert to 3-channel BGR (ArcFace expects 3 channels)
        bgr = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        print(f"    [OK] Step 3: Converted to 3-channel BGR")
        
        # STEP 4: Resize to 112x112 (ArcFace native size)
        target_size = 112
        resized = cv2.resize(bgr, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
        print(f"    [OK] Step 4: Resized to {target_size}x{target_size} (ArcFace native size)")
        print(f"    [OK] Final output: {'Sketch (intact)' if is_sketch else 'Edge-based'} representation, size {resized.shape} (ready for ArcFace)")
        
        # Save preprocessed image to temp_uploads folder
        file_hash = hashlib.md5(image_path.encode()).hexdigest()[:8]
        mode = "sketch" if is_sketch else "photo"
        threshold_str = f"{canny_threshold[0]}_{canny_threshold[1]}"
        processed_path = generate_temp_filepath(prefix=f'edge_preprocessed_{mode}_{threshold_str}_{file_hash}')
        
        # Validate cv2.imwrite() succeeds
        write_success = cv2.imwrite(processed_path, resized, [cv2.IMWRITE_JPEG_QUALITY, 95])
        if not write_success:
            print(f"  [ERROR] Failed to write preprocessed image to: {processed_path}")
            return None
        
        # Validate file exists
        if not os.path.exists(processed_path):
            print(f"  [ERROR] Preprocessed file does not exist: {processed_path}")
            return None
        
        # Validate file can be read by cv2
        test_img = cv2.imread(processed_path)
        if test_img is None:
            print(f"  [ERROR] cv2.imread() failed on preprocessed file: {processed_path}")
            cleanup_temp_file(processed_path)
            return None
        
        print(f"  [PREPROCESSING] Complete - saved to: {processed_path}")
        return processed_path
        
    except Exception as e:
        print(f"  [PREPROCESSING ERROR] {e}")
        traceback.print_exc()
        return None


def preprocess_with_adaptive_canny(image_path: str, is_sketch: bool = False, 
                                   reference_embedding: np.ndarray = None) -> tuple:
    """
    ADAPTIVE: Test multiple Canny thresholds and select the best one
    
    **USAGE:** Production endpoints when adaptive threshold selection is needed
    
    Tests multiple Canny threshold combinations:
    - (30, 120) - More edges (sensitive)
    - (50, 150) - Balanced (default)
    - (70, 200) - Fewer edges (conservative)
    
    If reference_embedding is provided, selects the threshold that produces
    the highest embedding similarity. Otherwise, returns default (50, 150).
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
        reference_embedding: Reference embedding to compare against (optional)
    
    Returns:
        tuple: (best_preprocessed_path, best_threshold, threshold_results)
    """
    # Threshold combinations to test
    threshold_combinations = [
        (30, 120),  # More edges (sensitive)
        (50, 150),  # Balanced (default)
        (70, 200)   # Fewer edges (conservative)
    ]
    
    print(f"\n[ADAPTIVE CANNY] Testing {len(threshold_combinations)} threshold combinations...")
    
    # If no reference embedding, just use default
    if reference_embedding is None or is_sketch:
        print(f"  No reference embedding or is sketch - using default (50, 150)")
        best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
        return best_path, (50, 150), None
    
    threshold_results = []
    temp_paths = []
    
    try:
        # Test each threshold combination
        for threshold in threshold_combinations:
            print(f"\n  Testing threshold {threshold}...")
            
            # Preprocess with this threshold
            processed_path = preprocess_for_cross_domain_matching(
                image_path, 
                is_sketch=is_sketch, 
                canny_threshold=threshold
            )
            
            if processed_path is None:
                print(f"    [ERROR] Preprocessing failed for threshold {threshold}")
                continue
            
            temp_paths.append(processed_path)
            
            # Extract embedding
            try:
                result = DeepFace.represent(
                    img_path=processed_path,
                    model_name='ArcFace',
                    enforce_detection=True,
                    align=True,
                    detector_backend='opencv'
                )
                embedding = np.array(result[0]['embedding'])
                
                # Compute similarity with reference embedding
                dot_product = np.dot(embedding, reference_embedding)
                norm1 = np.linalg.norm(embedding)
                norm2 = np.linalg.norm(reference_embedding)
                similarity = dot_product / (norm1 * norm2)
                
                threshold_results.append({
                    'threshold': threshold,
                    'similarity': float(similarity),
                    'path': processed_path
                })
                
                print(f"    Similarity: {similarity:.4f} ({similarity*100:.1f}%)")
                
            except Exception as e:
                print(f"    [ERROR] Embedding extraction failed: {e}")
                continue
        
        # Select best threshold based on highest similarity
        if len(threshold_results) > 0:
            best_result = max(threshold_results, key=lambda x: x['similarity'])
            best_threshold = best_result['threshold']
            best_path = best_result['path']
            best_similarity = best_result['similarity']
            
            print(f"\n  [BEST THRESHOLD] {best_threshold} with similarity {best_similarity:.4f} ({best_similarity*100:.1f}%)")
            
            # Cleanup non-selected preprocessed images
            for result in threshold_results:
                if result['path'] != best_path:
                    cleanup_temp_file(result['path'])
            
            return best_path, best_threshold, threshold_results
        else:
            print(f"  [ERROR] All thresholds failed, using default")
            best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
            return best_path, (50, 150), None
            
    except Exception as e:
        print(f"  [ADAPTIVE CANNY ERROR] {e}")
        traceback.print_exc()
        
        # Cleanup all temp files
        for path in temp_paths:
            cleanup_temp_file(path)
        
        # Fallback to default
        best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
        return best_path, (50, 150), None


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

def forensic_face_comparison(sketch_path: str, photo_path: str, use_cache: bool = True, 
                            use_adaptive_canny: bool = True) -> dict:
    """
    HYBRID: Forensic-grade face comparison with hybrid scoring
    
    **USAGE:** Production endpoints (/api/compare, /api/criminals/search)
    **PREPROCESSING:** Uses preprocess_for_cross_domain_matching()
    
    HYBRID SCORING:
    - 80% ArcFace embedding similarity (deep features)
    - 20% Geometric similarity (facial structure)
    - Final score = 0.8 * embedding + 0.2 * geometry
    
    ADAPTIVE CANNY:
    - Tests multiple Canny thresholds: (30,120), (50,150), (70,200)
    - Automatically selects the threshold with highest embedding similarity
    - Only applied for cross-domain (sketch-to-photo) comparisons
    
    IMPROVEMENTS:
    - Uses DeepFace.represent() for direct embedding extraction
    - Manual cosine similarity computation
    - Lightweight geometric scoring component
    - Ranked similarity categories (HIGH/MEDIUM/LOW)
    - No binary match logic
    - Deterministic results
    - Enhanced debug logging
    
    Args:
        sketch_path: Path to sketch/query image
        photo_path: Path to photo/reference image
        use_cache: Whether to use result caching
        use_adaptive_canny: Whether to use adaptive Canny threshold selection (default: True)
    
    DETERMINISTIC: All operations use fixed parameters for consistent results
    """
    global RESULT_CACHE
    
    # Ensure models are initialized
    initialize_models()
    
    start_time = time.time()
    print(f"\n{'='*60}")
    print("FORENSIC FACE COMPARISON - HYBRID SCORING")
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
            cache_key = f"{hash1}_{hash2}_{is_img1_sketch}_{is_img2_sketch}_hybrid_v1"
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
        # ADAPTIVE CANNY: For cross-domain comparisons, use adaptive threshold selection
        # This tests multiple Canny thresholds and selects the best one
        use_adaptive = is_cross_domain and use_adaptive_canny
        
        if use_adaptive:
            print(f"[PREPROCESSING] Using ADAPTIVE Canny threshold selection...")
            
            # First, preprocess the sketch (no adaptive needed for sketches)
            processed_img1 = preprocess_for_cross_domain_matching(sketch_path, is_sketch=is_img1_sketch)
            
            if processed_img1 is None:
                return {
                    'distance': 1.0,
                    'similarity': 0.0,
                    'embedding_similarity': 0.0,
                    'geometric_similarity': 0.0,
                    'similarity_category': 'ERROR',
                    'confidence_level': 'error',
                    'confidence_score': 0.0,
                    'match_quality': 'Preprocessing failed for image 1',
                    'is_cross_domain': is_cross_domain,
                    'comparison_type': 'error',
                    'model_used': 'failed',
                    'metric_used': 'none',
                    'embedding_length': 0,
                    'embedding_norm_1': 0.0,
                    'embedding_norm_2': 0.0,
                    'processing_time': round(time.time() - start_time, 3),
                    'error': 'Preprocessing failed for image 1',
                    'from_cache': False,
                    'forensic_note': 'Preprocessing failed - unable to process image 1.'
                }
            
            # Extract sketch embedding (reference for adaptive selection)
            print(f"  Extracting reference embedding from sketch...")
            embedding1_result = DeepFace.represent(
                img_path=processed_img1,
                model_name='ArcFace',
                enforce_detection=True,
                align=True,
                detector_backend='opencv'
            )
            embedding1 = np.array(embedding1_result[0]['embedding'])
            
            # Use adaptive Canny for the photo
            processed_img2, best_threshold, threshold_results = preprocess_with_adaptive_canny(
                photo_path, 
                is_sketch=is_img2_sketch,
                reference_embedding=embedding1
            )
            
            if processed_img2 is None:
                return {
                    'distance': 1.0,
                    'similarity': 0.0,
                    'embedding_similarity': 0.0,
                    'geometric_similarity': 0.0,
                    'similarity_category': 'ERROR',
                    'confidence_level': 'error',
                    'confidence_score': 0.0,
                    'match_quality': 'Adaptive preprocessing failed for image 2',
                    'is_cross_domain': is_cross_domain,
                    'comparison_type': 'error',
                    'model_used': 'failed',
                    'metric_used': 'none',
                    'embedding_length': 0,
                    'embedding_norm_1': 0.0,
                    'embedding_norm_2': 0.0,
                    'processing_time': round(time.time() - start_time, 3),
                    'error': 'Adaptive preprocessing failed for image 2',
                    'from_cache': False,
                    'forensic_note': 'Adaptive preprocessing failed - unable to process image 2.'
                }
            
            # Extract embedding for image 2 (already done in adaptive selection, but re-extract for consistency)
            print(f"  Extracting final embedding 2 with best threshold {best_threshold}...")
            embedding2_result = DeepFace.represent(
                img_path=processed_img2,
                model_name='ArcFace',
                enforce_detection=True,
                align=True,
                detector_backend='opencv'
            )
            embedding2 = np.array(embedding2_result[0]['embedding'])
            
            adaptive_info = {
                'used': True,
                'best_threshold': best_threshold,
                'tested_thresholds': [r['threshold'] for r in threshold_results] if threshold_results else [],
                'threshold_similarities': {str(r['threshold']): r['similarity'] for r in threshold_results} if threshold_results else {}
            }
            
        else:
            # Standard preprocessing without adaptive selection
            print(f"[PREPROCESSING] Applying standard preprocessing to both images...")
            processed_img1 = preprocess_for_cross_domain_matching(sketch_path, is_sketch=is_img1_sketch)
            processed_img2 = preprocess_for_cross_domain_matching(photo_path, is_sketch=is_img2_sketch)
            
            # Validate preprocessing succeeded
            if processed_img1 is None:
                return {
                    'distance': 1.0,
                    'similarity': 0.0,
                    'embedding_similarity': 0.0,
                    'geometric_similarity': 0.0,
                    'similarity_category': 'ERROR',
                    'confidence_level': 'error',
                    'confidence_score': 0.0,
                    'match_quality': 'Preprocessing failed for image 1',
                    'is_cross_domain': is_cross_domain,
                    'comparison_type': 'error',
                    'model_used': 'failed',
                    'metric_used': 'none',
                    'embedding_length': 0,
                    'embedding_norm_1': 0.0,
                    'embedding_norm_2': 0.0,
                    'processing_time': round(time.time() - start_time, 3),
                    'error': 'Preprocessing failed for image 1',
                    'from_cache': False,
                    'forensic_note': 'Preprocessing failed - unable to process image 1.'
                }
            
            if processed_img2 is None:
                return {
                    'distance': 1.0,
                    'similarity': 0.0,
                    'embedding_similarity': 0.0,
                    'geometric_similarity': 0.0,
                    'similarity_category': 'ERROR',
                    'confidence_level': 'error',
                    'confidence_score': 0.0,
                    'match_quality': 'Preprocessing failed for image 2',
                    'is_cross_domain': is_cross_domain,
                    'comparison_type': 'error',
                    'model_used': 'failed',
                    'metric_used': 'none',
                    'embedding_length': 0,
                    'embedding_norm_1': 0.0,
                    'embedding_norm_2': 0.0,
                    'processing_time': round(time.time() - start_time, 3),
                    'error': 'Preprocessing failed for image 2',
                    'from_cache': False,
                    'forensic_note': 'Preprocessing failed - unable to process image 2.'
                }
            
            # Validate preprocessed files exist
            if not os.path.exists(processed_img1):
                return {
                    'distance': 1.0,
                    'similarity': 0.0,
                    'embedding_similarity': 0.0,
                    'geometric_similarity': 0.0,
                    'similarity_category': 'ERROR',
                    'confidence_level': 'error',
                    'confidence_score': 0.0,
                    'match_quality': 'Preprocessed file 1 does not exist',
                    'is_cross_domain': is_cross_domain,
                    'comparison_type': 'error',
                    'model_used': 'failed',
                    'metric_used': 'none',
                    'embedding_length': 0,
                    'embedding_norm_1': 0.0,
                    'embedding_norm_2': 0.0,
                    'processing_time': round(time.time() - start_time, 3),
                    'error': 'Preprocessed file 1 does not exist',
                    'from_cache': False,
                    'forensic_note': 'File validation failed.'
                }
            
            if not os.path.exists(processed_img2):
                return {
                    'distance': 1.0,
                    'similarity': 0.0,
                    'embedding_similarity': 0.0,
                    'geometric_similarity': 0.0,
                    'similarity_category': 'ERROR',
                    'confidence_level': 'error',
                    'confidence_score': 0.0,
                    'match_quality': 'Preprocessed file 2 does not exist',
                    'is_cross_domain': is_cross_domain,
                    'comparison_type': 'error',
                    'model_used': 'failed',
                    'metric_used': 'none',
                    'embedding_length': 0,
                    'embedding_norm_1': 0.0,
                    'embedding_norm_2': 0.0,
                    'processing_time': round(time.time() - start_time, 3),
                    'error': 'Preprocessed file 2 does not exist',
                    'from_cache': False,
                    'forensic_note': 'File validation failed.'
                }
            
            # Extract embeddings using DeepFace.represent()
            print(f"\n[EMBEDDING EXTRACTION] Extracting ArcFace embeddings...")
            
            # Extract embedding for image 1
            print(f"  Extracting embedding 1...")
            embedding1_result = DeepFace.represent(
                img_path=processed_img1,
                model_name='ArcFace',
                enforce_detection=True,  # Enable face detection
                align=True,              # Enable face alignment
                detector_backend='opencv'
            )
            embedding1 = np.array(embedding1_result[0]['embedding'])
            
            # Extract embedding for image 2
            print(f"  Extracting embedding 2...")
            embedding2_result = DeepFace.represent(
                img_path=processed_img2,
                model_name='ArcFace',
                enforce_detection=True,  # Enable face detection
                align=True,              # Enable face alignment
                detector_backend='opencv'
            )
            embedding2 = np.array(embedding2_result[0]['embedding'])
            
            adaptive_info = {'used': False}
        
        # Log embedding details
        print(f"\n[EMBEDDING DETAILS]")
        print(f"  Embedding 1 length: {len(embedding1)}")
        print(f"  Embedding 2 length: {len(embedding2)}")
        print(f"  Embedding 1 norm (L2): {np.linalg.norm(embedding1):.6f}")
        print(f"  Embedding 2 norm (L2): {np.linalg.norm(embedding2):.6f}")
        
        # Compute cosine similarity manually
        print(f"\n[EMBEDDING SIMILARITY]")
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        # Cosine similarity = dot(A, B) / (||A|| * ||B||)
        embedding_similarity = dot_product / (norm1 * norm2)
        
        print(f"  Dot product: {dot_product:.6f}")
        print(f"  Norm 1 x Norm 2: {(norm1 * norm2):.6f}")
        print(f"  Embedding similarity (cosine): {embedding_similarity:.6f} ({embedding_similarity*100:.2f}%)")
        
        # Compute geometric similarity
        print(f"\n[GEOMETRIC SIMILARITY]")
        geometric_similarity = compute_geometric_similarity(sketch_path, photo_path)
        print(f"  Geometric similarity: {geometric_similarity:.6f} ({geometric_similarity*100:.2f}%)")
        
        # Hybrid score: 80% embedding + 20% geometry
        print(f"\n[HYBRID SCORING]")
        hybrid_similarity = 0.8 * embedding_similarity + 0.2 * geometric_similarity
        hybrid_distance = 1.0 - hybrid_similarity
        
        print(f"  Embedding weight: 80%")
        print(f"  Geometric weight: 20%")
        print(f"  Hybrid similarity: {hybrid_similarity:.6f} ({hybrid_similarity*100:.2f}%)")
        print(f"  Hybrid distance: {hybrid_distance:.6f}")
        
        # Determine similarity category based on hybrid similarity
        print(f"\n[ANALYSIS]")
        print(f"  Comparison type: {comparison_type}")
        print(f"  Final hybrid similarity: {hybrid_similarity:.6f} ({hybrid_similarity*100:.2f}%)")
        
        if is_cross_domain:
            # Cross-domain (sketch-to-photo) thresholds
            if hybrid_similarity > 0.60:
                similarity_category = 'HIGH'
                confidence_level = 'high_similarity'
                confidence_score = 85.0
                match_quality = 'High Similarity - Strong candidate for investigation'
            elif hybrid_similarity >= 0.50:
                similarity_category = 'MEDIUM'
                confidence_level = 'medium_similarity'
                confidence_score = 65.0
                match_quality = 'Medium Similarity - Possible match, requires verification'
            else:
                similarity_category = 'LOW'
                confidence_level = 'low_similarity'
                confidence_score = 35.0
                match_quality = 'Low Similarity - Unlikely match'
        else:
            # Same-domain (photo-to-photo) thresholds
            if hybrid_similarity > 0.70:
                similarity_category = 'HIGH'
                confidence_level = 'high_similarity'
                confidence_score = 95.0
                match_quality = 'High Similarity - Strong match'
            elif hybrid_similarity >= 0.60:
                similarity_category = 'MEDIUM'
                confidence_level = 'medium_similarity'
                confidence_score = 80.0
                match_quality = 'Medium Similarity - Good match'
            else:
                similarity_category = 'LOW'
                confidence_level = 'low_similarity'
                confidence_score = 50.0
                match_quality = 'Low Similarity - Weak match'
        
        elapsed_time = time.time() - start_time
        
        print(f"\n[RESULTS]")
        print(f"  Embedding similarity: {embedding_similarity:.4f} ({embedding_similarity*100:.1f}%)")
        print(f"  Geometric similarity: {geometric_similarity:.4f} ({geometric_similarity*100:.1f}%)")
        print(f"  Hybrid similarity: {hybrid_similarity:.4f} ({hybrid_similarity*100:.1f}%)")
        print(f"  Hybrid distance: {hybrid_distance:.4f}")
        print(f"  Similarity category: {similarity_category}")
        print(f"  Confidence level: {confidence_level}")
        print(f"  Confidence score: {confidence_score:.1f}%")
        print(f"  Match quality: {match_quality}")
        print(f"  Processing time: {elapsed_time:.3f}s")
        print(f"{'='*60}\n")
        
        result_dict = {
            'distance': float(hybrid_distance),
            'similarity': float(hybrid_similarity),
            'embedding_similarity': float(embedding_similarity),
            'geometric_similarity': float(geometric_similarity),
            'similarity_category': similarity_category,
            'confidence_level': confidence_level,
            'confidence_score': float(confidence_score),
            'match_quality': match_quality,
            'is_cross_domain': bool(is_cross_domain),
            'comparison_type': comparison_type,
            'model_used': 'ArcFace',
            'metric_used': 'hybrid (80% embedding + 20% geometry)',
            'embedding_length': int(len(embedding1)),
            'embedding_norm_1': float(norm1),
            'embedding_norm_2': float(norm2),
            'processing_time': round(elapsed_time, 3),
            'from_cache': False,
            'adaptive_canny': adaptive_info,
            'forensic_note': 'Hybrid scoring: 80% deep features + 20% geometric. Investigation assistant - not identity confirmation.' if is_cross_domain else 'Hybrid scoring with higher reliability for same-domain comparison.'
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
            'embedding_similarity': 0.0,
            'geometric_similarity': 0.0,
            'similarity_category': 'ERROR',
            'confidence_level': 'error',
            'confidence_score': 0.0,
            'match_quality': 'Comparison failed',
            'is_cross_domain': False,
            'comparison_type': 'error',
            'model_used': 'failed',
            'metric_used': 'none',
            'embedding_length': 0,
            'embedding_norm_1': 0.0,
            'embedding_norm_2': 0.0,
            'processing_time': round(elapsed_time, 3),
            'error': str(e),
            'from_cache': False,
            'forensic_note': 'Comparison failed due to technical error.'
        }
    
    finally:
        # Cleanup processed temporary images
        if processed_img1 and processed_img1 != sketch_path:
            cleanup_temp_file(processed_img1)
        if processed_img2 and processed_img2 != photo_path:
            cleanup_temp_file(processed_img2)


def save_temp_file(file_storage) -> str:
    """
    Save uploaded file to temp_uploads folder
    
    Args:
        file_storage: Flask FileStorage object
    
    Returns:
        str: Path to saved file
    """
    filepath = generate_temp_filepath(original_filename=file_storage.filename, prefix='upload')
    file_storage.save(filepath)
    
    # Validate file was saved
    if not os.path.exists(filepath):
        raise IOError(f"Failed to save uploaded file to: {filepath}")
    
    # Validate file can be read by cv2
    test_img = cv2.imread(filepath)
    if test_img is None:
        cleanup_temp_file(filepath)
        raise IOError(f"Uploaded file is corrupted or invalid format: {file_storage.filename}")
    
    return filepath


def save_bytes_to_temp(data: bytes, original_filename: str) -> str:
    """
    Save bytes data to temp_uploads folder
    
    Args:
        data: Image data as bytes
        original_filename: Original filename (for extension)
    
    Returns:
        str: Path to saved file
    """
    filepath = generate_temp_filepath(original_filename=original_filename, prefix='bytes')
    with open(filepath, 'wb') as f:
        f.write(data)
    
    # Validate file was saved
    if not os.path.exists(filepath):
        raise IOError(f"Failed to save bytes to file: {filepath}")
    
    # Validate file can be read by cv2
    test_img = cv2.imread(filepath)
    if test_img is None:
        cleanup_temp_file(filepath)
        raise IOError(f"Saved bytes data is corrupted or invalid format")
    
    return filepath


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
            # Extract embedding for query sketch ONCE
            print(f"\n[QUERY EMBEDDING] Extracting embedding for sketch...")
            query_embedding = extract_embedding(sketch_path)
            
            if query_embedding is None:
                return jsonify({"error": "Failed to extract embedding from sketch"}), 400
            
            query_norm = np.linalg.norm(query_embedding)
            print(f"  [OK] Query embedding extracted: length={len(query_embedding)}, norm={query_norm:.6f}")
            
            # Compute geometric similarity for query sketch (for hybrid scoring)
            # We'll compute this with each criminal photo
            
            # Get all criminals from database
            db = next(get_db())
            criminals = db.query(Criminal).all()
            print(f"\n[DATABASE SEARCH] Comparing against {len(criminals)} criminals...")
            
            matches = []
            
            # Compare sketch embedding with each precomputed criminal embedding
            for criminal in criminals:
                try:
                    # Check if precomputed embedding exists in cache
                    if criminal.criminal_id in EMBEDDING_CACHE:
                        # Use precomputed embedding (FAST!)
                        criminal_embedding = EMBEDDING_CACHE[criminal.criminal_id]
                        
                        # Compute embedding similarity (cosine)
                        dot_product = np.dot(query_embedding, criminal_embedding)
                        criminal_norm = np.linalg.norm(criminal_embedding)
                        embedding_similarity = dot_product / (query_norm * criminal_norm)
                        
                        # Compute geometric similarity
                        # Save criminal photo to temp file for geometric scoring
                        criminal_photo_path = save_bytes_to_temp(
                            criminal.photo_data,
                            criminal.photo_filename or 'criminal.jpg'
                        )
                        
                        try:
                            geometric_similarity = compute_geometric_similarity(sketch_path, criminal_photo_path)
                        finally:
                            cleanup_temp_file(criminal_photo_path)
                        
                        # Hybrid score: 80% embedding + 20% geometry
                        hybrid_similarity = 0.8 * embedding_similarity + 0.2 * geometric_similarity
                        hybrid_distance = 1.0 - hybrid_similarity
                        
                        # Initial category (will be recalculated after normalization)
                        # These are just placeholders for logging
                        if hybrid_similarity > 0.60:
                            similarity_category = 'HIGH'
                        elif hybrid_similarity >= 0.50:
                            similarity_category = 'MEDIUM'
                        else:
                            similarity_category = 'LOW'
                        
                        print(f"  {criminal.full_name}: hybrid={hybrid_similarity:.4f}, emb={embedding_similarity:.4f}, geo={geometric_similarity:.4f}")
                        
                        # Add to matches (categories will be assigned after normalization)
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
                            "similarity_score": float(hybrid_similarity),
                            "embedding_similarity": float(embedding_similarity),
                            "geometric_similarity": float(geometric_similarity),
                            "distance": float(hybrid_distance),
                            "model_used": 'ArcFace',
                            "metric_used": 'hybrid (80% embedding + 20% geometry)',
                            "is_cross_domain": True
                        })
                    else:
                        # Fallback: embedding not precomputed, skip or compute on-the-fly
                        print(f"  [WARNING] No precomputed embedding for {criminal.criminal_id}, skipping...")
                        continue
                            
                except Exception as e:
                    print(f"  [ERROR] Error comparing with criminal {criminal.id}: {e}")
                    continue
            
            # Sort by similarity score (highest first)
            matches.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # ================================================================
            # SIMILARITY DISTRIBUTION ANALYSIS
            # ================================================================
            # Compute statistical metrics to help investigators understand
            # the distribution of similarities and identify standout candidates
            # ================================================================
            
            distribution_stats = {}
            
            if len(matches) > 0:
                similarities = [m['similarity_score'] for m in matches]
                embedding_sims = [m['embedding_similarity'] for m in matches]
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
                    "mean_embedding": float(np.mean(embedding_sims)),
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
                    
                    # Add detailed explanation for each result
                    match['explanation'] = {
                        "hybrid_score": {
                            "value": float(raw_similarity),
                            "percentage": f"{raw_similarity*100:.1f}%",
                            "description": "Combined score: 80% embedding + 20% geometric"
                        },
                        "embedding_similarity": {
                            "value": float(match['embedding_similarity']),
                            "percentage": f"{match['embedding_similarity']*100:.1f}%",
                            "description": "Deep feature similarity from ArcFace model",
                            "weight": "80%"
                        },
                        "geometric_similarity": {
                            "value": float(match['geometric_similarity']),
                            "percentage": f"{match['geometric_similarity']*100:.1f}%",
                            "description": "Facial structure and landmark similarity",
                            "weight": "20%"
                        },
                        "statistical_position": {
                            "z_score": float(z_score),
                            "description": f"{'Above' if z_score > 0 else 'Below'} average by {abs(z_score):.2f} standard deviations"
                        }
                    }
            
            # Return top 10 matches (or fewer if less available)
            # Allow configurable top_n via query parameter
            top_n = int(request.form.get('top_n', 10))  # Default to 10
            top_n = min(max(top_n, 1), 20)  # Clamp between 1 and 20
            
            top_matches = matches[:top_n]
            
            # Add rank to each match
            for idx, match in enumerate(top_matches, 1):
                match['rank'] = idx
            
            print(f"\n[RESULTS]")
            print(f"  Total matches: {len(matches)}")
            print(f"  Returning top: {len(top_matches)}")
            print(f"  Candidates above average: {sum(1 for m in matches if m['statistical_analysis']['above_average'])}")
            
            for match in top_matches[:5]:  # Print first 5 for brevity
                print(f"  Rank {match['rank']}: {match['criminal']['full_name']}")
                print(f"    Hybrid: {match['similarity_score']*100:.1f}%, "
                      f"Embedding: {match['embedding_similarity']*100:.1f}%, "
                      f"Geometric: {match['geometric_similarity']*100:.1f}%")
                print(f"    Z-score: {match['statistical_analysis']['z_score']:.2f}, "
                      f"Category: {match['similarity_category']}")
            
            if len(top_matches) > 5:
                print(f"  ... and {len(top_matches) - 5} more")
            
            return jsonify({
                "matches": top_matches,
                "total_matches": len(matches),
                "showing_top": len(top_matches),
                "threshold_used": threshold,
                "distribution_analysis": distribution_stats,
                "search_method": "optimized (precomputed embeddings + statistical analysis)",
                "forensic_note": "Results ranked with statistical analysis. Candidates significantly above average are highlighted. Cross-domain sketch-to-photo matching has inherent limitations. Use as investigation leads, not absolute identification. Manual verification required.",
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
    
    app.run(debug=True, host='0.0.0.0', port=port)

