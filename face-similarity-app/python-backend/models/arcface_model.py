"""
ArcFace model wrapper and initialization
Handles ArcFace model loading and inference
"""
import numpy as np
from deepface import DeepFace


# Global model state
_ARCFACE_MODEL = None
_ARCFACE_INITIALIZED = False


def initialize_arcface_model(dummy_image_path: str = None):
    """
    Pre-load ArcFace model to ensure consistent performance
    
    Uses direct model loading via DeepFace.build_model() for efficiency.
    This is faster than dummy image inference.
    
    Args:
        dummy_image_path: Path to dummy image (deprecated, kept for API compatibility)
    
    Returns:
        bool: True if successful, False otherwise
    """
    global _ARCFACE_MODEL, _ARCFACE_INITIALIZED
    
    if _ARCFACE_INITIALIZED:
        return True
    
    try:
        print("Loading ArcFace model...")
        
        # Load model directly (more efficient than dummy image inference)
        _ARCFACE_MODEL = DeepFace.build_model("ArcFace")
        
        _ARCFACE_INITIALIZED = True
        print("[OK] ArcFace model loaded successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] ArcFace model initialization failed: {e}")
        _ARCFACE_MODEL = None
        _ARCFACE_INITIALIZED = False
        return False


def is_arcface_initialized() -> bool:
    """
    Check if ArcFace model is initialized
    
    Returns:
        bool: True if initialized, False otherwise
    """
    return _ARCFACE_INITIALIZED and _ARCFACE_MODEL is not None


def get_arcface_model():
    """
    Get the loaded ArcFace model
    
    Returns:
        Model instance or None if not initialized
    """
    return _ARCFACE_MODEL


def extract_arcface_embedding(image_path: str, enforce_detection: bool = False, 
                               align: bool = False, detector_backend: str = 'skip') -> np.ndarray:
    """
    Extract ArcFace embedding from image with safety validation
    
    Args:
        image_path: Path to image file or numpy array
        enforce_detection: Whether to enforce face detection
        align: Whether to align face
        detector_backend: Face detector backend ('opencv', 'skip', etc.)
    
    Returns:
        np.ndarray: 512-dimensional ArcFace embedding
    
    Raises:
        ValueError: If result is empty or embedding is missing
        ValueError: If embedding dimensions are incorrect
        Exception: If embedding extraction fails
    """
    try:
        result = DeepFace.represent(
            img_path=image_path,
            model_name='ArcFace',
            enforce_detection=enforce_detection,
            align=align,
            detector_backend=detector_backend
        )
        
        # Safety validation: Check result is not empty
        if not result or len(result) == 0:
            raise ValueError("DeepFace.represent() returned empty result - no face detected or extraction failed")
        
        # Safety validation: Check embedding key exists
        if 'embedding' not in result[0]:
            raise ValueError("DeepFace.represent() result missing 'embedding' key - unexpected response format")
        
        embedding = np.array(result[0]['embedding'])
        
        # Safety validation: Check embedding dimensions
        expected_dim = 512
        if len(embedding) != expected_dim:
            raise ValueError(f"ArcFace embedding has incorrect dimensions: expected {expected_dim}, got {len(embedding)}")
        
        return embedding
        
    except ValueError as e:
        # Re-raise validation errors with clear message
        raise ValueError(f"ArcFace embedding extraction validation failed: {e}")
    except Exception as e:
        raise Exception(f"ArcFace embedding extraction failed: {e}")


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    L2 normalize embedding vector
    
    Args:
        embedding: Embedding vector
    
    Returns:
        np.ndarray: L2 normalized embedding
    """
    norm = np.linalg.norm(embedding)
    if norm > 0:
        return embedding / norm
    return embedding
