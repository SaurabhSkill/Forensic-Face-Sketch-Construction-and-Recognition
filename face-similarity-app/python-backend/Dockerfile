FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Suppress TensorFlow verbose logs and disable oneDNN (prevents extra graph recompilation)
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV TF_ENABLE_ONEDNN_OPTS=0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp_uploads directory
RUN mkdir -p temp_uploads

# ============================================================================
# MODEL PRELOADING (build-time)
# ============================================================================
# Runs preload_models.py which:
#   1. Downloads Facenet512 weights from S3 (or DeepFace CDN fallback)
#   2. Downloads InsightFace w600k_r50.onnx from S3 (or GitHub fallback)
#   3. Runs warmup inference on both models to compile TF/ONNX graphs
#
# AWS credentials are passed as build args so they are NOT baked into the
# image layer (they are only available during this RUN step).
#
# If S3 credentials are not provided, models download from public CDNs.
# ============================================================================

ARG AWS_ACCESS_KEY_ID=""
ARG AWS_SECRET_ACCESS_KEY=""
ARG AWS_REGION="us-east-1"
ARG MODEL_S3_BUCKET=""
ARG FACENET_S3_KEY="facenet512_weights.h5"
ARG INSIGHTFACE_S3_KEY="w600k_r50.onnx"

RUN AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
    AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
    AWS_REGION=${AWS_REGION} \
    MODEL_S3_BUCKET=${MODEL_S3_BUCKET} \
    FACENET_S3_KEY=${FACENET_S3_KEY} \
    INSIGHTFACE_S3_KEY=${INSIGHTFACE_S3_KEY} \
    python preload_models.py

# Expose port
EXPOSE 5001

# Run with gunicorn
# --workers 1       : Single worker — TF/ONNX models are large; multiple workers multiply RAM usage
# --threads 4       : Handle concurrent requests within the single worker
# --timeout 600     : 10 min — face comparison + model init can be slow
# --graceful-timeout 120 : Give worker time to finish in-flight requests on shutdown
# --preload         : Load app (and trigger startup) before forking workers
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "4", "--timeout", "600", "--graceful-timeout", "120", "--worker-class", "gthread", "--preload", "app_v2:app"]
