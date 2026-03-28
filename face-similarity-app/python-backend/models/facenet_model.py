"""
Facenet512 model wrapper - EC2-hardened
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

WEIGHTS_DIR = os.path.join(os.path.expanduser("~"), ".deepface", "weights")
FACENET_WEIGHT_FILE = "facenet512_weights.h5"
FACENET_WEIGHT_PATH = os.path.join(WEIGHTS_DIR, FACENET_WEIGHT_FILE)

# Facenet512 .h5 should be at least 80 MB
FACENET_MIN_SIZE_BYTES = 80 * 1024 * 1024  # 80 MB

# HDF5 magic bytes
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"

MAX_LOAD_RETRIES = 3

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------

_FACENET_MODEL = None
_FACENET_INITIALIZED = False
_FACENET_LOAD_FAILED = False
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Weight file validation helpers
# ---------------------------------------------------------------------------

def _ensure_weights_dir() -> None:
    try:
        os.makedirs(WEIGHTS_DIR, mode=0o755, exist_ok=True)
        print(f"[Facenet512] Weights directory: {WEIGHTS_DIR}")
    except OSError as e:
        print(f"[Facenet512] WARNING: Could not create weights dir: {e}")


def _get_weight_file_info() -> dict:
    if not os.path.exists(FACENET_WEIGHT_PATH):
        return {"exists": False, "size_bytes": 0, "size_mb": 0.0}
    size = os.path.getsize(FACENET_WEIGHT_PATH)
    return {
        "exists": True,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 2),
        "path": FACENET_WEIGHT_PATH,
    }


def _is_valid_hdf5(path: str) -> bool:
    """Check HDF5 magic bytes - catches the EC2 'file signature not found' error."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        return header == HDF5_MAGIC
    except Exception as e:
        print(f"[Facenet512] Could not read file header: {e}")
        return False


def _validate_weight_file() -> tuple[bool, str]:
    info = _get_weight_file_info()

    if not info["exists"]:
        return False, "weight file does not exist"

    print(f"[Facenet512] Weight file found: {info['path']} ({info['size_mb']} MB)")

    if info["size_bytes"] < FACENET_MIN_SIZE_BYTES:
        return False, (
            f"weight file too small ({info['size_mb']} MB < "
            f"{FACENET_MIN_SIZE_BYTES // (1024*1024)} MB) - likely partial download"
        )

    if not _is_valid_hdf5(FACENET_WEIGHT_PATH):
        return False, "weight file has invalid HDF5 signature - file is corrupt"

    return True, "ok"


def _delete_corrupt_weight_file() -> None:
    try:
        if os.path.exists(FACENET_WEIGHT_PATH):
            os.remove(FACENET_WEIGHT_PATH)
            print(f"[Facenet512] Deleted corrupt weight file: {FACENET_WEIGHT_PATH}")
    except OSError as e:
        print(f"[Facenet512] WARNING: Could not delete corrupt weight file: {e}")


# ---------------------------------------------------------------------------
# Model loading with retry
# ---------------------------------------------------------------------------

def _load_model_once() -> object:
    """
    Load Facenet512 via DeepFace.build_model() with retry + weight validation.
    Raises on final failure.
    """
    _ensure_weights_dir()

    for attempt in range(1, MAX_LOAD_RETRIES + 1):
        print(f"[Facenet512] Load attempt {attempt}/{MAX_LOAD_RETRIES}...")

        valid, reason = _validate_weight_file()
        if not valid:
            print(f"[Facenet512] Weight validation failed: {reason}")
            _delete_corrupt_weight_file()
            print("[Facenet512] Triggering fresh download via DeepFace...")

        try:
            model = DeepFace.build_model("Facenet512")

            info = _get_weight_file_info()
            print(
                f"[Facenet512] [OK] Model loaded successfully "
                f"(weights: {info.get('size_mb', '?')} MB)"
            )
            return model

        except OSError as e:
            print(f"[Facenet512] [FAIL] OSError on attempt {attempt}: {e}")
            print("[Facenet512] Deleting potentially corrupt weight file and retrying...")
            _delete_corrupt_weight_file()

        except Exception as e:
            print(f"[Facenet512] [FAIL] Unexpected error on attempt {attempt}: {e}")
            traceback.print_exc()
            if attempt == MAX_LOAD_RETRIES:
                raise

    raise RuntimeError(
        f"[Facenet512] Failed to load model after {MAX_LOAD_RETRIES} attempts. "
        "Check disk space, network, and file permissions on EC2."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_facenet_model(dummy_image_path: str = None) -> bool:
    """
    Thread-safe singleton initializer for Facenet512.
    Safe to call multiple times - loads only once.

    Returns:
        bool: True if model is ready, False if loading failed.
    """
    global _FACENET_MODEL, _FACENET_INITIALIZED, _FACENET_LOAD_FAILED

    if _FACENET_INITIALIZED:
        return True
    if _FACENET_LOAD_FAILED:
        return False

    with _LOCK:
        if _FACENET_INITIALIZED:
            return True
        if _FACENET_LOAD_FAILED:
            return False

        print("[Facenet512] Initializing model (singleton)...")
        try:
            _FACENET_MODEL = _load_model_once()
            _FACENET_INITIALIZED = True
            print("[Facenet512] [OK] Ready")
            return True
        except Exception as e:
            print(f"[Facenet512] [FAIL] Initialization permanently failed: {e}")
            _FACENET_LOAD_FAILED = True
            _FACENET_MODEL = None
            _FACENET_INITIALIZED = False
            return False


def is_facenet_initialized() -> bool:
    return _FACENET_INITIALIZED and _FACENET_MODEL is not None


def get_facenet_model():
    return _FACENET_MODEL


def extract_facenet_embedding(
    image_path,
    enforce_detection: bool = False,
    align: bool = False,
    detector_backend: str = "skip",
) -> np.ndarray:
    """
    Extract Facenet512 embedding. Accepts file path or numpy array.

    Returns:
        np.ndarray: 512-D L2-normalized embedding.

    Raises:
        RuntimeError: If model is not initialized.
        ValueError: If result is empty or malformed.
    """
    if not is_facenet_initialized():
        raise RuntimeError(
            "Facenet512 model is not initialized. Call initialize_facenet_model() first."
        )

    result = DeepFace.represent(
        img_path=image_path,
        model_name="Facenet512",
        enforce_detection=enforce_detection,
        align=align,
        detector_backend=detector_backend,
    )

    if not result or "embedding" not in result[0]:
        raise ValueError(
            "Facenet512: DeepFace.represent() returned empty/malformed result"
        )

    embedding = np.array(result[0]["embedding"])

    if embedding.shape[0] != 512:
        raise ValueError(
            f"Facenet512: unexpected embedding dim {embedding.shape[0]}, expected 512"
        )

    return embedding


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2 normalize an embedding vector."""
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm > 0 else embedding
