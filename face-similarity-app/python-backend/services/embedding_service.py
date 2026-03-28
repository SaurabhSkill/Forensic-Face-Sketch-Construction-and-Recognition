"""
embedding_service.py — EC2-hardened face embedding service

Key guarantees:
  - Models loaded ONCE at startup (singleton, thread-safe)
  - Weight files validated (HDF5 signature + size) before every load attempt
  - Corrupt/partial files deleted and re-downloaded automatically
  - ArcFace failure → fallback to Facenet-only (API never crashes)
  - Facenet failure → fallback to ArcFace-only
  - Both fail → controlled error dict returned (no exception propagates to API)
  - TTA never reloads models; individual augmentation failures are skipped safely
  - All steps logged with file paths and sizes for EC2 debugging
"""

import os
import threading
import traceback

import cv2
import numpy as np
from deepface import DeepFace
from deepface.modules import detection

from models.arcface_model import (
    initialize_arcface_model,
    extract_arcface_embedding,
    normalize_embedding as normalize_arcface,
    is_arcface_initialized,
    ARCFACE_WEIGHT_PATH,
)
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

MODEL_INITIALIZED = False          # True once at least one model is ready
_INIT_LOCK = threading.Lock()      # Guards the initialization sequence


# ---------------------------------------------------------------------------
# Startup model initialization
# ---------------------------------------------------------------------------

def initialize_models() -> bool:
    """
    Load ArcFace and Facenet512 at server startup.

    - Thread-safe: safe to call from multiple gunicorn workers simultaneously.
    - Idempotent: calling more than once is a no-op.
    - Partial success: if one model fails the other still serves requests.

    Returns:
        bool: True if at least one model loaded successfully.
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
        _log_weight_file_status()

        arcface_ok = _init_arcface_safe()
        facenet_ok = _init_facenet_safe()

        if not arcface_ok and not facenet_ok:
            print("[EmbeddingService] ❌ CRITICAL: Both models failed to load.")
            print("[EmbeddingService]    Face comparison will return errors.")
            MODEL_INITIALIZED = True   # Don't retry on every request
            return False

        MODEL_INITIALIZED = True
        print("=" * 60)
        print(f"  ArcFace  : {'✅ ready' if arcface_ok else '❌ unavailable'}")
        print(f"  Facenet  : {'✅ ready' if facenet_ok else '❌ unavailable'}")
        print("=" * 60 + "\n")
        return True


def is_models_initialized() -> bool:
    return MODEL_INITIALIZED


# ---------------------------------------------------------------------------
# Private init helpers
# ---------------------------------------------------------------------------

def _init_arcface_safe() -> bool:
    """Initialize ArcFace, catching all exceptions."""
    try:
        print("[ArcFace] Starting initialization...")
        ok = initialize_arcface_model()
        if ok:
            print("[ArcFace] ✅ Initialized successfully")
        else:
            print("[ArcFace] ❌ Initialization returned False")
        return ok
    except Exception as e:
        print(f"[ArcFace] ❌ Exception during init: {e}")
        traceback.print_exc()
        return False


def _init_facenet_safe() -> bool:
    """Initialize Facenet512, catching all exceptions."""
    try:
        print("[Facenet512] Starting initialization...")
        ok = initialize_facenet_model()
        if ok:
            print("[Facenet512] ✅ Initialized successfully")
        else:
            print("[Facenet512] ❌ Initialization returned False")
        return ok
    except Exception as e:
        print(f"[Facenet512] ❌ Exception during init: {e}")
        traceback.print_exc()
        return False


def _log_weight_file_status() -> None:
    """Log weight file paths and sizes — critical for EC2 debugging."""
    for label, path in [("ArcFace", ARCFACE_WEIGHT_PATH), ("Facenet512", FACENET_WEIGHT_PATH)]:
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  [{label}] weights: {path} ({size_mb:.1f} MB)")
        else:
            print(f"  [{label}] weights: NOT FOUND — will download on first load")


# ---------------------------------------------------------------------------
# TTA augmentations
# ---------------------------------------------------------------------------

def generate_tta_augmentations(aligned_face: np.ndarray) -> list:
    """
    Generate 3 TTA versions of an aligned face.
    Never reloads models. Individual failures return the original only.

    Returns:
        list[np.ndarray]: 1–3 augmented face images.
    """
    try:
        h, w = aligned_face.shape[:2]
        augmented = [aligned_face.copy()]  # 1. original

        # 2. Horizontal flip
        try:
            augmented.append(cv2.flip(aligned_face, 1))
        except Exception as e:
            print(f"[TTA] Flip augmentation failed (skipped): {e}")

        # 3. Rotation +5°
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
            print(f"[TTA] Rotation augmentation failed (skipped): {e}")

        return augmented

    except Exception as e:
        print(f"[TTA] generate_tta_augmentations failed entirely: {e}")
        return [aligned_face]


# ---------------------------------------------------------------------------
# Single-model embedding extraction (with TTA)
# ---------------------------------------------------------------------------

def _resize_for_model(face: np.ndarray, size: int = 112) -> np.ndarray:
    """Resize face to model input size."""
    return cv2.resize(face, (size, size), interpolation=cv2.INTER_LANCZOS4)


def _extract_single_embedding(face_arr: np.ndarray, model_name: str) -> np.ndarray:
    """
    Extract embedding from a single numpy face array.
    Does NOT reload the model — uses the already-loaded singleton via DeepFace.represent().

    Args:
        face_arr: Preprocessed face (numpy array, already resized).
        model_name: 'ArcFace' or 'Facenet512'.

    Returns:
        np.ndarray: L2-normalized embedding.

    Raises:
        RuntimeError: If model is not initialized.
        ValueError: If result is malformed.
    """
    if model_name == "ArcFace":
        if not is_arcface_initialized():
            raise RuntimeError("ArcFace model not initialized")
        normalize_fn = normalize_arcface
    elif model_name == "Facenet512":
        if not is_facenet_initialized():
            raise RuntimeError("Facenet512 model not initialized")
        normalize_fn = normalize_facenet
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    result = DeepFace.represent(
        img_path=face_arr,
        model_name=model_name,
        enforce_detection=False,
        align=False,
        detector_backend="skip",
    )

    if not result or "embedding" not in result[0]:
        raise ValueError(f"{model_name}: empty/malformed result from DeepFace.represent()")

    embedding = np.array(result[0]["embedding"])
    return normalize_fn(embedding)


def extract_embedding_with_tta(processed_face: np.ndarray, model_name: str) -> np.ndarray:
    """
    Extract embedding with TTA averaging.

    - Generates up to 3 augmentations.
    - Skips any augmentation that fails (logs warning, continues).
    - If ALL augmentations fail → falls back to plain extraction from original.
    - Never reloads models.

    Args:
        processed_face: Preprocessed face image (numpy array).
        model_name: 'ArcFace' or 'Facenet512'.

    Returns:
        np.ndarray: L2-normalized averaged embedding.

    Raises:
        RuntimeError: If model is unavailable AND fallback also fails.
    """
    augmented_faces = generate_tta_augmentations(processed_face)
    embeddings = []

    for idx, aug_face in enumerate(augmented_faces):
        try:
            resized = _resize_for_model(aug_face)
            emb = _extract_single_embedding(resized, model_name)
            embeddings.append(emb)
            print(f"    [TTA] {model_name} aug {idx}: ✅ ({len(emb)}-D)")
        except Exception as e:
            print(f"    [TTA] {model_name} aug {idx}: ⚠️  skipped — {e}")
            continue

    if embeddings:
        avg = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg)
        avg = avg / norm if norm > 0 else avg
        print(f"    [TTA] {model_name}: averaged {len(embeddings)} augmentation(s)")
        return avg

    # All TTA augmentations failed — try plain extraction as last resort
    print(f"    [TTA] {model_name}: all augmentations failed, trying plain extraction...")
    resized = _resize_for_model(processed_face)
    return _extract_single_embedding(resized, model_name)


# ---------------------------------------------------------------------------
# Face detection + alignment
# ---------------------------------------------------------------------------

def _detect_and_align_face(image_path: str) -> np.ndarray:
    """
    Detect and align the largest face in the image.

    Returns:
        np.ndarray: Aligned face as uint8 BGR array.

    Raises:
        ValueError: If no face is detected.
        RuntimeError: If detection itself errors.
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

    # DeepFace may return float32 in [0,1] — convert to uint8
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
    Apply domain-bridging preprocessing to an aligned face.

    Photos  → Canny edge detection (reduces photo→sketch domain gap)
    Sketches → grayscale → 3-channel BGR (no edge detection)

    Returns:
        np.ndarray: Preprocessed face as uint8 BGR.
    """
    # Ensure uint8
    if aligned_face.dtype in (np.float32, np.float64):
        aligned_face = (aligned_face * 255).astype(np.uint8)

    # Convert to grayscale
    gray = (
        cv2.cvtColor(aligned_face, cv2.COLOR_BGR2GRAY)
        if len(aligned_face.shape) == 3
        else aligned_face
    )

    if is_sketch:
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    # Photo: apply Canny edge detection
    edges = cv2.Canny(gray, threshold1=canny_threshold[0], threshold2=canny_threshold[1])
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------------------
# Adaptive Canny threshold selection
# ---------------------------------------------------------------------------

def _select_best_canny_threshold(
    aligned_face: np.ndarray,
    reference_embedding: np.ndarray,
) -> tuple:
    """
    Test 3 Canny threshold combinations and pick the one whose ArcFace
    embedding is most similar to the reference (sketch) embedding.

    Falls back to (50, 150) if ArcFace is unavailable or all tests fail.
    """
    if not is_arcface_initialized():
        print("    [AdaptiveCanny] ArcFace unavailable, using default threshold (50, 150)")
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
            resized = _resize_for_model(edges_bgr)
            emb = _extract_single_embedding(resized, "ArcFace")
            sim = cosine_similarity(emb, reference_embedding)
            print(f"    [AdaptiveCanny] threshold={thresh}: similarity={sim*100:.1f}%")
            if sim > best_similarity:
                best_similarity = sim
                best_threshold = thresh
        except Exception as e:
            print(f"    [AdaptiveCanny] threshold={thresh}: failed — {e}")

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
    Extract ArcFace + Facenet512 dual embeddings from an image.

    Fail-safe behaviour:
      - ArcFace fails  → result still contains Facenet embedding (success=True)
      - Facenet fails  → result still contains ArcFace embedding (success=True)
      - Both fail      → returns {'success': False, 'error': '...'}
      - API never raises an unhandled exception

    Args:
        image_path:           Path to image file.
        is_sketch:            True for sketch images, False for photos.
        use_adaptive_canny:   Test multiple Canny thresholds (photos only).
        reference_embedding:  Sketch embedding for adaptive threshold selection.

    Returns:
        dict with keys:
            success (bool)
            arcface (np.ndarray | None)
            facenet (np.ndarray | None)
            aligned_face (np.ndarray | None)
            tta_applied (bool)
            tta_augmentations (int)
            best_threshold (tuple | None)
            error (str | None)
    """
    result = {
        "success": False,
        "arcface": None,
        "facenet": None,
        "aligned_face": None,
        "tta_applied": False,
        "tta_augmentations": 3,
        "best_threshold": None,
        "error": None,
    }

    # ── 0. Guard: at least one model must be ready ──────────────────────────
    if not is_arcface_initialized() and not is_facenet_initialized():
        msg = "No face recognition models are available. Check server startup logs."
        print(f"[EmbeddingService] ❌ {msg}")
        result["error"] = msg
        return result

    # ── 1. Validate input file ───────────────────────────────────────────────
    if not os.path.exists(image_path):
        result["error"] = f"Input image not found: {image_path}"
        print(f"[EmbeddingService] ❌ {result['error']}")
        return result

    img_check = cv2.imread(image_path)
    if img_check is None:
        result["error"] = f"cv2.imread() failed — corrupt or unsupported image: {image_path}"
        print(f"[EmbeddingService] ❌ {result['error']}")
        return result

    print(f"[EmbeddingService] Processing: {os.path.basename(image_path)} "
          f"({'sketch' if is_sketch else 'photo'})")

    # ── 2. Face detection + alignment ───────────────────────────────────────
    try:
        print("  [Step 1] Detecting and aligning face...")
        aligned_face = _detect_and_align_face(image_path)
        result["aligned_face"] = aligned_face.copy()
    except Exception as e:
        result["error"] = f"Face detection failed: {e}"
        print(f"[EmbeddingService] ❌ {result['error']}")
        return result

    # ── 3. Preprocessing (edge detection / sketch passthrough) ──────────────
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
        print(f"[EmbeddingService] ❌ {result['error']}")
        return result

    # ── 4. ArcFace embedding (with TTA) ─────────────────────────────────────
    arcface_ok = False
    if is_arcface_initialized():
        try:
            print("  [Step 3a] Extracting ArcFace embedding (TTA)...")
            arcface_emb = extract_embedding_with_tta(processed_face, "ArcFace")
            result["arcface"] = arcface_emb
            arcface_ok = True
            print(f"    ✅ ArcFace: {len(arcface_emb)}-D, normalized")
        except Exception as e:
            print(f"  [Step 3a] ❌ ArcFace failed: {e}")
            traceback.print_exc()
    else:
        print("  [Step 3a] ⚠️  ArcFace not initialized — skipping")

    # ── 5. Facenet512 embedding (with TTA) ──────────────────────────────────
    facenet_ok = False
    if is_facenet_initialized():
        try:
            print("  [Step 3b] Extracting Facenet512 embedding (TTA)...")
            facenet_emb = extract_embedding_with_tta(processed_face, "Facenet512")
            result["facenet"] = facenet_emb
            facenet_ok = True
            print(f"    ✅ Facenet512: {len(facenet_emb)}-D, normalized")
        except Exception as e:
            print(f"  [Step 3b] ❌ Facenet512 failed: {e}")
            traceback.print_exc()
    else:
        print("  [Step 3b] ⚠️  Facenet512 not initialized — skipping")

    # ── 6. Determine overall success ────────────────────────────────────────
    if not arcface_ok and not facenet_ok:
        result["error"] = (
            "Both ArcFace and Facenet512 embedding extraction failed. "
            "Check model weights and server logs."
        )
        print(f"[EmbeddingService] ❌ {result['error']}")
        return result

    if not arcface_ok:
        print("[EmbeddingService] ⚠️  ArcFace unavailable — using Facenet512 only")
    if not facenet_ok:
        print("[EmbeddingService] ⚠️  Facenet512 unavailable — using ArcFace only")

    result["success"] = True
    result["tta_applied"] = True
    print("[EmbeddingService] ✅ Dual embedding extraction complete")
    return result


def extract_embedding(image_path: str, is_sketch: bool = False) -> np.ndarray:
    """
    Legacy single-embedding API — returns ArcFace embedding (or Facenet as fallback).
    Use extract_dual_embeddings() for new code.
    """
    res = extract_dual_embeddings(image_path, is_sketch)
    if res and res["success"]:
        return res["arcface"] if res["arcface"] is not None else res["facenet"]
    return None
