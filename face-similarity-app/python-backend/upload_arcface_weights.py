"""
upload_arcface_weights.py
=========================
One-time utility to upload arcface_weights.h5 to the project S3 bucket.

USAGE:
    python upload_arcface_weights.py [--path /custom/path/to/arcface_weights.h5]

The file will be stored at: s3://<bucket>/models/arcface_weights.h5
The server will download it automatically on next startup.

HOW TO GET THE WEIGHTS FILE:
    The complete arcface_weights.h5 (~130 MB) can be obtained by:
    1. Running deepface on a machine where the download works:
         python -c "from deepface import DeepFace; DeepFace.build_model('ArcFace')"
       Then copy ~/.deepface/weights/arcface_weights.h5

    2. Or download manually from Google Drive (if accessible):
         https://drive.google.com/uc?id=1LVB3CdVejpmGHM28BpqqkbZP5hDEcdZY
"""

import argparse
import os
import sys

import boto3
from dotenv import load_dotenv

load_dotenv()

WEIGHTS_DIR = os.path.join(os.path.expanduser("~"), ".deepface", "weights")
S3_KEY = "models/arcface_weights.h5"
MIN_SIZE = 120 * 1024 * 1024   # 120 MB — complete file is ~130 MB
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"


def is_valid_hdf5(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            header = f.read(8)
        if header != HDF5_MAGIC:
            return False
        import h5py
        with h5py.File(path, "r"):
            pass
        return True
    except Exception:
        return False


def find_local_file(custom_path: str = None) -> str:
    """Find the best available local arcface weights file."""
    if custom_path:
        if os.path.exists(custom_path):
            return custom_path
        print(f"ERROR: Specified path not found: {custom_path}")
        sys.exit(1)

    candidates = []
    if os.path.exists(WEIGHTS_DIR):
        for fname in os.listdir(WEIGHTS_DIR):
            if "arcface" not in fname.lower():
                continue
            path = os.path.join(WEIGHTS_DIR, fname)
            size = os.path.getsize(path)
            valid = is_valid_hdf5(path)
            candidates.append((path, size, valid))
            status = "VALID" if valid else "INVALID/TRUNCATED"
            print(f"  {fname}: {size/1024/1024:.1f} MB [{status}]")

    # Prefer valid files >= MIN_SIZE
    valid_large = [(p, s) for p, s, v in candidates if v and s >= MIN_SIZE]
    if valid_large:
        return max(valid_large, key=lambda x: x[1])[0]

    # Any valid file
    valid_any = [(p, s) for p, s, v in candidates if v]
    if valid_any:
        best = max(valid_any, key=lambda x: x[1])
        print(f"WARNING: Best valid file is only {best[1]/1024/1024:.1f} MB (expected ~130 MB)")
        return best[0]

    return None


def main():
    parser = argparse.ArgumentParser(description="Upload arcface_weights.h5 to S3")
    parser.add_argument("--path", help="Path to arcface_weights.h5 (optional)")
    parser.add_argument("--force", action="store_true", help="Re-upload even if already in S3")
    args = parser.parse_args()

    print("=" * 60)
    print("ArcFace Weights S3 Upload")
    print("=" * 60)

    bucket = os.environ.get("AWS_S3_BUCKET_NAME")
    region = os.environ.get("AWS_REGION", "us-east-1")
    key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")

    if not all([bucket, key_id, secret]):
        print("ERROR: AWS credentials not set. Check .env file.")
        sys.exit(1)

    print(f"Bucket : {bucket}")
    print(f"S3 key : {S3_KEY}")
    print()

    s3 = boto3.client("s3", region_name=region,
                      aws_access_key_id=key_id,
                      aws_secret_access_key=secret)

    # Check if already uploaded
    if not args.force:
        try:
            obj = s3.head_object(Bucket=bucket, Key=S3_KEY)
            size_mb = obj["ContentLength"] / 1024 / 1024
            if obj["ContentLength"] >= MIN_SIZE:
                print(f"[OK] Already in S3: {S3_KEY} ({size_mb:.1f} MB)")
                print("Use --force to re-upload.")
                return
            else:
                print(f"S3 file too small ({size_mb:.1f} MB), re-uploading...")
        except Exception:
            print("Not yet in S3, proceeding...")

    # Find local file
    print(f"\nScanning for local weights in: {WEIGHTS_DIR}")
    local_path = find_local_file(args.path)

    if not local_path:
        print("\nERROR: No arcface_weights.h5 found locally.")
        print("\nTo get the file:")
        print("  1. On a machine with internet access, run:")
        print("       python -c \"from deepface import DeepFace; DeepFace.build_model('ArcFace')\"")
        print(f"     Then copy: ~/.deepface/weights/arcface_weights.h5")
        print("  2. Or download from Google Drive:")
        print("       https://drive.google.com/uc?id=1LVB3CdVejpmGHM28BpqqkbZP5hDEcdZY")
        print(f"  3. Place the file at: {WEIGHTS_DIR}/arcface_weights.h5")
        print("  4. Re-run this script.")
        sys.exit(1)

    size_mb = os.path.getsize(local_path) / 1024 / 1024
    valid = is_valid_hdf5(local_path)
    print(f"\nFile   : {local_path}")
    print(f"Size   : {size_mb:.1f} MB")
    print(f"Valid  : {valid}")

    if not valid:
        print("\nERROR: File is not a valid/complete HDF5. Cannot upload.")
        sys.exit(1)

    if size_mb < 100:
        print(f"\nWARNING: File is only {size_mb:.1f} MB (expected ~130 MB).")
        ans = input("Upload anyway? [y/N]: ").strip().lower()
        if ans != "y":
            sys.exit(0)

    print(f"\nUploading {size_mb:.1f} MB to S3... (this may take a minute)")
    try:
        s3.upload_file(
            local_path, bucket, S3_KEY,
            ExtraArgs={"ContentType": "application/octet-stream"},
        )
    except Exception as e:
        print(f"ERROR: Upload failed: {e}")
        sys.exit(1)

    # Verify
    obj = s3.head_object(Bucket=bucket, Key=S3_KEY)
    uploaded_mb = obj["ContentLength"] / 1024 / 1024
    print(f"\n[OK] Uploaded: s3://{bucket}/{S3_KEY} ({uploaded_mb:.1f} MB)")
    print("The server will download this automatically on next startup.")


if __name__ == "__main__":
    main()
