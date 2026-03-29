"""
embedding_service.py — dual-model face embedding service.

Models:
  - InsightFace buffalo_l  (replaces DeepFace ArcFace)  → 512-D
  - DeepFace Facenet512                                  → 512-D

Key guarantees:
  - Both models loaded ONCE at startup (singleton, thread-safe)
  - InsightFace failure → Facenet-only (API never crashes)
  - Facenet failure     → InsightFace-only
  - Both fail          → controlled error dict (no unhandled exception)
  - TTA: 3 augmentations averaged per model
  - All steps logged for debugging
"""

import os
import threading
import traceback

import cv2
import numpy as np

# InsightFace (replaces DeepFace ArcFace)
from models.insightface_model import (
    initialize_insightface_model,
    extract_insightface_embedding,
    normalize_embedding as normalize_insightface,
    is_insightface_initialized,
)

# DeepFace Facenet512 (unchanged)
from deepface import DeepFace
from deepface.modules import detection
from models.facenet_model import (
    initialize_facenet_model,
    extract_facenet_embedding,
    normalize_embedding as normalize_facenet,
    is_facenet_initialized,
    FACENET_WEIGHT_PATH,
)

from utils.file_utils import generate_temp_filepath, cleanup_temp_file
from utils.similarity_utils import cosine_similarity

# ---------------------------------------------------------------------------
# Global initialization state
# ---------------------------------------------------------------------------

MODEL_INITIALIZED = False
_INIT_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Startup model initialization
# ---------------------------------------------------------------------------

def initialize_models() -> bool:
    """
    Load InsightFace + Facenet512 at server startup.
    Thread-safe, idempotent. Returns True if at least one model loaded.
    """
    global MODEL_INITIALIZED

    if MODEL_INITIALIZED:
        return True

    with _INIT_LOCK:
        if MODEL_INITIALIZED:
            return True

        print("\n" + "=" * 60)
        print("  INITIALIZING FACE RECOGNITION MODELS")
        print("=" * 60)

        insightface_ok = _init_insightface_safe()
        facenet_ok     = _init_facenet_safe()

        if not insightface_ok and not facenet_ok:
            print("[EmbeddingService] [FAIL] CRITICAL: Both models failed to load.")
            MODEL_INITIALIZED = True
            return False

        MODEL_INITIALIZED = True
        print("=" * 60)
        print(f"  InsightFace : {'[OK] ready' if insightface_ok else '[FAIL] unavailable'}")
        print(f"  Facenet512  : {'[OK] ready' if facenet_ok     else '[FAIL] unavailable'}")
        print("=" * 60 + "\n")
        return True


def is_models_initialized() -> bool:
    return MODEL_INITIALIZED


# ---------------------------------------------------------------------------
# Private init helpers
# ---------------------------------------------------------------------------

def _init_insightface_safe() -> bool:
    try:
        print("[InsightFace] Starting initialization...")
        ok = initialize_insightface_model()
        print(f"[InsightFace] {'[OK] Initialized' if ok else '[FAIL] Initialization returned False'}")
        return ok
    except Exception as e:
        print(f"[InsightFace] [FAIL] Exception during init: {e}")
        traceback.print_exc()
        return False


def _init_facenet_safe() -> bool:
    try:
        print("[Facenet512] Starting initialization...")
        ok = initialize_facenet_model()
        print(f"[Facenet512] {'[OK] Initialized' if ok else '[FAIL] Initialization returned False'}")
        return ok
    except Exception as e:
        print(f"[Facenet512] [FAIL] Exception during init: {e}")
        traceback.print_exc()
        return False


def _log_weight_file_status() -> None:
    if os.path.exists(FACENET_WEIGHT_PATH):
        size_mb = os.path.getsize(FACENET_WEIGHT_PATH) / (1024 * 1024)
        print(f"  [Facenet512] weights: {FACENET_WEIGHT_PATH} ({size_mb:.1f} MB)")
    else:
        print("  [Facenet512] weights: NOT FOUND - will download on first load")
    print("  [InsightFace] weights: managed by insightface package (~/.insightface/)")


# ---------------------------------------------------------------------------
# TTA augmentations
# ---------------------------------------------------------------------------

def generate_tta_augmentations(aligned_face: np.ndarray) -> list:
    """
    Generate 3 TTA versions of an aligned face.
    Returns list of 1-3 augmented images.
    """
    try:
        h, w = aligned_face.shape[:2]
        augmented = [aligned_face.copy()]

        # Horizontal flip
        try:
            augmented.append(cv2.flip(aligned_face, 1))
        except Exception as e:
            print(f"[TTA] Flip failed (skipped): {e}")

        # Rotation +5 degrees
        try:
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, 5, 1.0)
            rotated = cv2.warpAffine(
                aligned_face, M, (w, h),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
            augmented.append(rotated)
        except Exception as e:
            print(f"[TTA] Rotation failed (skipped): {e}")

        return augmented

    except Exception as e:
        print(f"[TTA] generate_tta_augmentations failed: {e}")
        return [aligned_face]


# ---------------------------------------------------------------------------
# Single-model embedding extraction helpers
# ---------------------------------------------------------------------------

_FACENET_INPUT_SIZE = 160


def _resize_for_facenet(face: np.ndarray) -> np.ndarray:
    return cv2.resize(face, (_FACENET_INPUT_SIZE, _FACENET_INPUT_SIZE),
                      interpolation=cv2.INTER_LANCZOS4)


def _extract_insightface_single(face_arr: np.ndarray) -> np.ndarray:
    """Extract InsightFace embedding from a single face array."""
    if not is_insightface_initialized():
        raise RuntimeError("InsightFace model not initialized")
    emb = extract_insightface_embedding(face_arr)
    return normalize_insightface(emb)


def _extract_facenet_single(face_arr: np.ndarray) -> np.ndarray:
    """Extract Facenet512 embedding from a single face array via DeepFace."""
    if not is_facenet_initialized():
        raise RuntimeError("Facenet512 model not initialized")

    resized = _resize_for_facenet(face_arr)
    result = DeepFace.represent(
        img_path=resized,
        model_name="Facenet512",
        enforce_detection=False,
        align=False,
        detector_backend="skip",
    )
    if not result or "embedding" not in result[0]:
        raise ValueError("Facenet512: empty/malformed result from DeepFace.represent()")

    emb = np.array(result[0]["embedding"])
    return normalize_facenet(emb)


# ---------------------------------------------------------------------------
# TTA-averaged embedding extraction (public, used by face_comparison_service)
# ---------------------------------------------------------------------------

def extract_embedding_with_tta(processed_face: np.ndarray, model_name: str) -> np.ndarray:
    """
    Extract embedding with TTA averaging.

    model_name: 'InsightFace' or 'Facenet512'
    Returns: L2-normalized 512-D embedding.
    Raises RuntimeError if model unavailable AND fallback also fails.
    """
    augmented_faces = generate_tta_augmentations(processed_face)
    embeddings = []

    for idx, aug_face in enumerate(augmented_faces):
        try:
            if model_name == "InsightFace":
                emb = _extract_insightface_single(aug_face)
            elif model_name == "Facenet512":
                emb = _extract_facenet_single(aug_face)
            else:
                raise ValueError(f"Unsupported model: {model_name}")

            embeddings.append(emb)
            print(f"    [TTA] {model_name} aug {idx}: [OK] ({len(emb)}-D)")
        except Exception as e:
            print(f"    [TTA] {model_name} aug {idx}: [WARN] skipped - {e}")

    if embeddings:
        avg = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg)
        avg = avg / norm if norm > 0 else avg
        print(f"    [TTA] {model_name}: averaged {len(embeddings)} augmentation(s)")
        return avg

    # All TTA failed — plain extraction as last resort
    print(f"    [TTA] {model_name}: all augmentations failed, trying plain extraction...")
    if model_name == "InsightFace":
        return _extract_insightface_single(processed_face)
    return _extract_facenet_single(processed_face)


# ---------------------------------------------------------------------------
# Face detection + alignment (Facenet/DeepFace detector, unchanged)
# ---------------------------------------------------------------------------

def _detect_and_align_face(image_path: str) -> np.ndarray:
    """
    Detect and align the largest face using DeepFace opencv detector.
    Returns uint8 BGR aligned face array.
    Raises ValueError if no face detected.
    """
    face_objs = detection.extract_faces(
        img_path=image_path,
        detector_backend="opencv",
        enforce_detection=True,
        align=True,
        grayscale=False,
    )

    if not face_objs:
        raise ValueError(f"No face detected in: {image_path}")

    aligned = face_objs[0]["face"]
    if aligned.dtype in (np.float32, np.float64):
        aligned = (aligned * 255).astype(np.uint8)

    print(f"    [Detect] Face aligned: shape={aligned.shape}, dtype={aligned.dtype}")
    return aligned


# ---------------------------------------------------------------------------
# Image preprocessing (edge detection for photos)
# ---------------------------------------------------------------------------

def _preprocess_face(
    aligned_face: np.ndarray,
    is_sketch: bool,
    canny_threshold: tuple = (50, 150),
) -> np.ndarray:
    """
    Photos  → Canny edge detection (reduces photo→sketch domain gap)
    Sketches → grayscale → 3-channel BGR
    """
    if aligned_face.dtype in (np.float32, np.float64):
        aligned_face = (aligned_face * 255).astype(np.uint8)

    gray = (
        cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY)
        if len(aligned_face.shape) == 3
        else aligned_face
    )

    if is_sketch:
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    edges = cv2.Canny(gray, threshold1=canny_threshold[0], threshold2=canny_threshold[1])
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# Adaptive Canny threshold selection (uses InsightFace instead of ArcFace)
# ---------------------------------------------------------------------------

def _select_best_canny_threshold(
    aligned_face: np.ndarray,
    reference_embedding: np.ndarray,
) -> tuple:
    """
    Test 3 Canny threshold combinations and pick the one whose InsightFace
    embedding is most similar to the reference (sketch) embedding.
    Falls back to (50, 150) if InsightFace is unavailable.
    """
    if not is_insightface_initialized():
        print("    [AdaptiveCanny] InsightFace unavailable, using default threshold (50, 150)")
        return (50, 150)

    candidates = [(30, 120), (50, 150), (70, 200)]
    best_threshold = (50, 150)
    best_similarity = -1.0

    if aligned_face.dtype in (np.float32, np.float64):
        aligned_face = (aligned_face * 255).astype(np.uint8)

    gray = (
        cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY)
        if len(aligned_face.shape) == 3
        else aligned_face
    )

    for thresh in candidates:
        try:
            edges = cv2.Canny(gray, threshold1=thresh[0], threshold2=thresh[1])
            edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            emb = _extract_insightface_single(edges_bgr)
            sim = cosine_similarity(emb, reference_embedding)
            print(f"    [AdaptiveCanny] threshold={thresh}: similarity={sim*100:.1f}%")
            if sim > best_similarity:
                best_similarity = sim
                best_threshold = thresh
        except Exception as e:
            print(f"    [AdaptiveCanny] threshold={thresh}: failed - {e}")

    print(f"    [AdaptiveCanny] Best threshold: {best_threshold} (sim={best_similarity*100:.1f}%)")
    return best_threshold


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def extract_dual_embeddings(
    image_path: str,
    is_sketch: bool = False,
    use_adaptive_canny: bool = False,
    reference_embedding: np.ndarray = None,
) -> dict:
    """
    Extract InsightFace + Facenet512 dual embeddings from an image.

    Fail-safe:
      - InsightFace fails → result still contains Facenet embedding (success=True)
      - Facenet fails     → result still contains InsightFace embedding (success=True)
      - Both fail         → {'success': False, 'error': '...'}

    Returns dict with keys:
        success, insightface, facenet, aligned_face,
        tta_applied, tta_augmentations, best_threshold, error
    """
    result = {
        "success": False,
        "insightface": None,
        "facenet": None,
        "aligned_face": None,
        "tta_applied": False,
        "tta_augmentations": 3,
        "best_threshold": None,
        "error": None,
    }

    if not is_insightface_initialized() and not is_facenet_initialized():
        msg = "No face recognition models available. Check server startup logs."
        print(f"[EmbeddingService] [FAIL] {msg}")
        result["error"] = msg
        return result

    if not os.path.exists(image_path):
        result["error"] = f"Input image not found: {image_path}"
        print(f"[EmbeddingService] [FAIL] {result['error']}")
        return result

    img_check = cv2.imread(image_path)
    if img_check is None:
        result["error"] = f"cv2.imread() failed: {image_path}"
        print(f"[EmbeddingService] [FAIL] {result['error']}")
        return result

    print(f"[EmbeddingService] Processing: {os.path.basename(image_path)} "
          f"({'sketch' if is_sketch else 'photo'})")

    # Step 1: Face detection + alignment
    try:
        print("  [Step 1] Detecting and aligning face...")
        aligned_face = _detect_and_align_face(image_path)
        result["aligned_face"] = aligned_face.copy()
    except Exception as e:
        result["error"] = f"Face detection failed: {e}"
        print(f"[EmbeddingService] [FAIL] {result['error']}")
        return result

    # Step 2: Preprocessing
    try:
        print("  [Step 2] Preprocessing face...")
        if not is_sketch and use_adaptive_canny and reference_embedding is not None:
            print("    Using adaptive Canny threshold selection...")
            best_thresh = _select_best_canny_threshold(aligned_face, reference_embedding)
            result["best_threshold"] = best_thresh
        else:
            best_thresh = (50, 150)

        processed_face = _preprocess_face(aligned_face, is_sketch, canny_threshold=best_thresh)
        print(f"    Preprocessed shape: {processed_face.shape}")
    except Exception as e:
        result["error"] = f"Preprocessing failed: {e}"
        print(f"[EmbeddingService] [FAIL] {result['error']}")
        return result

    # Step 3a: InsightFace embedding (with TTA)
    insightface_ok = False
    if is_insightface_initialized():
        try:
            print("  [Step 3a] Extracting InsightFace embedding (TTA)...")
            insightface_emb = extract_embedding_with_tta(processed_face, "InsightFace")
            result["insightface"] = insightface_emb
            insightface_ok = True
            print(f"    [OK] InsightFace: {len(insightface_emb)}-D, normalized")
        except Exception as e:
            print(f"  [Step 3a] [FAIL] InsightFace failed: {e}")
            traceback.print_exc()
    else:
        print("  [Step 3a] [WARN] InsightFace not initialized - skipping")

    # Step 3b: Facenet512 embedding (with TTA)
    facenet_ok = False
    if is_facenet_initialized():
        try:
            print("  [Step 3b] Extracting Facenet512 embedding (TTA)...")
            facenet_emb = extract_embedding_with_tta(processed_face, "Facenet512")
            result["facenet"] = facenet_emb
            facenet_ok = True
            print(f"    [OK] Facenet512: {len(facenet_emb)}-D, normalized")
        except Exception as e:
            print(f"  [Step 3b] [FAIL] Facenet512 failed: {e}")
            traceback.print_exc()
    else:
        print("  [Step 3b] [WARN] Facenet512 not initialized - skipping")

    if not insightface_ok and not facenet_ok:
        result["error"] = (
            "Both InsightFace and Facenet512 embedding extraction failed. "
            "Check model weights and server logs."
        )
        print(f"[EmbeddingService] [FAIL] {result['error']}")
        return result

    if not insightface_ok:
        print("[EmbeddingService] [WARN] InsightFace unavailable - using Facenet512 only")
    if not facenet_ok:
        print("[EmbeddingService] [WARN] Facenet512 unavailable - using InsightFace only")

    result["success"] = True
    result["tta_applied"] = True
    print("[EmbeddingService] [OK] Dual embedding extraction complete")
    return result


def extract_embedding(image_path: str, is_sketch: bool = False) -> np.ndarray:
    """
    Legacy single-embedding API.
    Returns InsightFace embedding (or Facenet as fallback).
    Use extract_dual_embeddings() for new code.
    """
    res = extract_dual_embeddings(image_path, is_sketch)
    if res and res["success"]:
        return res["insightface"] if res["insightface"] is not None else res["facenet"]
    return None
