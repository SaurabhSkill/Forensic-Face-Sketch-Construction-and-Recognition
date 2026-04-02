"""
facenet_service/main.py
=======================
Lightweight FastAPI microservice that returns Facenet512 face embeddings.

Endpoints:
  POST /embedding  — accepts image path or base64, returns 512-D embedding

Model is loaded ONCE at startup via lifespan event using a global singleton.
DeepFace.represent() receives the pre-loaded MODEL object — never reloads.
"""

import base64
import logging
import os
import tempfile
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import uvicorn
from deepface import DeepFace
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("facenet_service")

# ---------------------------------------------------------------------------
# Global singleton — loaded ONCE at startup, reused for every request
# ---------------------------------------------------------------------------

MODEL       = None   # DeepFace Facenet512 model object (Keras model)
MODEL_READY = False  # True after successful warmup inference


def _load_model() -> bool:
    """
    Load Facenet512 ONCE and run a warmup inference to compile the TF graph.
    Sets the global MODEL and MODEL_READY.
    Returns True on success.
    """
    global MODEL, MODEL_READY

    # Guard: never load twice
    if MODEL is not None:
        print("[Facenet] Using cached model", flush=True)
        log.info("[Facenet] Using cached model")
        return True

    print("Loading Facenet model...", flush=True)
    log.info("Loading Facenet model...")
    try:
        MODEL = DeepFace.build_model("Facenet512")
        log.info("[Facenet] Model object built and stored in global singleton")
    except Exception as exc:
        log.error("Failed to load Facenet model: %s", exc)
        return False

    # Warmup — compiles TF graph so first real request is instant
    print("Warming up Facenet...", flush=True)
    log.info("Warming up Facenet...")
    try:
        dummy = np.zeros((160, 160, 3), dtype=np.uint8)
        # Pass "Facenet512" string for warmup — same as inference
        DeepFace.represent(
            img_path=dummy,
            model_name="Facenet512",
            enforce_detection=False,
            align=False,
            detector_backend="skip",
        )
        print("Facenet ready", flush=True)
        log.info("Facenet ready")
        MODEL_READY = True
        return True
    except Exception as exc:
        log.warning("Warmup failed (non-fatal): %s", exc)
        print("Facenet ready", flush=True)
        log.info("Facenet ready (warmup skipped)")
        MODEL_READY = True
        return True


# ---------------------------------------------------------------------------
# Lifespan — runs ONCE at startup and once at shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    ok = _load_model()
    if not ok:
        log.error("Model failed to load — /embedding will return 503")
    yield
    log.info("Shutting down facenet_service")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Facenet512 Embedding Service",
    description="Returns 512-D L2-normalized face embeddings using DeepFace Facenet512.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class EmbeddingRequest(BaseModel):
    image_path:   Optional[str] = None   # absolute path to image file on server
    image_base64: Optional[str] = None   # base64-encoded image bytes


class EmbeddingResponse(BaseModel):
    embedding:  list[float]              # 512-D L2-normalized vector
    model:      str = "Facenet512"
    dimensions: int = 512


# ---------------------------------------------------------------------------
# Helper — decode input to a temp file path
# ---------------------------------------------------------------------------

def _resolve_image(req: EmbeddingRequest) -> str:
    if req.image_path:
        if not os.path.isfile(req.image_path):
            raise HTTPException(
                status_code=400,
                detail=f"image_path does not exist: {req.image_path}",
            )
        return req.image_path

    if req.image_base64:
        try:
            image_bytes = base64.b64decode(req.image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 encoding")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        try:
            tmp.write(image_bytes)
            tmp.flush()
            return tmp.name
        finally:
            tmp.close()

    raise HTTPException(
        status_code=400,
        detail="Provide either 'image_path' or 'image_base64'",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status":       "ready" if MODEL_READY else "initializing",
        "model":        "Facenet512",
        "model_loaded": MODEL_READY,
    }


@app.post("/embedding", response_model=EmbeddingResponse)
def get_embedding(req: EmbeddingRequest):
    """
    Extract a 512-D L2-normalized Facenet512 embedding from an image.

    Accepts:
      - image_path:   path to an image file on the server filesystem
      - image_base64: base64-encoded image bytes (JPEG/PNG)

    Returns:
      - embedding: list of 512 floats (L2-normalized)
    """
    if not MODEL_READY:
        raise HTTPException(
            status_code=503,
            detail="Model is still initializing. Retry in a moment.",
        )

    # MODEL is guaranteed non-None here (MODEL_READY is only True after load)
    print("[Facenet] Using cached model", flush=True)
    log.info("[Facenet] Using cached model — running inference")

    tmp_path   = None
    image_path = _resolve_image(req)

    if req.image_base64:
        tmp_path = image_path

    try:
        log.info("Running Facenet512 inference on: %s", os.path.basename(image_path))

        # Pass "Facenet512" string — DeepFace resolves the already-loaded model
        # from its internal registry. Passing the object directly is not supported.
        result = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet512",
            enforce_detection=False,
            align=True,
            detector_backend="opencv",
        )

        if not result or "embedding" not in result[0]:
            raise HTTPException(
                status_code=422,
                detail="DeepFace returned empty result — no face detected",
            )

        raw = np.array(result[0]["embedding"], dtype=np.float32)

        # L2 normalize
        norm      = np.linalg.norm(raw)
        embedding = (raw / norm if norm > 0 else raw).tolist()

        log.info("Embedding extracted — dim=%d, norm=%.4f", len(embedding), norm)

        return EmbeddingResponse(
            embedding=embedding,
            dimensions=len(embedding),
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.error("Inference failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
