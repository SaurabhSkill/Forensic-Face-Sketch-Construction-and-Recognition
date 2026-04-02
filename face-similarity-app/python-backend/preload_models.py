"""
preload_models.py
=================
Run during Docker build to download and warm up both face recognition models.
This ensures zero model downloads at container runtime.

Models downloaded:
  - Facenet512 weights (~90 MB)  -> /root/.deepface/weights/
  - InsightFace w600k_r50.onnx (~166 MB) -> /root/.insightface/models/buffalo_l/

Source priority:
  1. AWS S3 (MODEL_S3_BUCKET env var) — fastest, uses your own bucket
  2. Auto-download fallback — DeepFace/InsightFace download from their CDNs

Usage (called by Dockerfile RUN step):
  python preload_models.py
"""

import os
import sys

# ── Silence TF noise during build ────────────────────────────────────────────
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

# ── Paths ─────────────────────────────────────────────────────────────────────
DEEPFACE_WEIGHTS_DIR  = os.path.join(os.path.expanduser("~"), ".deepface", "weights")
INSIGHTFACE_MODEL_DIR = os.path.join(os.path.expanduser("~"), ".insightface", "models", "buffalo_l")
FACENET_WEIGHT_FILE   = os.path.join(DEEPFACE_WEIGHTS_DIR,  "facenet512_weights.h5")
INSIGHTFACE_ONNX_FILE = os.path.join(INSIGHTFACE_MODEL_DIR, "w600k_r50.onnx")

FACENET_MIN_MB    = 80
INSIGHTFACE_MIN_MB = 150


def _size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 * 1024) if os.path.exists(path) else 0.0


def _valid(path: str, min_mb: float) -> bool:
    return os.path.exists(path) and _size_mb(path) >= min_mb


# ── S3 download ───────────────────────────────────────────────────────────────

def _download_from_s3(s3_key: str, local_path: str, label: str) -> bool:
    """Download a single model file from S3. Returns True on success."""
    bucket = os.getenv("MODEL_S3_BUCKET", "")
    region = os.getenv("AWS_REGION", "us-east-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    if not bucket or not access_key or not secret_key:
        print(f"  [S3] Credentials/bucket not set — skipping S3 for {label}")
        return False

    try:
        import boto3
        from botocore.exceptions import ClientError

        s3 = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

        meta = s3.head_object(Bucket=bucket, Key=s3_key)
        total = meta["ContentLength"]
        print(f"  [S3] Downloading {label} ({total / (1024*1024):.1f} MB) from s3://{bucket}/{s3_key}")

        downloaded = [0]

        def _cb(n):
            downloaded[0] += n
            pct = downloaded[0] / total * 100
            if downloaded[0] % (20 * 1024 * 1024) < 1024 * 1024:
                print(f"  [S3]   {pct:.0f}% ({downloaded[0] / (1024*1024):.0f} MB)", flush=True)

        tmp = local_path + ".tmp"
        s3.download_file(bucket, s3_key, tmp, Callback=_cb)

        if os.path.getsize(tmp) == total:
            os.replace(tmp, local_path)
            print(f"  [S3] [OK] {label} saved to {local_path}")
            return True

        os.remove(tmp)
        print(f"  [S3] [FAIL] Size mismatch for {label}")
        return False

    except Exception as exc:
        print(f"  [S3] [FAIL] {label}: {exc}")
        return False


# ── Facenet512 ────────────────────────────────────────────────────────────────

def preload_facenet() -> bool:
    print("\n" + "=" * 60)
    print("PRELOADING Facenet512")
    print("=" * 60)

    os.makedirs(DEEPFACE_WEIGHTS_DIR, exist_ok=True)

    # 1. Already present?
    if _valid(FACENET_WEIGHT_FILE, FACENET_MIN_MB):
        print(f"  [OK] Already present: {FACENET_WEIGHT_FILE} ({_size_mb(FACENET_WEIGHT_FILE):.1f} MB)")
    else:
        # 2. Try S3
        s3_key = os.getenv("FACENET_S3_KEY", "facenet512_weights.h5")
        ok = _download_from_s3(s3_key, FACENET_WEIGHT_FILE, "Facenet512")

        # 3. Fallback: let DeepFace auto-download
        if not ok:
            print("  [FALLBACK] Triggering DeepFace auto-download...")
            try:
                from deepface import DeepFace
                DeepFace.build_model("Facenet512")
                print("  [OK] DeepFace auto-download complete")
            except Exception as exc:
                print(f"  [FAIL] DeepFace auto-download failed: {exc}")
                return False

    # 4. Validate
    if not _valid(FACENET_WEIGHT_FILE, FACENET_MIN_MB):
        print(f"  [FAIL] Weight file missing or too small after download")
        return False

    # 5. Warmup inference — compiles TF graph so first request is instant
    print("  Running warmup inference to compile TF graph...")
    try:
        import numpy as np
        from deepface import DeepFace

        dummy = np.zeros((160, 160, 3), dtype=np.uint8)
        DeepFace.represent(
            img_path=dummy,
            model_name="Facenet512",
            enforce_detection=False,
            align=False,
            detector_backend="skip",
        )
        print("  [OK] Facenet512 warmup complete — TF graph compiled")
        return True
    except Exception as exc:
        print(f"  [WARN] Warmup failed (non-fatal): {exc}")
        # Weight file is present — model will warm up on first request
        return True


# ── InsightFace ───────────────────────────────────────────────────────────────

def preload_insightface() -> bool:
    print("\n" + "=" * 60)
    print("PRELOADING InsightFace (w600k_r50.onnx)")
    print("=" * 60)

    os.makedirs(INSIGHTFACE_MODEL_DIR, exist_ok=True)

    # 1. Already present?
    if _valid(INSIGHTFACE_ONNX_FILE, INSIGHTFACE_MIN_MB):
        print(f"  [OK] Already present: {INSIGHTFACE_ONNX_FILE} ({_size_mb(INSIGHTFACE_ONNX_FILE):.1f} MB)")
    else:
        # 2. Try S3
        s3_key = os.getenv("INSIGHTFACE_S3_KEY", "w600k_r50.onnx")
        ok = _download_from_s3(s3_key, INSIGHTFACE_ONNX_FILE, "InsightFace w600k_r50.onnx")

        # 3. Fallback: download from GitHub release zip
        if not ok:
            print("  [FALLBACK] Downloading buffalo_l.zip from GitHub...")
            try:
                import urllib.request
                import zipfile
                import shutil

                zip_url = (
                    "https://github.com/deepinsight/insightface"
                    "/releases/download/v0.7/buffalo_l.zip"
                )
                zip_path = INSIGHTFACE_ONNX_FILE + ".buffalo_l.zip"

                print(f"  Fetching: {zip_url}")
                urllib.request.urlretrieve(zip_url, zip_path)

                with zipfile.ZipFile(zip_path, "r") as zf:
                    names = zf.namelist()
                    target = next((n for n in names if n.endswith("w600k_r50.onnx")), None)
                    if not target:
                        raise FileNotFoundError(f"w600k_r50.onnx not in zip. Contents: {names}")
                    with zf.open(target) as src, open(INSIGHTFACE_ONNX_FILE, "wb") as dst:
                        shutil.copyfileobj(src, dst)

                os.remove(zip_path)
                print(f"  [OK] Extracted to {INSIGHTFACE_ONNX_FILE}")

            except Exception as exc:
                print(f"  [FAIL] GitHub fallback failed: {exc}")
                return False

    # 4. Validate
    if not _valid(INSIGHTFACE_ONNX_FILE, INSIGHTFACE_MIN_MB):
        print(f"  [FAIL] ONNX file missing or too small after download")
        return False

    # 5. Warmup — load ONNX session and run dummy inference
    print("  Running warmup inference to load ONNX session...")
    try:
        import numpy as np
        import onnxruntime as ort

        sess_opts = ort.SessionOptions()
        sess_opts.log_severity_level = 3  # suppress ONNX verbose output
        sess = ort.InferenceSession(
            INSIGHTFACE_ONNX_FILE,
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        input_name  = sess.get_inputs()[0].name
        output_name = sess.get_outputs()[0].name
        dummy = np.zeros((1, 3, 112, 112), dtype=np.float32)
        out = sess.run([output_name], {input_name: dummy})
        print(f"  [OK] InsightFace warmup complete — output shape: {out[0].shape}")
        return True

    except Exception as exc:
        print(f"  [WARN] Warmup failed (non-fatal): {exc}")
        return True  # ONNX file is present — session loads on first request


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MODEL PRELOADER — Docker build step")
    print("=" * 60)

    facenet_ok    = preload_facenet()
    insightface_ok = preload_insightface()

    print("\n" + "=" * 60)
    print("PRELOAD SUMMARY")
    print("=" * 60)
    print(f"  Facenet512   : {'[OK] READY' if facenet_ok    else '[FAIL] UNAVAILABLE'}")
    print(f"  InsightFace  : {'[OK] READY' if insightface_ok else '[FAIL] UNAVAILABLE'}")
    print("=" * 60)

    if not facenet_ok and not insightface_ok:
        print("\n[FATAL] Both models failed — aborting build")
        sys.exit(1)

    if not facenet_ok or not insightface_ok:
        print("\n[WARN] One model failed — container will attempt download at runtime")

    print("\n[OK] Preload complete\n")
