"""
InsightFace model wrapper — uses ONNX Runtime directly.

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

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# InsightFace buffalo_l recognition model (ArcFace R50, 512-D)
MODEL_URL = (
    "https://github.com/deepinsight/insightface/releases/download/v0.7/"
    "buffalo_l.zip"
)
# Direct ONNX file URL (smaller download — recognition model only)
RECOG_ONNX_URL = (
    "https://huggingface.co/deepinsight/insightface/resolve/main/"
    "models/buffalo_l/w600k_r50.onnx"
)

MODEL_DIR  = os.path.join(os.path.expanduser("~"), ".insightface", "models", "buffalo_l")
ONNX_PATH  = os.path.join(MODEL_DIR, "w600k_r50.onnx")
ONNX_MIN_SIZE = 160 * 1024 * 1024   # ~166 MB complete file

EMBEDDING_DIM = 512
INPUT_SIZE    = 112   # ArcFace R50 expects 112x112

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------

_SESSION = None                      # onnxruntime.InferenceSession
_INPUT_NAME  = None
_OUTPUT_NAME = None
_INSIGHTFACE_INITIALIZED  = False
_INSIGHTFACE_LOAD_FAILED  = False
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Weight download
# ---------------------------------------------------------------------------

def _ensure_model() -> bool:
    """Download w600k_r50.onnx if not present or too small."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    if os.path.exists(ONNX_PATH):
        size = os.path.getsize(ONNX_PATH)
        if size >= ONNX_MIN_SIZE:
            print(f"[InsightFace] ONNX model found: {ONNX_PATH} ({size//(1024*1024)} MB)")
            return True
        print(f"[InsightFace] ONNX model too small ({size} bytes), re-downloading...")
        os.remove(ONNX_PATH)

    print(f"[InsightFace] Downloading w600k_r50.onnx from HuggingFace...")
    print(f"  URL: {RECOG_ONNX_URL}")
    try:
        urllib.request.urlretrieve(RECOG_ONNX_URL, ONNX_PATH)
        size = os.path.getsize(ONNX_PATH)
        print(f"[InsightFace] Downloaded: {size//(1024*1024)} MB")
        return size >= ONNX_MIN_SIZE
    except Exception as e:
        print(f"[InsightFace] Download failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initialize_insightface_model() -> bool:
    """
    Load InsightFace ArcFace R50 ONNX model.
    Thread-safe, idempotent.
    Returns True if model loaded successfully.
    """
    global _SESSION, _INPUT_NAME, _OUTPUT_NAME
    global _INSIGHTFACE_INITIALIZED, _INSIGHTFACE_LOAD_FAILED

    if _INSIGHTFACE_INITIALIZED:
        return True
    if _INSIGHTFACE_LOAD_FAILED:
        return False

    with _LOCK:
        if _INSIGHTFACE_INITIALIZED:
            return True

        try:
            import onnxruntime as ort

            if not _ensure_model():
                raise RuntimeError("Could not obtain w600k_r50.onnx")

            print(f"[InsightFace] Loading ONNX session from {ONNX_PATH} ...")
            sess_opts = ort.SessionOptions()
            sess_opts.inter_op_num_threads = 2
            sess_opts.intra_op_num_threads = 4

            _SESSION     = ort.InferenceSession(
                ONNX_PATH,
                sess_options=sess_opts,
                providers=["CPUExecutionProvider"],
            )
            _INPUT_NAME  = _SESSION.get_inputs()[0].name
            _OUTPUT_NAME = _SESSION.get_outputs()[0].name

            _INSIGHTFACE_INITIALIZED = True
            print(f"[InsightFace] [OK] Model loaded — input={_INPUT_NAME}, output={_OUTPUT_NAME}")
            return True

        except Exception as e:
            _INSIGHTFACE_LOAD_FAILED = True
            print(f"[InsightFace] [CRITICAL] Failed to load model: {e}")
            traceback.print_exc()
            return False


def is_insightface_initialized() -> bool:
    return _INSIGHTFACE_INITIALIZED


def _preprocess_for_arcface(face_bgr: np.ndarray) -> np.ndarray:
    """
    Resize to 112x112, normalize to [-1, 1], convert to NCHW float32.
    This matches the preprocessing expected by w600k_r50.onnx.
    """
    img = face_bgr
    if img.dtype != np.uint8:
        img = (img * 255).clip(0, 255).astype(np.uint8)

    # Resize to 112x112
    img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LANCZOS4)

    # BGR → RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Normalize to [-1, 1]
    img = img.astype(np.float32)
    img = (img - 127.5) / 128.0

    # HWC → NCHW
    img = img.transpose(2, 0, 1)[np.newaxis, ...]   # (1, 3, 112, 112)
    return img


def extract_insightface_embedding(face_bgr: np.ndarray) -> np.ndarray:
    """
    Extract a 512-D L2-normalized embedding from a BGR face crop.

    Args:
        face_bgr: uint8 BGR numpy array (any size — resized internally to 112x112).

    Returns:
        np.ndarray: 512-D float32 L2-normalized embedding.

    Raises:
        RuntimeError: If model not initialized.
    """
    if not _INSIGHTFACE_INITIALIZED or _SESSION is None:
        raise RuntimeError("InsightFace model not initialized")

    inp = _preprocess_for_arcface(face_bgr)
    outputs = _SESSION.run([_OUTPUT_NAME], {_INPUT_NAME: inp})
    emb = outputs[0][0]   # shape (512,)

    # L2 normalize
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm

    return emb.astype(np.float32)


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """L2-normalize an embedding vector (no-op if already normalized)."""
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm > 0 else embedding
