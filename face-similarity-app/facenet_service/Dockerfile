FROM python:3.11-slim

# ── Python runtime ────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── TensorFlow CPU-only tuning ────────────────────────────────────────────────
# TF_CPP_MIN_LOG_LEVEL=3   : suppress all TF C++ logs (errors only)
# OMP_NUM_THREADS=1        : prevent OpenMP from spawning excess threads
# TF_NUM_INTRAOP_THREADS=1 : single-threaded op execution (stable in containers)
# TF_NUM_INTEROP_THREADS=1 : single-threaded inter-op parallelism
# CUDA_VISIBLE_DEVICES=""  : explicitly disable GPU (CPU-only)
ENV TF_CPP_MIN_LOG_LEVEL=3
ENV OMP_NUM_THREADS=1
ENV TF_NUM_INTRAOP_THREADS=1
ENV TF_NUM_INTEROP_THREADS=1
ENV CUDA_VISIBLE_DEVICES=""

# ── System dependencies ───────────────────────────────────────────────────────
# libglib2.0-0 required by opencv-python-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY main.py .

# ── Model preload at build time ───────────────────────────────────────────────
# Downloads Facenet512 weights and compiles the TF graph during docker build.
# This ensures zero model download or TF initialization delay at runtime.
RUN python - <<'EOF'
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np
from deepface import DeepFace

print("Loading Facenet model...")
DeepFace.build_model("Facenet512")

print("Warming up Facenet...")
dummy = np.zeros((160, 160, 3), dtype=np.uint8)
try:
    DeepFace.represent(
        img_path=dummy,
        model_name="Facenet512",
        enforce_detection=False,
        align=False,
        detector_backend="skip",
    )
    print("Facenet ready")
except Exception as e:
    print(f"Warmup failed (non-fatal): {e}")
    print("Facenet ready")
EOF

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
