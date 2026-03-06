"""
Service for generating face embeddings
Handles embedding extraction with TTA, dual model fusion, and normalization
"""
import os
import cv2
import numpy as np
import uuid
import traceback
from deepface import DeepFace
from deepface.modules import detection

# Import from sibling modules
from models.arcface_model import (
    initialize_arcface_model,
    extract_arcface_embedding,
    normalize_embedding as normalize_arcface_embedding,
    is_arcface_initialized
)
from models.facenet_model import (
    initialize_facenet_model,
    extract_facenet_embedding,
    normalize_embedding as normalize_facenet_embedding,
    is_facenet_initialized
)
from utils.file_utils import generate_temp_filepath, cleanup_temp_file
from utils.similarity_utils import cosine_similarity


# Global model initialization state
MODEL_INITIALIZED = False


def initialize_models():
    """
    Pre-load DeepFace models (ArcFace + Facenet) to ensure consistent performance
    
    Uses direct model loading for efficiency (no dummy image needed).
    
    Returns:
        bool: True if successful, False otherwise
    """
    global MODEL_INITIALIZED
    
    if MODEL_INITIALIZED:
        return True
    
    print("=" * 60)
    print("Initializing DeepFace models for consistent results...")
    print("=" * 60)
    
    try:
        # Pre-load ArcFace model (direct loading, no dummy image needed)
        initialize_arcface_model()
        
        # Pre-load Facenet512 model (direct loading, no dummy image needed)
        initialize_facenet_model()
        
        MODEL_INITIALIZED = True
        print("=" * 60)
        print("Model initialization complete!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"Model initialization error: {e}")
        traceback.print_exc()
        MODEL_INITIALIZED = True  # Continue anyway
        return False


def is_models_initialized() -> bool:
    """
    Check if models are initialized
    
    Returns:
        bool: True if initialized, False otherwise
    """
    return MODEL_INITIALIZED


def generate_tta_augmentations(aligned_face: np.ndarray) -> list:
    """
    Generate Test-Time Augmentation (TTA) versions of aligned face for robust embedding extraction.
    
    OPTIMIZED: Reduced from 5 to 3 augmentations for faster processing while maintaining accuracy.
    
    Augmentations:
    1. Original face
    2. Horizontal flip
    3. Rotation +5 degrees
    
    Args:
        aligned_face: Aligned face image (numpy array)
    
    Returns:
        list: List of augmented face images (3 augmentations)
    """
    try:
        augmented_faces = []
        h, w = aligned_face.shape[:2]
        
        # 1. Original face
        augmented_faces.append(aligned_face.copy())
        
        # 2. Horizontal flip
        flipped = cv2.flip(aligned_face, 1)
        augmented_faces.append(flipped)
        
        # 3. Rotation +5 degrees
        center = (w // 2, h // 2)
        rotation_matrix_pos = cv2.getRotationMatrix2D(center, 5, 1.0)
        rotated_pos = cv2.warpAffine(aligned_face, rotation_matrix_pos, (w, h), 
                                      flags=cv2.INTER_LINEAR, 
                                      borderMode=cv2.BORDER_REPLICATE)
        augmented_faces.append(rotated_pos)
        
        return augmented_faces
        
    except Exception as e:
        print(f"[WARNING] TTA augmentation failed: {e}, using original only")
        return [aligned_face]


def extract_embedding_with_tta(processed_face: np.ndarray, model_name: str) -> np.ndarray:
    """
    Extract embedding with Test-Time Augmentation for improved robustness.
    
    Generates multiple augmented versions, extracts embeddings from each,
    and averages them for the final robust embedding.
    
    OPTIMIZED: Extracts embeddings directly from numpy arrays without disk I/O.
    
    Args:
        processed_face: Processed face image (after edge detection if photo)
        model_name: 'ArcFace' or 'Facenet512'
    
    Returns:
        np.ndarray: Averaged embedding (L2 normalized)
    """
    try:
        # Generate augmented versions
        augmented_faces = generate_tta_augmentations(processed_face)
        
        embeddings = []
        
        # Extract embedding from each augmented version
        for idx, aug_face in enumerate(augmented_faces):
            try:
                # Resize to model input size
                target_size = 112
                resized_face = cv2.resize(aug_face, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
                
                # Extract embedding directly from numpy array (no disk I/O!)
                if model_name == 'ArcFace':
                    # DeepFace.represent() accepts numpy arrays directly
                    result = DeepFace.represent(
                        img_path=resized_face,  # Can be numpy array!
                        model_name='ArcFace',
                        enforce_detection=False,
                        align=False,
                        detector_backend='skip'
                    )
                    embedding = np.array(result[0]['embedding'])
                    # L2 normalize
                    embedding = normalize_arcface_embedding(embedding)
                    
                elif model_name == 'Facenet512':
                    # DeepFace.represent() accepts numpy arrays directly
                    result = DeepFace.represent(
                        img_path=resized_face,  # Can be numpy array!
                        model_name='Facenet512',
                        enforce_detection=False,
                        align=False,
                        detector_backend='skip'
                    )
                    embedding = np.array(result[0]['embedding'])
                    # L2 normalize
                    embedding = normalize_facenet_embedding(embedding)
                    
                else:
                    raise ValueError(f"Unsupported model: {model_name}")
                
                embeddings.append(embedding)
                    
            except Exception as e:
                print(f"      [WARNING] TTA augmentation {idx} failed: {e}")
                continue
        
        # Average all embeddings
        if len(embeddings) > 0:
            avg_embedding = np.mean(embeddings, axis=0)
            
            # L2 normalize the averaged embedding
            norm = np.linalg.norm(avg_embedding)
            if norm > 0:
                avg_embedding = avg_embedding / norm
            
            return avg_embedding
        else:
            # Fallback: extract from original without TTA
            print("      [WARNING] All TTA augmentations failed, extracting from original")
            target_size = 112
            resized_face = cv2.resize(processed_face, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
            
            # Extract embedding directly from numpy array (no disk I/O!)
            if model_name == 'ArcFace':
                result = DeepFace.represent(
                    img_path=resized_face,
                    model_name='ArcFace',
                    enforce_detection=False,
                    align=False,
                    detector_backend='skip'
                )
                embedding = np.array(result[0]['embedding'])
                embedding = normalize_arcface_embedding(embedding)
                
            elif model_name == 'Facenet512':
                result = DeepFace.represent(
                    img_path=resized_face,
                    model_name='Facenet512',
                    enforce_detection=False,
                    align=False,
                    detector_backend='skip'
                )
                embedding = np.array(result[0]['embedding'])
                embedding = normalize_facenet_embedding(embedding)
                
            else:
                raise ValueError(f"Unsupported model: {model_name}")
            
            return embedding
        
    except Exception as e:
        print(f"[ERROR] TTA embedding extraction failed: {e}")
        raise


def extract_dual_embeddings(image_path: str, is_sketch: bool = False, use_adaptive_canny: bool = False, reference_embedding: np.ndarray = None) -> dict:
    """
    Extract dual embeddings (ArcFace + Facenet) from image with edge-based preprocessing
    
    DUAL EMBEDDING FUSION:
    - Extracts embeddings from both ArcFace and Facenet models
    - Both embeddings are L2 normalized
    - Returns dict with both embeddings for fusion
    - Also returns the aligned face for geometric similarity calculation
    
    APPROACH:
    1. Detect and align face on ORIGINAL image (before edge detection)
    2. Apply edge detection to the ALIGNED face (photos only)
    3. If use_adaptive_canny=True and reference_embedding provided, test multiple thresholds
    4. Extract embeddings from both models
    5. L2 normalize both embeddings
    6. Return embeddings AND aligned face
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
        use_adaptive_canny: If True, test multiple Canny thresholds (photos only)
        reference_embedding: Reference embedding for adaptive threshold selection
    
    Returns:
        dict: {
            'arcface': np.ndarray (512-D, L2 normalized),
            'facenet': np.ndarray (512-D, L2 normalized),
            'aligned_face': np.ndarray (aligned face image for geometric similarity),
            'best_threshold': tuple (if adaptive Canny used),
            'success': bool
        }
        Returns None if extraction fails
    """
    try:
        # Validate input file exists
        if not os.path.exists(image_path):
            print(f"[ERROR] Input image does not exist: {image_path}")
            return None
        
        # Validate file can be read by cv2
        img = cv2.imread(image_path)
        if img is None:
            print(f"[ERROR] cv2.imread() failed - image is corrupted or invalid: {image_path}")
            return None
        
        # STEP 1: Detect and extract face from ORIGINAL image
        print(f"  [STEP 1] Detecting face on original image...")
        
        # Detect face and get aligned face region
        face_objs = detection.extract_faces(
            img_path=image_path,
            detector_backend='opencv',
            enforce_detection=True,
            align=True,
            grayscale=False
        )
        
        if not face_objs or len(face_objs) == 0:
            print(f"[ERROR] No face detected in: {image_path}")
            return None
        
        # Get the first (largest) face
        face_obj = face_objs[0]
        aligned_face = face_obj['face']  # This is the aligned face as numpy array
        
        print(f"    [OK] Face detected and aligned, size: {aligned_face.shape}")
        
        # Keep a copy of the aligned face for geometric similarity (before edge processing)
        # Convert to uint8 if needed
        if aligned_face.dtype == np.float32 or aligned_face.dtype == np.float64:
            aligned_face_copy = (aligned_face * 255).astype(np.uint8)
        else:
            aligned_face_copy = aligned_face.copy()
        
        # STEP 2: Apply edge detection to aligned face (if photo)
        if not is_sketch:
            # Convert to uint8 if needed (DeepFace returns normalized float)
            if aligned_face.dtype == np.float32 or aligned_face.dtype == np.float64:
                aligned_face = (aligned_face * 255).astype(np.uint8)
            
            # Convert to grayscale
            if len(aligned_face.shape) == 3:
                gray = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY)
            else:
                gray = aligned_face
            
            # Adaptive Canny threshold selection for photos
            if use_adaptive_canny and reference_embedding is not None:
                print("  [STEP 2] Applying ADAPTIVE Canny edge detection to aligned face...")
                
                # Test multiple threshold combinations
                threshold_combinations = [
                    (30, 120),  # More edges (sensitive)
                    (50, 150),  # Balanced (default)
                    (70, 200)   # Fewer edges (conservative)
                ]
                
                best_threshold = (50, 150)
                best_similarity = -1.0
                best_edges = None
                
                print(f"    Testing {len(threshold_combinations)} threshold combinations...")
                
                for threshold in threshold_combinations:
                    # Apply Canny edge detection with this threshold
                    edges = cv2.Canny(gray, threshold1=threshold[0], threshold2=threshold[1])
                    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                    
                    # Resize to model input size
                    target_size = 112
                    resized_face = cv2.resize(edges_bgr, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)
                    
                    try:
                        # Extract ArcFace embedding directly from numpy array (no disk I/O!)
                        result = DeepFace.represent(
                            img_path=resized_face,  # Can be numpy array!
                            model_name='ArcFace',
                            enforce_detection=False,
                            align=False,
                            detector_backend='skip'
                        )
                        test_embedding = np.array(result[0]['embedding'])
                        
                        # L2 normalize
                        test_embedding = normalize_arcface_embedding(test_embedding)
                        
                        # Compute similarity with reference using stable cosine similarity
                        similarity = cosine_similarity(test_embedding, reference_embedding)
                        
                        print(f"      Threshold {threshold}: similarity={similarity:.4f} ({similarity*100:.1f}%)")
                        
                        if similarity > best_similarity:
                            best_similarity = similarity
                            best_threshold = threshold
                            best_edges = edges
                        
                    except Exception as e:
                        print(f"      Threshold {threshold}: FAILED - {e}")
                
                print(f"    [BEST] Threshold {best_threshold} with similarity {best_similarity:.4f}")
                
                # Use best threshold result
                if best_edges is not None:
                    processed_face = cv2.cvtColor(best_edges, cv2.COLOR_GRAY2BGR)
                else:
                    # Fallback to default
                    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
                    processed_face = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                    best_threshold = (50, 150)
                
                print(f"    [OK] Adaptive edge detection applied with threshold {best_threshold}")
                
            else:
                # Standard Canny edge detection (default threshold)
                print(f"  [STEP 2] Applying edge detection to aligned face...")
                edges = cv2.Canny(gray, threshold1=50, threshold2=150)
                processed_face = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                best_threshold = (50, 150)
                print(f"    [OK] Edge detection applied")
            
        else:
            print(f"  [STEP 2] Sketch - keeping aligned face intact...")
            
            # Convert to uint8 if needed
            if aligned_face.dtype == np.float32 or aligned_face.dtype == np.float64:
                aligned_face = (aligned_face * 255).astype(np.uint8)
            
            # Convert to grayscale
            if len(aligned_face.shape) == 3:
                gray = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY)
            else:
                gray = aligned_face
            
            # Convert to 3-channel BGR (no edge detection)
            processed_face = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            best_threshold = None  # No threshold for sketches
            
            print(f"    [OK] Sketch kept intact")
        
        # STEP 3: Extract dual embeddings with Test-Time Augmentation (TTA)
        print(f"  [STEP 3] Extracting dual embeddings with TTA (ArcFace + Facenet)...")
        
        # Extract ArcFace embedding with TTA
        print("    Extracting ArcFace embedding with TTA (3 augmentations)...")
        arcface_embedding = extract_embedding_with_tta(processed_face, 'ArcFace')
        print(f"      [OK] ArcFace: length={len(arcface_embedding)}, TTA-averaged and normalized")
        
        # Extract Facenet512 embedding with TTA
        print("    Extracting Facenet512 embedding with TTA (3 augmentations)...")
        facenet_embedding = extract_embedding_with_tta(processed_face, 'Facenet512')
        print(f"      [OK] Facenet: length={len(facenet_embedding)}, TTA-averaged and normalized")
        
        print(f"    [OK] Dual embeddings extracted successfully with TTA")
        
        result = {
            'arcface': arcface_embedding,
            'facenet': facenet_embedding,
            'aligned_face': aligned_face_copy,
            'success': True,
            'tta_applied': True,
            'tta_augmentations': 3
        }
        
        # Add best_threshold if adaptive Canny was used
        if use_adaptive_canny and not is_sketch:
            result['best_threshold'] = best_threshold
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Dual embedding extraction failed: {e}")
        traceback.print_exc()
        return None


def extract_embedding(image_path: str, is_sketch: bool = False) -> np.ndarray:
    """
    Extract ArcFace embedding from image with edge-based preprocessing
    
    LEGACY FUNCTION: Use extract_dual_embeddings() for dual model fusion
    
    APPROACH:
    1. Detect and align face on ORIGINAL image (before edge detection)
    2. Apply edge detection to the ALIGNED face
    3. Extract embedding from edge-detected aligned face
    
    This ensures face detection works while still reducing domain gap.
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
    
    Returns:
        np.ndarray: 512-dimensional embedding vector, or None if extraction fails
    """
    # Use dual embeddings and return only ArcFace for backward compatibility
    result = extract_dual_embeddings(image_path, is_sketch)
    if result and result['success']:
        return result['arcface']
    return None
