"""
ArcFace model wrapper - production hardened.

Download priority:
  1. Already on disk and valid  -> use immediately
  2. S3 self-hosted bucket      -> download from s3://bucket/models/arcface_weights.h5
  3. Google Drive (legacy)      -> gdown with ID 1LVB3CdVejpmGHM28BpqqkbZP5hDEcdZY
  4. GitHub releases (legacy)   -> may be 404, kept as last resort

Hard-fail policy:
  If the model cannot be loaded after all attempts, the server logs a clear
  CRITICAL error and raises RuntimeError. The caller (embedding_service.py)
  decides whether to continue with Facenet-only or abort.
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
ARCFACE_WEIGHT_FILE = "arcface_weights.h5"
ARCFACE_WEIGHT_PATH = os.path.join(WEIGHTS_DIR, ARCFACE_WEIGHT_FILE)

# Complete arcface_weights.h5 is ~130 MB
ARCFACE_MIN_SIZE_BYTES = 120 * 1024 * 1024  # 120 MB

HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
MAX_LOAD_RETRIES = 3

# Google Drive file ID (from deepface 0.0.79 source — legacy fallback)
ARCFACE_GDRIVE_ID = "1LVB3CdVejpmGHM28BpqqkbZP5hDEcdZY"

# GitHub URL (currently 404 — kept as last resort)
ARCFACE_GITHUB_URL = (
    "https://github.com/serengil/deepface_models/releases/download/v1.0/arcface_weights.h5"
)

# S3 key where we self-host the weights
ARCFACE_S3_KEY = "models/arcface_weights.h5"

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------

_ARCFACE_MODEL = None
_ARCFACE_INITIALIZED = False
_ARCFACE_LOAD_FAILED = False
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Weight file helpers
# ---------------------------------------------------------------------------

def _ensure_weights_dir() -> None:
    try:
        os.makedirs(WEIGHTS_DIR, mode=0o755, exist_ok=True)
    except OSError as e:
        print(f"[ArcFace] WARNING: Could not create weights dir: {e}")


def _get_weight_file_info() -> dict:
    if not os.path.exists(ARCFACE_WEIGHT_PATH):
        return {"exists": False, "size_bytes": 0, "size_mb": 0.0}
    size = os.path.getsize(ARCFACE_WEIGHT_PATH)
    return {"exists": True, "size_bytes": size, "size_mb": round(size / (1024 * 1024), 2)}


def _is_valid_hdf5(path: str) -> bool:
    """Check HDF5 magic bytes AND that h5py can open the file (catches truncated files)."""
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        if header != HDF5_MAGIC:
            return False
        # Full open check — catches truncated files that have valid magic
        import h5py
        with h5py.File(path, "r"):
            pass
        return True
    except Exception:
        return False


def _validate_weight_file() -> tuple:
    """Returns (is_valid: bool, reason: str)."""
    info = _get_weight_file_info()
    if not info["exists"]:
        return False, "weight file does not exist"
    print(f"[ArcFace] Weight file: {ARCFACE_WEIGHT_PATH} ({info['size_mb']} MB)")
    if info["size_bytes"] < ARCFACE_MIN_SIZE_BYTES:
        return False, (
            f"too small ({info['size_mb']} MB < {ARCFACE_MIN_SIZE_BYTES//(1024*1024)} MB)"
            " - incomplete download"
        )
    if not _is_valid_hdf5(ARCFACE_WEIGHT_PATH):
        return False, "invalid or truncated HDF5 file"
    return True, "ok"


def _delete_weight_file() -> None:
    try:
        if os.path.exists(ARCFACE_WEIGHT_PATH):
            os.remove(ARCFACE_WEIGHT_PATH)
            print(f"[ArcFace] Deleted: {ARCFACE_WEIGHT_PATH}")
    except OSError as e:
        print(f"[ArcFace] WARNING: Could not delete weight file: {e}")


# ---------------------------------------------------------------------------
# Download strategies (tried in order)
# ---------------------------------------------------------------------------

def _download_from_s3() -> bool:
    """Download from the project's own S3 bucket — most reliable source."""
    try:
        import boto3
        from dotenv import load_dotenv
        load_dotenv()

        bucket = os.environ.get("AWS_S3_BUCKET_NAME")
        region = os.environ.get("AWS_REGION", "us-east-1")
        key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")

        if not all([bucket, key_id, secret]):
            print("[ArcFace] S3 credentials not configured, skipping S3 download")
            return False

        s3 = boto3.client(
            "s3", region_name=region,
            aws_access_key_id=key_id,
            aws_secret_access_key=secret,
        )

        # Check the file exists in S3 and is large enough
        try:
            obj = s3.head_object(Bucket=bucket, Key=ARCFACE_S3_KEY)
            s3_size = obj["ContentLength"]
            s3_size_mb = s3_size / (1024 * 1024)
            print(f"[ArcFace] S3 object found: {ARCFACE_S3_KEY} ({s3_size_mb:.1f} MB)")
            if s3_size < ARCFACE_MIN_SIZE_BYTES:
                print(f"[ArcFace] S3 file too small ({s3_size_mb:.1f} MB) - skipping")
                return False
        except Exception as e:
            print(f"[ArcFace] S3 object not found or inaccessible: {e}")
            return False

        _ensure_weights_dir()
        tmp_path = ARCFACE_WEIGHT_PATH + ".s3download"
        print(f"[ArcFace] Downloading from S3: s3://{bucket}/{ARCFACE_S3_KEY}")

        s3.download_file(bucket, ARCFACE_S3_KEY, tmp_path)

        if not os.path.exists(tmp_path):
            print("[ArcFace] S3 download produced no file")
            return False

        downloaded_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        print(f"[ArcFace] S3 download complete: {downloaded_mb:.1f} MB")

        if not _is_valid_hdf5(tmp_path):
            print("[ArcFace] S3 file is not a valid HDF5")
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False

        if os.path.exists(ARCFACE_WEIGHT_PATH):
            os.remove(ARCFACE_WEIGHT_PATH)
        os.rename(tmp_path, ARCFACE_WEIGHT_PATH)
        print(f"[ArcFace] [OK] Weights installed from S3: {downloaded_mb:.1f} MB")
        return True

    except Exception as e:
        print(f"[ArcFace] S3 download failed: {e}")
        return False


def _download_from_gdrive() -> bool:
    """Download from Google Drive (legacy — may be rate-limited)."""
    try:
        import gdown
        _ensure_weights_dir()
        tmp_path = ARCFACE_WEIGHT_PATH + ".gdrive"
        url = f"https://drive.google.com/uc?id={ARCFACE_GDRIVE_ID}"
        print(f"[ArcFace] Trying Google Drive: {ARCFACE_GDRIVE_ID}")
        gdown.download(url, tmp_path, quiet=False, fuzzy=True)

        if not os.path.exists(tmp_path):
            return False

        size_mb = os.path.getsize(tmp_path) / (1024 * 1024)
        if size_mb < 100 or not _is_valid_hdf5(tmp_path):
            print(f"[ArcFace] GDrive result invalid ({size_mb:.1f} MB)")
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False

        if os.path.exists(ARCFACE_WEIGHT_PATH):
            os.remove(ARCFACE_WEIGHT_PATH)
        os.rename(tmp_path, ARCFACE_WEIGHT_PATH)
        print(f"[ArcFace] [OK] Weights installed from GDrive: {size_mb:.1f} MB")
        return True

    except Exception as e:
        print(f"[ArcFace] GDrive download failed: {e}")
        return False


def _download_from_github() -> bool:
    """Download from GitHub releases (currently 404 — last resort)."""
    try:
        import urllib.request
        _ensure_weights_dir()
        tmp_path = ARCFACE_WEIGHT_PATH + ".ghdownload"
        print(f"[ArcFace] Trying GitHub: {ARCFACE_GITHUB_URL}")

        req = urllib.request.Request(
            ARCFACE_GITHUB_URL,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/octet-stream"},
        )
        with urllib.request.urlopen(req, timeout=300) as resp, open(tmp_path, "wb") as f:
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)

        size_mb = total / (1024 * 1024)
        if total < ARCFACE_MIN_SIZE_BYTES or not _is_valid_hdf5(tmp_path):
            print(f"[ArcFace] GitHub result invalid ({size_mb:.1f} MB)")
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return False

        if os.path.exists(ARCFACE_WEIGHT_PATH):
            os.remove(ARCFACE_WEIGHT_PATH)
        os.rename(tmp_path, ARCFACE_WEIGHT_PATH)
        print(f"[ArcFace] [OK] Weights installed from GitHub: {size_mb:.1f} MB")
        return True

    except Exception as e:
        print(f"[ArcFace] GitHub download failed: {e}")
        return False


def ensure_arcface_weights() -> bool:
    """
    Ensure arcface_weights.h5 is present, valid, and complete.
    Tries: disk check → S3 → GDrive → GitHub.
    Returns True if weights are ready, False if all sources failed.
    """
    valid, reason = _validate_weight_file()
    if valid:
        print(f"[ArcFace] Weights already valid on disk")
        return True

    print(f"[ArcFace] Weights not ready: {reason}")
    _delete_weight_file()

    for name, fn in [
        ("S3 (self-hosted)", _download_from_s3),
        ("Google Drive", _download_from_gdrive),
        ("GitHub releases", _download_from_github),
    ]:
        print(f"[ArcFace] Trying download source: {name}")
        if fn():
            valid, reason = _validate_weight_file()
            if valid:
                return True
            print(f"[ArcFace] Post-download validation failed: {reason}")
            _delete_weight_file()

    return False


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _load_model_once() -> object:
    """
    Ensure weights exist, then load via DeepFace.build_model().
    Raises RuntimeError if weights cannot be obtained or model fails to load.
    """
    _ensure_weights_dir()

    weights_ready = ensure_arcface_weights()
    if not weights_ready:
        raise RuntimeError(
            "[ArcFace] CRITICAL: Could not obtain arcface_weights.h5 from any source.\n"
            "  Manual fix: download the file (~130 MB) and place it at:\n"
            f"  {ARCFACE_WEIGHT_PATH}\n"
            "  Then upload to S3: python upload_arcface_weights.py"
        )

    for attempt in range(1, MAX_LOAD_RETRIES + 1):
        print(f"[ArcFace] Load attempt {attempt}/{MAX_LOAD_RETRIES}...")
        try:
            model = DeepFace.build_model("ArcFace")
            info = _get_weight_file_info()
            print(f"[ArcFace] [OK] Model loaded ({info.get('size_mb', '?')} MB)")
            return model

        except OSError as e:
            print(f"[ArcFace] OSError on attempt {attempt}: {e}")
            # File became corrupt between validation and load — re-download
            _delete_weight_file()
            if not ensure_arcface_weights():
                break

        except Exception as e:
            print(f"[ArcFace] Unexpected error on attempt {attempt}: {e}")
            traceback.print_exc()
            if attempt == MAX_LOAD_RETRIES:
                raise

    raise RuntimeError(
        f"[ArcFace] Failed to load model after {MAX_LOAD_RETRIES} attempts."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_arcface_model(dummy_image_path: str = None) -> bool:
    """
    Thread-safe singleton initializer. Loads only once.
    Returns True if model is ready, False if loading failed.
    """
    global _ARCFACE_MODEL, _ARCFACE_INITIALIZED, _ARCFACE_LOAD_FAILED

    if _ARCFACE_INITIALIZED:
        return True
    if _ARCFACE_LOAD_FAILED:
        return False

    with _LOCK:
        if _ARCFACE_INITIALIZED:
            return True
        if _ARCFACE_LOAD_FAILED:
            return False

        print("[ArcFace] Initializing model...")
        try:
            _ARCFACE_MODEL = _load_model_once()
            _ARCFACE_INITIALIZED = True
            print("[ArcFace] [OK] Ready")
            return True
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"[ArcFace] CRITICAL: Model initialization failed")
            print(f"  Error: {e}")
            print(f"  The system will run with Facenet512 only.")
            print(f"  To fix: ensure arcface_weights.h5 (~130 MB) is at:")
            print(f"  {ARCFACE_WEIGHT_PATH}")
            print(f"  Then run: python upload_arcface_weights.py")
            print(f"{'='*60}\n")
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
    if not is_arcface_initialized():
        raise RuntimeError("ArcFace model not initialized.")

    result = DeepFace.represent(
        img_path=image_path,
        model_name="ArcFace",
        enforce_detection=enforce_detection,
        align=align,
        detector_backend=detector_backend,
    )

    if not result or "embedding" not in result[0]:
        raise ValueError("ArcFace: empty/malformed result from DeepFace.represent()")

    embedding = np.array(result[0]["embedding"])
    if embedding.shape[0] != 512:
        raise ValueError(f"ArcFace: unexpected dim {embedding.shape[0]}, expected 512")

    return embedding


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm > 0 else embedding
