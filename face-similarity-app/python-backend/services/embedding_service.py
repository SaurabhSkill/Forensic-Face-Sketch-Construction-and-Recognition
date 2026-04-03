"""
embedding_service.py — InsightFace-only face embedding service.

Model:
  - InsightFace ArcFace R50 (w600k_r50.onnx) → 512-D L2-normalized

Key guarantees:
  - Model loaded ONCE at startup (singleton, thread-safe)
  - Failure → controlled error dict (no unhandled exception)
  - TTA: 3 augmentations averaged
  - All steps logged for debugging
"""

import os
import base64
import threading
import traceback

import cv2
import numpy as np
import requests

from models.insightface_model import (
    initialize_insightface_model,
    extract_insightface_embedding,
    normalize_embedding as normalize_insightface,
    is_insightface_initialized,
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
    Load InsightFace at server startup.
    Thread-safe, idempotent. Returns True if model loaded.
    """
    global MODEL_INITIALIZED

    if MODEL_INITIALIZED:
        return True

    with _INIT_LOCK:
        if MODEL_INITIALIZED:
            return True

        print("\n" + "=" * 60)
        print("  INITIALIZING FACE RECOGNITION MODEL")
        print("=" * 60)

        insightface_ok = _init_insightface_safe()

        if not insightface_ok:
            print("[EmbeddingService] [FAIL] CRITICAL: InsightFace failed to load.")

        MODEL_INITIALIZED = True
        print("=" * 60)
        print(f"  InsightFace : {'[OK] ready' if insightface_ok else '[FAIL] unavailable'}")
        print("=" * 60 + "\n")
        return insightface_ok


def is_models_initialized() -> bool:
    return MODEL_INITIALIZED


# ---------------------------------------------------------------------------
# Public warmup — call once at server startup
# ---------------------------------------------------------------------------

def warmup_models() -> dict:
    """
    Run a dummy inference through InsightFace to ensure the ONNX graph is
    compiled before the first real request arrives.

    Never raises — all failures are caught and logged.

    Returns:
        dict: {'insightface': bool}
    """
    results = {"insightface": False}

    print("\n" + "=" * 60)
    print("  MODEL WARMUP — preloading InsightFace ONNX graph")
    print("=" * 60)

    if is_insightface_initialized():
        print("[Warmup] Warming up InsightFace (ArcFace)...")
        try:
            import onnxruntime as ort
            from models.insightface_model import ONNX_PATH

            sess_opts = ort.SessionOptions()
            sess_opts.log_severity_level = 3
            sess = ort.InferenceSession(
                ONNX_PATH,
                sess_options=sess_opts,
                providers=["CPUExecutionProvider"],
            )
            input_name  = sess.get_inputs()[0].name
            output_name = sess.get_outputs()[0].name

            dummy = np.zeros((1, 3, 112, 112), dtype=np.float32)
            out = sess.run([output_name], {input_name: dummy})

            print(f"[Warmup] [OK] InsightFace ready — output shape: {out[0].shape}")
            results["insightface"] = True

        except Exception as e:
            print(f"[Warmup] [WARN] InsightFace warmup failed (non-fatal): {e}")
    else:
        print("[Warmup] InsightFace not initialized — skipping")

    print("=" * 60)
    print(f"  InsightFace : {'[OK] warm' if results['insightface'] else '[SKIP/FAIL]'}")
    print("=" * 60 + "\n")

    return results


# ---------------------------------------------------------------------------
# Private init helper
# ---------------------------------------------------------------------------

def _init_insightface_safe() -> bool:
    try:
        ok = initialize_insightface_model()
        if not ok:
            print("[InsightFace] [ERROR] initialize_insightface_model() returned False — model unavailable")
        return ok
    except RuntimeError as e:
        print(f"[InsightFace] [ERROR] Initialization failed with RuntimeError:")
        print(f"[InsightFace] [ERROR] {e}")
        print("[InsightFace] [ERROR] Fix: ensure w600k_r50.onnx (~166 MB) is present.")
        from models.insightface_model import ONNX_PATH
        print(f"[InsightFace] [ERROR]   {ONNX_PATH}")
        return False
    except Exception as e:
        print(f"[InsightFace] [ERROR] Unexpected exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# TTA augmentations
# ---------------------------------------------------------------------------

def generate_tta_augmentations(aligned_face: np.ndarray) -> list:
    """Generate 3 TTA versions of an aligned face."""
    try:
        h, w = aligned_face.shape[:2]
        augmented = [aligned_face.copy()]

        try:
            augmented.append(cv2.flip(aligned_face, 1))
        except Exception as e:
            print(f"[TTA] Flip failed (skipped): {e}")

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
# Single-model extraction
# ---------------------------------------------------------------------------

def _extract_insightface_single(face_arr: np.ndarray) -> np.ndarray:
    """Extract InsightFace embedding from a single face array."""
    if not is_insightface_initialized():
        raise RuntimeError("InsightFace model not initialized")
    emb = extract_insightface_embedding(face_arr)
    return normalize_insightface(emb)


# ---------------------------------------------------------------------------
# External Facenet microservice
# ---------------------------------------------------------------------------

# Reads FACENET_API_URL from environment.
# Local dev  → default: http://localhost:8001
# Docker     → set FACENET_API_URL=http://facenet:8001 via docker-compose
FACENET_API_URL  = os.environ.get("FACENET_API_URL", "http://localhost:8001")
_FACENET_TIMEOUT = 10   # seconds per attempt
_FACENET_RETRIES = 1    # one retry on failure

print(f"[FacenetAPI] Using URL: {FACENET_API_URL}", flush=True)


def get_facenet_embedding_from_service(face_arr: np.ndarray) -> np.ndarray:
    """
    Call the external Facenet microservice (POST /embedding) and return
    a 512-D L2-normalized embedding.

    - Sends the face as a base64-encoded JPEG
    - Timeout: 10s per attempt
    - Retries: 1 (2 total attempts)
    - Returns None on failure — caller continues with InsightFace only

    Logs:
        [Facenet API] calling...
        [Facenet API] success
        [Facenet API] failed - fallback
    """
    # Resize to 160x160 (Facenet input size) before encoding
    resized = cv2.resize(face_arr, (160, 160), interpolation=cv2.INTER_LANCZOS4)

    ok, buf = cv2.imencode(".jpg", resized)
    if not ok:
        print("[Facenet API] failed - fallback (cv2.imencode failed)", flush=True)
        return None

    image_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    url = f"{FACENET_API_URL}/embedding"

    for attempt in range(1, _FACENET_RETRIES + 2):   # 1 + 1 retry = 2 total
        try:
            print(f"[Facenet API] calling... (attempt {attempt})", flush=True)
            resp = requests.post(
                url,
                json={"image_base64": image_b64},
                timeout=_FACENET_TIMEOUT,
            )
            resp.raise_for_status()

            data = resp.json()
            emb  = np.array(data["embedding"], dtype=np.float32)

            if emb.shape[0] != 512:
                raise ValueError(f"Unexpected embedding dim: {emb.shape[0]}")

            # L2 normalize
            norm = np.linalg.norm(emb)
            emb  = emb / norm if norm > 0 else emb

            print("[Facenet API] success", flush=True)
            return emb

        except Exception as exc:
            print(f"[Facenet API] attempt {attempt} failed: {exc}", flush=True)
            if attempt > _FACENET_RETRIES:
                print("[Facenet API] failed - fallback (InsightFace only)", flush=True)
                return None

    return None


# ---------------------------------------------------------------------------
# TTA-averaged extraction (public)
# ---------------------------------------------------------------------------

def extract_embedding_with_tta(processed_face: np.ndarray, model_name: str) -> np.ndarray:
    """
    Extract InsightFace embedding with TTA averaging.
    model_name must be 'InsightFace'.
    """
    if model_name != "InsightFace":
        raise ValueError(f"Unsupported model: {model_name}. Only InsightFace is supported.")

    augmented_faces = generate_tta_augmentations(processed_face)
    embeddings = []

    for idx, aug_face in enumerate(augmented_faces):
        try:
            emb = _extract_insightface_single(aug_face)
            embeddings.append(emb)
            print(f"    [TTA] InsightFace aug {idx}: [OK] ({len(emb)}-D)")
        except Exception as e:
            print(f"    [TTA] InsightFace aug {idx}: [WARN] skipped - {e}")

    if embeddings:
        avg = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg)
        avg = avg / norm if norm > 0 else avg
        print(f"    [TTA] InsightFace: averaged {len(embeddings)} augmentation(s)")
        return avg

    # All TTA failed — try plain extraction once
    print("    [TTA] InsightFace: all augmentations failed, trying plain extraction...")
    return _extract_insightface_single(processed_face)


# ---------------------------------------------------------------------------
# Face detection + alignment
# ---------------------------------------------------------------------------

def _detect_and_align_face(image_path: str, enforce_detection: bool = False) -> np.ndarray:
    """
    Detect and align the largest face using OpenCV Haar cascade.
    Returns uint8 BGR face crop resized to 112x112 (InsightFace native size).
    Falls back to full image if no face detected (enforce_detection=False).
    No DeepFace / TensorFlow dependency.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"cv2.imread() failed: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        if enforce_detection:
            raise ValueError(f"No face detected in: {image_path}")
        print(f"    [Detect] No face detected — using full image as fallback: {image_path}")
        aligned = img
    else:
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        pad = int(min(w, h) * 0.2)
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img.shape[1], x + w + pad)
        y2 = min(img.shape[0], y + h + pad)
        aligned = img[y1:y2, x1:x2]

    aligned = cv2.resize(aligned, (112, 112), interpolation=cv2.INTER_LANCZOS4)
    print(f"    [Detect] Face aligned: shape={aligned.shape}, dtype={aligned.dtype}")
    return aligned


# ---------------------------------------------------------------------------
# Image preprocessing
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
# Adaptive Canny threshold selection
# ---------------------------------------------------------------------------

def _select_best_canny_threshold(
    aligned_face: np.ndarray,
    reference_embedding: np.ndarray,
) -> tuple:
    """Pick the Canny threshold whose InsightFace embedding best matches reference."""
    if not is_insightface_initialized():
        print("    [AdaptiveCanny] InsightFace unavailable, using default (50, 150)")
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
    use_tta: bool = True,
) -> dict:
    """
    Extract InsightFace embedding from an image.

    Args:
        use_tta: If True, apply TTA (3 augmentations averaged). Set False for
                 database/reference images to speed up processing.

    Returns dict with keys:
        success, insightface, facenet (always None), aligned_face,
        tta_applied, tta_augmentations, best_threshold, error

    Note: 'facenet' key is kept for API compatibility but is always None.
    """
    result = {
        "success":          False,
        "insightface":      None,
        "facenet":          None,   # kept for API compatibility
        "aligned_face":     None,
        "tta_applied":      False,
        "tta_augmentations": 3,
        "best_threshold":   None,
        "error":            None,
    }

    if not is_insightface_initialized():
        msg = "InsightFace model not available. Check server startup logs."
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
        aligned_face = _detect_and_align_face(image_path, enforce_detection=False)
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

    # Step 3: InsightFace embedding (with optional TTA)
    try:
        if use_tta:
            print("  [Step 3] Extracting InsightFace embedding (TTA)...")
            insightface_emb = extract_embedding_with_tta(processed_face, "InsightFace")
        else:
            print("  [Step 3] Extracting InsightFace embedding (no TTA, cached/reference)...")
            insightface_emb = _extract_insightface_single(processed_face)
        result["insightface"] = insightface_emb
        result["tta_applied"] = use_tta
        print(f"    [OK] InsightFace: {len(insightface_emb)}-D, normalized")
    except Exception as e:
        result["error"] = f"InsightFace embedding extraction failed: {e}"
        print(f"  [Step 3] [FAIL] InsightFace failed: {e}")
        traceback.print_exc()
        return result

    # Step 4: Facenet embedding via external microservice (optional — never blocks)
    facenet_emb = get_facenet_embedding_from_service(aligned_face)
    if facenet_emb is not None:
        result["facenet"] = facenet_emb
        print(f"    [OK] Facenet (API): {len(facenet_emb)}-D, normalized")
    else:
        print("    [INFO] Facenet unavailable — continuing with InsightFace only")

    result["success"]     = True
    result["tta_applied"] = True
    print("[EmbeddingService] [OK] Embedding extraction complete")
    return result


def extract_embedding(image_path: str, is_sketch: bool = False) -> np.ndarray:
    """Legacy single-embedding API. Returns InsightFace embedding."""
    res = extract_dual_embeddings(image_path, is_sketch)
    if res and res["success"]:
        return res["insightface"]
    return None
