"""
ArcFace model wrapper — strict validation, S3-first download, hard-fail.

Weight file requirements:
  - Size  : >= 120 MB  (complete file is ~130 MB)
  - Format: valid HDF5 (magic bytes + h5py open succeeds)

Download priority:
  1. Already on disk and valid
  2. S3 self-hosted  (s3://<bucket>/models/arcface_weights.h5)
  3. Google Drive    (gdown, ID: 1LVB3CdVejpmGHM28BpqqkbZP5hDEcdZY)
  4. GitHub releases (may be 404)

Hard-fail policy:
  If the model cannot be loaded, initialize_arcface_model() returns False
  and logs a CRITICAL message with exact fix instructions.
  The server continues with Facenet-only but logs a prominent warning on
  every request that uses embeddings.
"""

import os
import shutil
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

ARCFACE_MIN_SIZE_BYTES = 120 * 1024 * 1024   # 120 MB — complete file is ~130 MB
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
MAX_LOAD_RETRIES = 2

ARCFACE_GDRIVE_ID = "1LVB3CdVejpmGHM28BpqqkbZP5hDEcdZY"
ARCFACE_GITHUB_URL = (
    "https://github.com/serengil/deepface_models/releases/download/v1.0/arcface_weights.h5"
)
ARCFACE_S3_KEY = "models/arcface_weights.h5"

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------

_ARCFACE_MODEL = None
_ARCFACE_INITIALIZED = False
_ARCFACE_LOAD_FAILED = False
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Strict weight file validation
# ---------------------------------------------------------------------------

def _ensure_weights_dir() -> None:
    os.makedirs(WEIGHTS_DIR, mode=0o755, exist_ok=True)


def get_weight_info() -> dict:
    """Return size/existence info for the weight file."""
    if not os.path.exists(ARCFACE_WEIGHT_PATH):
        return {"exists": False, "size_bytes": 0, "size_mb": 0.0, "path": ARCFACE_WEIGHT_PATH}
    size = os.path.getsize(ARCFACE_WEIGHT_PATH)
    return {
        "exists": True,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 2),
        "path": ARCFACE_WEIGHT_PATH,
    }


def validate_weight_file(path: str = None) -> tuple:
    """
    Strict validation: existence + size >= 120 MB + valid HDF5 (h5py open).
    Returns (is_valid: bool, reason: str).
    """
    p = path or ARCFACE_WEIGHT_PATH

    if not os.path.exists(p):
        return False, "file does not exist"

    size = os.path.getsize(p)
    size_mb = size / (1024 * 1024)

    if size < ARCFACE_MIN_SIZE_BYTES:
        return False, (
            f"file too small: {size_mb:.1f} MB "
            f"(minimum {ARCFACE_MIN_SIZE_BYTES//(1024*1024)} MB, complete file is ~130 MB)"
        )

    # Magic bytes check
    try:
        with open(p, "rb") as f:
            header = f.read(8)
        if header != HDF5_MAGIC:
            return False, f"invalid HDF5 magic bytes: {header.hex()}"
    except OSError as e:
        return False, f"cannot read file: {e}"

    # Full h5py open — catches truncated files that pass magic check
    try:
        import h5py
        with h5py.File(p, "r") as f:
            keys = list(f.keys())[:2]
        return True, f"valid HDF5, {size_mb:.1f} MB, keys={keys}"
    except Exception as e:
        return False, f"HDF5 open failed (truncated?): {str(e)[:100]}"


def _delete_weight_file(path: str = None) -> None:
    p = path or ARCFACE_WEIGHT_PATH
    try:
        if os.path.exists(p):
            os.remove(p)
            print(f"[ArcFace] Deleted: {p}")
    except OSError as e:
        print(f"[ArcFace] WARNING: Could not delete {p}: {e}")


# ---------------------------------------------------------------------------
# Download strategies
# ---------------------------------------------------------------------------

def _install_file(tmp_path: str) -> bool:
    """Validate tmp file and move to final location."""
    ok, reason = validate_weight_file(tmp_path)
    if not ok:
        print(f"[ArcFace] Downloaded file invalid: {reason}")
        _delete_weight_file(tmp_path)
        return False
    _ensure_weights_dir()
    _delete_weight_file()
    shutil.move(tmp_path, ARCFACE_WEIGHT_PATH)
    ok2, reason2 = validate_weight_file()
    print(f"[ArcFace] Installed: {reason2}")
    return ok2


def _download_from_s3() -> bool:
    """Download from project S3 bucket — primary source after local disk."""
    try:
        import boto3
        from dotenv import load_dotenv
        load_dotenv()

        bucket = os.environ.get("AWS_S3_BUCKET_NAME")
        region = os.environ.get("AWS_REGION", "us-east-1")
        key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")

        if not all([bucket, key_id, secret]):
            print("[ArcFace] S3 credentials not set, skipping S3 download")
            return False

        s3 = boto3.client("s3", region_name=region,
                          aws_access_key_id=key_id,
                          aws_secret_access_key=secret)

        # Verify S3 object exists and is large enough before downloading
        try:
            obj = s3.head_object(Bucket=bucket, Key=ARCFACE_S3_KEY)
            s3_size = obj["ContentLength"]
            s3_size_mb = s3_size / (1024 * 1024)
            if s3_size < ARCFACE_MIN_SIZE_BYTES:
                print(f"[ArcFace] S3 file too small ({s3_size_mb:.1f} MB) — skipping")
                return False
            print(f"[ArcFace] S3 object: {ARCFACE_S3_KEY} ({s3_size_mb:.1f} MB)")
        except Exception as e:
            print(f"[ArcFace] S3 object not found: {e}")
            return False

        _ensure_weights_dir()
        tmp = ARCFACE_WEIGHT_PATH + ".s3dl"
        print(f"[ArcFace] Downloading from S3...")
        s3.download_file(bucket, ARCFACE_S3_KEY, tmp)
        return _install_file(tmp)

    except Exception as e:
        print(f"[ArcFace] S3 download error: {e}")
        return False


def _download_from_gdrive() -> bool:
    """Download from Google Drive via gdown."""
    try:
        import gdown
        _ensure_weights_dir()
        tmp = ARCFACE_WEIGHT_PATH + ".gdl"
        url = f"https://drive.google.com/uc?id={ARCFACE_GDRIVE_ID}"
        print(f"[ArcFace] Trying Google Drive (ID: {ARCFACE_GDRIVE_ID})...")
        gdown.download(url, tmp, quiet=False, fuzzy=True)
        if os.path.exists(tmp):
            return _install_file(tmp)
    except Exception as e:
        print(f"[ArcFace] GDrive download error: {e}")
    return False


def _download_from_github() -> bool:
    """Download from GitHub releases (may be 404)."""
    try:
        import urllib.request
        _ensure_weights_dir()
        tmp = ARCFACE_WEIGHT_PATH + ".ghdl"
        print(f"[ArcFace] Trying GitHub: {ARCFACE_GITHUB_URL}")
        req = urllib.request.Request(ARCFACE_GITHUB_URL, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/octet-stream",
        })
        with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as f:
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
        if os.path.exists(tmp):
            return _install_file(tmp)
    except Exception as e:
        print(f"[ArcFace] GitHub download error: {e}")
    return False


def ensure_arcface_weights() -> bool:
    """
    Ensure arcface_weights.h5 is present, valid, and complete.
    Tries: disk → S3 → GDrive → GitHub.
    Returns True if weights are ready.
    """
    ok, reason = validate_weight_file()
    if ok:
        print(f"[ArcFace] Weights valid on disk: {reason}")
        return True

    print(f"[ArcFace] Weights not ready: {reason}")
    _delete_weight_file()  # Remove any corrupt/partial file

    for name, fn in [
        ("S3 (self-hosted)", _download_from_s3),
        ("Google Drive", _download_from_gdrive),
        ("GitHub releases", _download_from_github),
    ]:
        print(f"[ArcFace] Trying: {name}")
        try:
            if fn():
                ok2, reason2 = validate_weight_file()
                if ok2:
                    print(f"[ArcFace] [OK] Weights ready from {name}: {reason2}")
                    return True
                print(f"[ArcFace] Post-download validation failed: {reason2}")
                _delete_weight_file()
        except Exception as e:
            print(f"[ArcFace] {name} error: {e}")

    return False


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _load_model_once() -> object:
    """
    Ensure weights are valid, then load via DeepFace.build_model().
    Raises RuntimeError if weights cannot be obtained or model fails to load.
    """
    _ensure_weights_dir()

    if not ensure_arcface_weights():
        raise RuntimeError(
            "Cannot obtain valid arcface_weights.h5 from any source.\n"
            f"  Required: >= {ARCFACE_MIN_SIZE_BYTES//(1024*1024)} MB, valid HDF5\n"
            f"  Target path: {ARCFACE_WEIGHT_PATH}\n"
            "  Fix: run  python get_arcface_weights.py --file /path/to/arcface_weights.h5\n"
            "  Then: python get_arcface_weights.py  (to upload to S3)"
        )

    for attempt in range(1, MAX_LOAD_RETRIES + 1):
        print(f"[ArcFace] Load attempt {attempt}/{MAX_LOAD_RETRIES}...")
        try:
            model = DeepFace.build_model("ArcFace")
            info = get_weight_info()
            print(f"[ArcFace] [OK] Model loaded ({info['size_mb']} MB)")
            return model

        except OSError as e:
            # File became corrupt between validation and load
            print(f"[ArcFace] OSError on attempt {attempt}: {e}")
            _delete_weight_file()
            if attempt < MAX_LOAD_RETRIES and not ensure_arcface_weights():
                break

        except Exception as e:
            print(f"[ArcFace] Load error on attempt {attempt}: {e}")
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
    Thread-safe singleton initializer.
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

        print("[ArcFace] Initializing...")
        try:
            _ARCFACE_MODEL = _load_model_once()
            _ARCFACE_INITIALIZED = True
            print("[ArcFace] [OK] Ready")
            return True

        except Exception as e:
            _ARCFACE_LOAD_FAILED = True
            _ARCFACE_MODEL = None
            _ARCFACE_INITIALIZED = False

            border = "=" * 60
            print(f"\n{border}")
            print("  ARCFACE MODEL FAILED TO LOAD")
            print(border)
            print(f"  Error   : {e}")
            print(f"  Impact  : System running with Facenet512 ONLY")
            print(f"            Dual-model accuracy is DEGRADED")
            print(f"  Fix     : python get_arcface_weights.py")
            print(f"            (or provide the file manually)")
            print(f"  File    : {ARCFACE_WEIGHT_PATH}")
            print(f"  Required: >= {ARCFACE_MIN_SIZE_BYTES//(1024*1024)} MB, valid HDF5")
            print(f"{border}\n")
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
