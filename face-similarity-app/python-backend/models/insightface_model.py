"""
InsightFace model wrapper - uses ONNX Runtime directly.

Avoids the Cython build requirement of the insightface package on Windows.
Downloads the buffalo_l recognition model (w600k_r50.onnx) on first use.

Model: ArcFace R50 from InsightFace buffalo_l pack
  - Input:  112x112 BGR image, normalized to [-1, 1]
  - Output: 512-D L2-normalized embedding
  - Source: https://github.com/deepinsight/insightface (buffalo_l pack)

Detection: Uses DeepFace opencv detector (already installed) for face alignment,
           then feeds the aligned crop directly to the ONNX recognition model.
"""

import os
import threading
import traceback
import urllib.request
import zipfile
import shutil

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_DIR  = os.path.join(os.path.expanduser("~"), ".insightface", "models", "buffalo_l")
ONNX_PATH  = os.path.join(MODEL_DIR, "w600k_r50.onnx")
ONNX_MIN_SIZE = 160 * 1024 * 1024   # ~166 MB complete file

EMBEDDING_DIM = 512
INPUT_SIZE    = 112   # ArcFace R50 expects 112x112

# Download sources tried in order (most reliable first)
_DOWNLOAD_SOURCES = [
    # 1. GitHub release zip (buffalo_l pack - most reliable, no auth required)
    {
        "label": "GitHub buffalo_l.zip",
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
        "type": "zip",
    },
    # 2. HuggingFace direct ONNX (may require auth - kept as fallback)
    {
        "label": "HuggingFace direct ONNX",
        "url": "https://huggingface.co/deepinsight/insightface/resolve/main/models/buffalo_l/w600k_r50.onnx",
        "type": "onnx",
    },
    # 3. Alternative HuggingFace mirror
    {
        "label": "HuggingFace mirror (no redirect)",
        "url": "https://huggingface.co/deepinsight/insightface/resolve/main/models/buffalo_l/w600k_r50.onnx?download=true",
        "type": "onnx",
    },
]

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------

_SESSION     = None
_INPUT_NAME  = None
_OUTPUT_NAME = None
_INSIGHTFACE_INITIALIZED = False
_INSIGHTFACE_LOAD_FAILED = False
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Weight download
# ---------------------------------------------------------------------------

def _download_with_progress(url: str, dest: str, label: str) -> bool:
    """Download a file with progress logging. Returns True on success."""
    tmp = dest + ".tmp"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/octet-stream, */*",
        })
        print(f"  [InsightFace] Connecting to {label}...")
        with urllib.request.urlopen(req, timeout=300) as resp:
            total_reported = int(resp.headers.get("Content-Length", 0))
            if total_reported:
                print(f"  [InsightFace] Expected size: {total_reported // (1024*1024)} MB")
            downloaded = 0
            with open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1024 * 1024)  # 1 MB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (20 * 1024 * 1024) == 0:
                        print(f"  [InsightFace] Downloaded: {downloaded // (1024*1024)} MB...")
        size = os.path.getsize(tmp)
        print(f"  [InsightFace] Download complete: {size // (1024*1024)} MB")
        shutil.move(tmp, dest)
        return True
    except Exception as e:
        print(f"  [InsightFace] Download failed ({label}): {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        return False


def _extract_onnx_from_zip(zip_path: str) -> bool:
    """Extract w600k_r50.onnx from buffalo_l.zip into MODEL_DIR."""
    print(f"  [InsightFace] Extracting ONNX from zip: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            print(f"  [InsightFace] Zip contents: {names}")
            target = next((n for n in names if n.endswith("w600k_r50.onnx")), None)
            if not target:
                print(f"  [InsightFace] ERROR: w600k_r50.onnx not found in zip. Contents: {names}")
                return False
            print(f"  [InsightFace] Extracting: {target}")
            with zf.open(target) as src, open(ONNX_PATH, "wb") as dst:
                shutil.copyfileobj(src, dst)
        size = os.path.getsize(ONNX_PATH)
        print(f"  [InsightFace] Extracted: {size // (1024*1024)} MB -> {ONNX_PATH}")
        return size >= ONNX_MIN_SIZE
    except Exception as e:
        print(f"  [InsightFace] Zip extraction failed: {e}")
        traceback.print_exc()
        return False


def _ensure_model() -> bool:
    """
    Ensure w600k_r50.onnx is present and valid.
    Tries multiple download sources in order.
    Returns True if model is ready.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Check existing file
    if os.path.exists(ONNX_PATH):
        size = os.path.getsize(ONNX_PATH)
        if size >= ONNX_MIN_SIZE:
            print(f"[InsightFace] Model already present: {ONNX_PATH} ({size // (1024*1024)} MB) [OK]")
            return True
        print(f"[InsightFace] Existing file too small ({size // (1024*1024)} MB < {ONNX_MIN_SIZE // (1024*1024)} MB) - removing and re-downloading")
        os.remove(ONNX_PATH)

    print(f"[InsightFace] Model not found at: {ONNX_PATH}")
    print(f"[InsightFace] Will try {len(_DOWNLOAD_SOURCES)} download source(s)...")

    for i, source in enumerate(_DOWNLOAD_SOURCES, 1):
        print(f"\n[InsightFace] --- Download attempt {i}/{len(_DOWNLOAD_SOURCES)}: {source['label']} ---")

        if source["type"] == "zip":
            zip_path = ONNX_PATH + ".buffalo_l.zip"
            ok = _download_with_progress(source["url"], zip_path, source["label"])
            if ok:
                extracted = _extract_onnx_from_zip(zip_path)
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
                if extracted:
                    size = os.path.getsize(ONNX_PATH)
                    print(f"[InsightFace] [OK] Model ready: {ONNX_PATH} ({size // (1024*1024)} MB)")
                    return True
                print(f"[InsightFace] Extraction failed for source {i}, trying next...")
            else:
                print(f"[InsightFace] Download failed for source {i}, trying next...")

        elif source["type"] == "onnx":
            ok = _download_with_progress(source["url"], ONNX_PATH, source["label"])
            if ok:
                size = os.path.getsize(ONNX_PATH)
                if size >= ONNX_MIN_SIZE:
                    print(f"[InsightFace] [OK] Model ready: {ONNX_PATH} ({size // (1024*1024)} MB)")
                    return True
                print(f"[InsightFace] Downloaded file too small ({size // (1024*1024)} MB), trying next source...")
                os.remove(ONNX_PATH)
            else:
                print(f"[InsightFace] Download failed for source {i}, trying next...")

    print(f"\n[InsightFace] [FAIL] ALL {len(_DOWNLOAD_SOURCES)} download sources failed.")
    print(f"[InsightFace] Manual fix: download w600k_r50.onnx (~166 MB) and place it at:")
    print(f"[InsightFace]   {ONNX_PATH}")
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_insightface_model() -> bool:
    """
    Load InsightFace ArcFace R50 ONNX model.
    Thread-safe, idempotent.
    Returns True if model loaded successfully.
    Raises RuntimeError on failure (fail loudly).
    """
    global _SESSION, _INPUT_NAME, _OUTPUT_NAME
    global _INSIGHTFACE_INITIALIZED, _INSIGHTFACE_LOAD_FAILED

    if _INSIGHTFACE_INITIALIZED:
        print("[InsightFace] Already initialized [OK]")
        return True
    if _INSIGHTFACE_LOAD_FAILED:
        print("[InsightFace] Previously failed - skipping retry")
        return False

    with _LOCK:
        if _INSIGHTFACE_INITIALIZED:
            return True

        print("[InsightFace] ============================================================")
        print("[InsightFace] Starting InsightFace ArcFace R50 initialization")
        print(f"[InsightFace] Target model path: {ONNX_PATH}")
        print(f"[InsightFace] Model directory:   {MODEL_DIR}")
        print("[InsightFace] ============================================================")

        try:
            import onnxruntime as ort
            print(f"[InsightFace] onnxruntime version: {ort.__version__}")
            print(f"[InsightFace] Available providers: {ort.get_available_providers()}")
        except ImportError as e:
            _INSIGHTFACE_LOAD_FAILED = True
            msg = f"onnxruntime not installed: {e}"
            print(f"[InsightFace] [ERROR] {msg}")
            raise RuntimeError(f"InsightFace init failed: {msg}")

        try:
            # Step 1: Ensure model file is present
            print("[InsightFace] Step 1: Checking/downloading model weights...")
            model_ready = _ensure_model()
            if not model_ready:
                _INSIGHTFACE_LOAD_FAILED = True
                msg = f"Could not obtain w600k_r50.onnx - all download sources failed. Place the file manually at: {ONNX_PATH}"
                print(f"[InsightFace] [ERROR] {msg}")
                raise RuntimeError(f"InsightFace init failed: {msg}")

            # Step 2: Verify file integrity
            print("[InsightFace] Step 2: Verifying model file...")
            actual_size = os.path.getsize(ONNX_PATH)
            print(f"[InsightFace]   File: {ONNX_PATH}")
            print(f"[InsightFace]   Size: {actual_size // (1024*1024)} MB ({actual_size:,} bytes)")
            if actual_size < ONNX_MIN_SIZE:
                _INSIGHTFACE_LOAD_FAILED = True
                msg = f"Model file too small: {actual_size // (1024*1024)} MB (expected >= {ONNX_MIN_SIZE // (1024*1024)} MB)"
                print(f"[InsightFace] [ERROR] {msg}")
                raise RuntimeError(f"InsightFace init failed: {msg}")
            print(f"[InsightFace]   Size check: PASSED [OK]")

            # Step 3: Create ONNX session
            print("[InsightFace] Step 3: Creating ONNX inference session...")
            sess_opts = ort.SessionOptions()
            sess_opts.inter_op_num_threads = 2
            sess_opts.intra_op_num_threads = 4
            sess_opts.log_severity_level = 2  # suppress verbose ONNX logs

            _SESSION = ort.InferenceSession(
                ONNX_PATH,
                sess_options=sess_opts,
                providers=["CPUExecutionProvider"],
            )

            # Step 4: Inspect session I/O
            _INPUT_NAME  = _SESSION.get_inputs()[0].name
            _OUTPUT_NAME = _SESSION.get_outputs()[0].name
            input_shape  = _SESSION.get_inputs()[0].shape
            output_shape = _SESSION.get_outputs()[0].shape

            print(f"[InsightFace]   Session created [OK]")
            print(f"[InsightFace]   Input  name:  {_INPUT_NAME}")
            print(f"[InsightFace]   Input  shape: {input_shape}")
            print(f"[InsightFace]   Output name:  {_OUTPUT_NAME}")
            print(f"[InsightFace]   Output shape: {output_shape}")

            # Step 5: Smoke test with a dummy input
            print("[InsightFace] Step 4: Running smoke test (dummy inference)...")
            dummy = np.zeros((1, 3, INPUT_SIZE, INPUT_SIZE), dtype=np.float32)
            out = _SESSION.run([_OUTPUT_NAME], {_INPUT_NAME: dummy})
            emb_shape = out[0].shape
            print(f"[InsightFace]   Smoke test output shape: {emb_shape}")
            if emb_shape[-1] != EMBEDDING_DIM:
                _INSIGHTFACE_LOAD_FAILED = True
                msg = f"Unexpected embedding dim: {emb_shape[-1]} (expected {EMBEDDING_DIM})"
                print(f"[InsightFace] [ERROR] {msg}")
                raise RuntimeError(f"InsightFace init failed: {msg}")
            print(f"[InsightFace]   Smoke test: PASSED [OK] (output dim={emb_shape[-1]})")

            _INSIGHTFACE_INITIALIZED = True
            print("[InsightFace] ============================================================")
            print("[InsightFace] [OK] InsightFace ArcFace R50 FULLY INITIALIZED AND READY")
            print("[InsightFace] ============================================================")
            return True

        except RuntimeError:
            raise  # already set _INSIGHTFACE_LOAD_FAILED and printed
        except Exception as e:
            _INSIGHTFACE_LOAD_FAILED = True
            print(f"[InsightFace] [ERROR] Unexpected failure during initialization:")
            traceback.print_exc()
            raise RuntimeError(f"InsightFace init failed: {e}") from e


def is_insightface_initialized() -> bool:
    return _INSIGHTFACE_INITIALIZED


def get_insightface_status() -> dict:
    """Return a status dict for diagnostics."""
    return {
        "initialized": _INSIGHTFACE_INITIALIZED,
        "load_failed": _INSIGHTFACE_LOAD_FAILED,
        "model_path": ONNX_PATH,
        "model_exists": os.path.exists(ONNX_PATH),
        "model_size_mb": os.path.getsize(ONNX_PATH) // (1024 * 1024) if os.path.exists(ONNX_PATH) else 0,
        "session_active": _SESSION is not None,
        "input_name": _INPUT_NAME,
        "output_name": _OUTPUT_NAME,
    }


# ---------------------------------------------------------------------------
# Preprocessing + inference
# ---------------------------------------------------------------------------

def _preprocess_for_arcface(face_bgr: np.ndarray) -> np.ndarray:
    """
    Resize to 112x112, normalize to [-1, 1], convert to NCHW float32.
    Matches the preprocessing expected by w600k_r50.onnx.
    """
    img = face_bgr
    if img.dtype != np.uint8:
        img = (img * 255).clip(0, 255).astype(np.uint8)

    img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LANCZOS4)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32)
    img = (img - 127.5) / 128.0
    img = img.transpose(2, 0, 1)[np.newaxis, ...]  # (1, 3, 112, 112)
    return img


def extract_insightface_embedding(face_bgr: np.ndarray) -> np.ndarray:
    """
    Extract a 512-D L2-normalized embedding from a BGR face crop.

    Args:
        face_bgr: uint8 BGR numpy array (any size - resized internally to 112x112).

    Returns:
        np.ndarray: 512-D float32 L2-normalized embedding.

    Raises:
        RuntimeError: If model not initialized.
    """
    if not _INSIGHTFACE_INITIALIZED or _SESSION is None:
        status = get_insightface_status()
        raise RuntimeError(
            f"InsightFace model not initialized. "
            f"Status: initialized={status['initialized']}, "
            f"load_failed={status['load_failed']}, "
            f"model_exists={status['model_exists']} ({status['model_size_mb']} MB), "
            f"session_active={status['session_active']}"
        )

    inp = _preprocess_for_arcface(face_bgr)
    outputs = _SESSION.run([_OUTPUT_NAME], {_INPUT_NAME: inp})
    emb = outputs[0][0]  # shape (512,)

    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm

    return emb.astype(np.float32)


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2-normalize an embedding vector (no-op if already normalized)."""
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm > 0 else embedding
