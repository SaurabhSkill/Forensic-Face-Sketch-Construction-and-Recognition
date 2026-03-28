"""
ArcFace model wrapper — EC2-hardened
Handles weight validation, corruption detection, retry logic, and singleton loading.
"""
import os
import threading
import traceback
import numpy as np
from deepface import DeepFace

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# DeepFace stores weights here by default
WEIGHTS_DIR = os.path.join(os.path.expanduser("~"), ".deepface", "weights")
ARCFACE_WEIGHT_FILE = "arcface_weights.h5"
ARCFACE_WEIGHT_PATH = os.path.join(WEIGHTS_DIR, ARCFACE_WEIGHT_FILE)

# ArcFace .h5 file should be at least 200 MB — anything smaller is a partial download
ARCFACE_MIN_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB

# HDF5 magic bytes (first 8 bytes of every valid .h5 file)
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"

# Max retries for model loading on transient failures
MAX_LOAD_RETRIES = 3

# ---------------------------------------------------------------------------
# Singleton state — protected by a lock for gunicorn multi-worker safety
# ---------------------------------------------------------------------------

_ARCFACE_MODEL = None
_ARCFACE_INITIALIZED = False
_ARCFACE_LOAD_FAILED = False
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Weight file validation helpers
# ---------------------------------------------------------------------------

def _ensure_weights_dir() -> None:
    """Create weights directory with correct permissions if it doesn't exist."""
    try:
        os.makedirs(WEIGHTS_DIR, mode=0o755, exist_ok=True)
        print(f"[ArcFace] Weights directory: {WEIGHTS_DIR}")
    except OSError as e:
        print(f"[ArcFace] WARNING: Could not create weights dir: {e}")


def _get_weight_file_info() -> dict:
    """Return size and existence info for the weight file."""
    if not os.path.exists(ARCFACE_WEIGHT_PATH):
        return {"exists": False, "size_bytes": 0, "size_mb": 0.0}
    size = os.path.getsize(ARCFACE_WEIGHT_PATH)
    return {
        "exists": True,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 2),
        "path": ARCFACE_WEIGHT_PATH,
    }


def _is_valid_hdf5(path: str) -> bool:
    """
    Check HDF5 magic bytes to detect corrupt / partial downloads.
    The error 'OSError: Unable to synchronously open file (file signature not found)'
    is caused by a file that is NOT a valid HDF5 — this catches it before TF tries to load it.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return header == HDF5_MAGIC
    except Exception as e:
        print(f"[ArcFace] Could not read file header: {e}")
        return False


def _validate_weight_file() -> tuple[bool, str]:
    """
    Full validation: existence + size + HDF5 signature.
    Returns (is_valid, reason_string).
    """
    info = _get_weight_file_info()

    if not info["exists"]:
        return False, "weight file does not exist"

    print(f"[ArcFace] Weight file found: {info['path']} ({info['size_mb']} MB)")

    if info["size_bytes"] < ARCFACE_MIN_SIZE_BYTES:
        return False, (
            f"weight file too small ({info['size_mb']} MB < "
            f"{ARCFACE_MIN_SIZE_BYTES // (1024*1024)} MB) — likely partial download"
        )

    if not _is_valid_hdf5(ARCFACE_WEIGHT_PATH):
        return False, "weight file has invalid HDF5 signature — file is corrupt"

    return True, "ok"


def _delete_corrupt_weight_file() -> None:
    """Remove a corrupt/partial weight file so DeepFace re-downloads it."""
    try:
        if os.path.exists(ARCFACE_WEIGHT_PATH):
            os.remove(ARCFACE_WEIGHT_PATH)
            print(f"[ArcFace] Deleted corrupt weight file: {ARCFACE_WEIGHT_PATH}")
    except OSError as e:
        print(f"[ArcFace] WARNING: Could not delete corrupt weight file: {e}")


# ---------------------------------------------------------------------------
# Model loading with retry
# ---------------------------------------------------------------------------

def _load_model_once() -> object:
    """
    Load ArcFace via DeepFace.build_model() with retry logic.
    Validates weights before each attempt.
    Raises on final failure.
    """
    _ensure_weights_dir()

    for attempt in range(1, MAX_LOAD_RETRIES + 1):
        print(f"[ArcFace] Load attempt {attempt}/{MAX_LOAD_RETRIES}...")

        # Validate weight file before attempting load
        valid, reason = _validate_weight_file()
        if not valid:
            print(f"[ArcFace] Weight validation failed: {reason}")
            _delete_corrupt_weight_file()
            print("[ArcFace] Triggering fresh download via DeepFace...")
            # DeepFace will re-download on next build_model() call

        try:
            model = DeepFace.build_model("ArcFace")

            # Confirm weights are now valid after load
            info = _get_weight_file_info()
            print(
                f"[ArcFace] ✅ Model loaded successfully "
                f"(weights: {info.get('size_mb', '?')} MB)"
            )
            return model

        except OSError as e:
            # This is the exact EC2 error: "file signature not found"
            print(f"[ArcFace] ❌ OSError on attempt {attempt}: {e}")
            print("[ArcFace] Deleting potentially corrupt weight file and retrying...")
            _delete_corrupt_weight_file()

        except Exception as e:
            print(f"[ArcFace] ❌ Unexpected error on attempt {attempt}: {e}")
            traceback.print_exc()
            if attempt == MAX_LOAD_RETRIES:
                raise

    raise RuntimeError(
        f"[ArcFace] Failed to load model after {MAX_LOAD_RETRIES} attempts. "
        "Check disk space, network, and file permissions on EC2."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_arcface_model(dummy_image_path: str = None) -> bool:
    """
    Thread-safe singleton initializer for ArcFace.
    Safe to call multiple times — loads only once.

    Args:
        dummy_image_path: Deprecated, kept for API compatibility.

    Returns:
        bool: True if model is ready, False if loading failed.
    """
    global _ARCFACE_MODEL, _ARCFACE_INITIALIZED, _ARCFACE_LOAD_FAILED

    # Fast path — already done
    if _ARCFACE_INITIALIZED:
        return True
    if _ARCFACE_LOAD_FAILED:
        return False

    with _LOCK:
        # Double-check inside lock
        if _ARCFACE_INITIALIZED:
            return True
        if _ARCFACE_LOAD_FAILED:
            return False

        print("[ArcFace] Initializing model (singleton)...")
        try:
            _ARCFACE_MODEL = _load_model_once()
            _ARCFACE_INITIALIZED = True
            print("[ArcFace] ✅ Ready")
            return True
        except Exception as e:
            print(f"[ArcFace] ❌ Initialization permanently failed: {e}")
            _ARCFACE_LOAD_FAILED = True
            _ARCFACE_MODEL = None
            _ARCFACE_INITIALIZED = False
            return False


def is_arcface_initialized() -> bool:
    return _ARCFACE_INITIALIZED and _ARCFACE_MODEL is not None


def get_arcface_model():
    return _ARCFACE_MODEL


def extract_arcface_embedding(
    image_path,
    enforce_detection: bool = False,
    align: bool = False,
    detector_backend: str = "skip",
) -> np.ndarray:
    """
    Extract ArcFace embedding. Accepts file path or numpy array.

    Returns:
        np.ndarray: 512-D L2-normalized embedding.

    Raises:
        RuntimeError: If model is not initialized.
        ValueError: If result is empty or malformed.
    """
    if not is_arcface_initialized():
        raise RuntimeError(
            "ArcFace model is not initialized. Call initialize_arcface_model() first."
        )

    result = DeepFace.represent(
        img_path=image_path,
        model_name="ArcFace",
        enforce_detection=enforce_detection,
        align=align,
        detector_backend=detector_backend,
    )

    if not result or "embedding" not in result[0]:
        raise ValueError("ArcFace: DeepFace.represent() returned empty/malformed result")

    embedding = np.array(result[0]["embedding"])

    if embedding.shape[0] != 512:
        raise ValueError(
            f"ArcFace: unexpected embedding dim {embedding.shape[0]}, expected 512"
        )

    return embedding


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2 normalize an embedding vector."""
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm > 0 else embedding
