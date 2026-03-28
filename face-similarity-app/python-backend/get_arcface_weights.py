"""
get_arcface_weights.py
======================
Downloads arcface_weights.h5 (~130 MB) and uploads it to S3.

Run this ONCE on any machine that can reach the download source:

    python get_arcface_weights.py

After this, the server downloads from S3 automatically on every startup.

DOWNLOAD SOURCES (tried in order):
  1. S3 self-hosted  (if already uploaded)
  2. deepface built-in gdown (Google Drive)
  3. Internet Archive
  4. Manual path     (--file /path/to/arcface_weights.h5)

USAGE:
    python get_arcface_weights.py
    python get_arcface_weights.py --file /path/to/arcface_weights.h5
    python get_arcface_weights.py --skip-upload   (local only, no S3)
"""

import argparse
import os
import sys
import shutil

HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
WEIGHTS_DIR = os.path.join(os.path.expanduser("~"), ".deepface", "weights")
TARGET = os.path.join(WEIGHTS_DIR, "arcface_weights.h5")
S3_KEY = "models/arcface_weights.h5"
MIN_SIZE = 120 * 1024 * 1024   # 120 MB — complete file is ~130 MB
GDRIVE_ID = "1LVB3CdVejpmGHM28BpqqkbZP5hDEcdZY"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(path: str) -> tuple:
    """Returns (ok: bool, reason: str)"""
    if not os.path.exists(path):
        return False, "file does not exist"
    size = os.path.getsize(path)
    if size < MIN_SIZE:
        return False, f"too small: {size/1024/1024:.1f} MB (need >{MIN_SIZE//1024//1024} MB)"
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        if header != HDF5_MAGIC:
            return False, f"invalid HDF5 magic: {header.hex()}"
        import h5py
        with h5py.File(path, "r") as f:
            keys = list(f.keys())[:2]
        return True, f"valid HDF5, {size/1024/1024:.1f} MB, keys={keys}"
    except Exception as e:
        return False, f"HDF5 open failed: {e}"


# ---------------------------------------------------------------------------
# Download strategies
# ---------------------------------------------------------------------------

def try_deepface_builtin() -> bool:
    """Let deepface download via its own gdown mechanism."""
    print("\n[Source 1] deepface built-in download (gdown/Google Drive)...")
    tmp = TARGET + ".deepface_dl"
    if os.path.exists(tmp):
        os.remove(tmp)
    try:
        import gdown
        url = f"https://drive.google.com/uc?id={GDRIVE_ID}"
        gdown.download(url, tmp, quiet=False, fuzzy=True)
        if os.path.exists(tmp):
            ok, reason = validate(tmp)
            if ok:
                _install(tmp)
                return True
            print(f"  Validation failed: {reason}")
            os.remove(tmp)
    except Exception as e:
        print(f"  Failed: {e}")
    return False


def try_wayback_machine() -> bool:
    """Try Internet Archive for the file."""
    print("\n[Source 2] Internet Archive (Wayback Machine)...")
    import urllib.request, json
    try:
        api = ("http://archive.org/wayback/available?url="
               "github.com/serengil/deepface_models/releases/download/v1.0/arcface_weights.h5")
        with urllib.request.urlopen(api, timeout=10) as r:
            data = json.loads(r.read())
        snap = data.get("archived_snapshots", {}).get("closest", {})
        if not snap.get("available"):
            print("  No snapshot available in Wayback Machine")
            return False
        wb_url = snap["url"]
        print(f"  Snapshot found: {wb_url}")
        return _download_url(wb_url, "wayback")
    except Exception as e:
        print(f"  Failed: {e}")
    return False


def try_github_direct() -> bool:
    """Try GitHub releases URL directly."""
    print("\n[Source 3] GitHub releases (may be 404)...")
    url = ("https://github.com/serengil/deepface_models/"
           "releases/download/v1.0/arcface_weights.h5")
    return _download_url(url, "github")


def _download_url(url: str, label: str) -> bool:
    import urllib.request
    tmp = TARGET + f".{label}_dl"
    if os.path.exists(tmp):
        os.remove(tmp)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/octet-stream, */*",
        })
        print(f"  Downloading from: {url}")
        with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as f:
            total = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                total += len(chunk)
                if total % (10 * 1024 * 1024) == 0:
                    print(f"  ... {total/1024/1024:.0f} MB", end="\r")
        print(f"  Downloaded: {total/1024/1024:.1f} MB")
        ok, reason = validate(tmp)
        if ok:
            _install(tmp)
            return True
        print(f"  Validation failed: {reason}")
        os.remove(tmp)
    except Exception as e:
        print(f"  Failed: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
    return False


def _install(tmp_path: str):
    """Move downloaded file to final location."""
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    if os.path.exists(TARGET):
        os.remove(TARGET)
    shutil.move(tmp_path, TARGET)
    ok, reason = validate(TARGET)
    print(f"  Installed: {TARGET}")
    print(f"  Validation: {reason}")


# ---------------------------------------------------------------------------
# S3 upload
# ---------------------------------------------------------------------------

def upload_to_s3() -> bool:
    print("\n[S3] Uploading to S3...")
    try:
        import boto3
        from dotenv import load_dotenv
        load_dotenv()

        bucket = os.environ.get("AWS_S3_BUCKET_NAME")
        region = os.environ.get("AWS_REGION", "us-east-1")
        key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")

        if not all([bucket, key_id, secret]):
            print("  S3 credentials not configured, skipping upload")
            return False

        s3 = boto3.client("s3", region_name=region,
                          aws_access_key_id=key_id,
                          aws_secret_access_key=secret)

        # Check if already uploaded with correct size
        try:
            obj = s3.head_object(Bucket=bucket, Key=S3_KEY)
            s3_size = obj["ContentLength"]
            local_size = os.path.getsize(TARGET)
            if s3_size == local_size:
                print(f"  Already in S3 with correct size ({s3_size/1024/1024:.1f} MB)")
                return True
            print(f"  S3 has {s3_size/1024/1024:.1f} MB, local has {local_size/1024/1024:.1f} MB — re-uploading")
        except Exception:
            pass

        local_size_mb = os.path.getsize(TARGET) / 1024 / 1024
        print(f"  Uploading {local_size_mb:.1f} MB to s3://{bucket}/{S3_KEY}")
        s3.upload_file(TARGET, bucket, S3_KEY,
                       ExtraArgs={"ContentType": "application/octet-stream"})

        obj = s3.head_object(Bucket=bucket, Key=S3_KEY)
        print(f"  [OK] Uploaded: {obj['ContentLength']/1024/1024:.1f} MB")
        return True

    except Exception as e:
        print(f"  S3 upload failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", help="Path to existing arcface_weights.h5")
    parser.add_argument("--skip-upload", action="store_true",
                        help="Skip S3 upload (local install only)")
    args = parser.parse_args()

    print("=" * 60)
    print("ArcFace Weights Installer")
    print("=" * 60)

    # Check if already valid locally
    ok, reason = validate(TARGET)
    if ok:
        print(f"\n[OK] Already valid: {reason}")
        if not args.skip_upload:
            upload_to_s3()
        return

    print(f"\nCurrent state: {reason}")

    # Manual file provided
    if args.file:
        ok, reason = validate(args.file)
        if not ok:
            print(f"ERROR: Provided file is invalid: {reason}")
            sys.exit(1)
        _install(args.file)
        if not args.skip_upload:
            upload_to_s3()
        print("\n[SUCCESS] ArcFace weights installed!")
        return

    # Try download sources
    success = (
        try_deepface_builtin() or
        try_wayback_machine() or
        try_github_direct()
    )

    if success:
        if not args.skip_upload:
            upload_to_s3()
        print("\n[SUCCESS] ArcFace weights installed and uploaded to S3!")
        print("The server will load ArcFace automatically on next startup.")
        return

    # All sources failed
    print("\n" + "=" * 60)
    print("FAILED: Could not download arcface_weights.h5 automatically.")
    print("=" * 60)
    print()
    print("MANUAL STEPS:")
    print("  1. On a machine with unrestricted internet access, run:")
    print("       python -c \"from deepface import DeepFace; DeepFace.build_model('ArcFace')\"")
    print(f"     This saves the file to: ~/.deepface/weights/arcface_weights.h5")
    print()
    print("  2. Copy the file (~130 MB) to this machine at:")
    print(f"     {TARGET}")
    print()
    print("  3. Run this script again:")
    print("       python get_arcface_weights.py --file /path/to/arcface_weights.h5")
    print()
    print("  OR: Copy directly to the weights directory and restart the server.")
    sys.exit(1)


if __name__ == "__main__":
    main()
