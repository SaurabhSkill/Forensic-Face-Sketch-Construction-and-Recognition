"""
S3 Model Loader
===============
Downloads face recognition models from AWS S3 if not present locally.

Models:
  - facenet512_weights.h5 (~90 MB) → ~/.deepface/weights/
  - w600k_r50.onnx (~166 MB) → ~/.insightface/models/buffalo_l/

Uses AWS credentials from .env (boto3 auto-loads from environment).

IMPORTANT: Uses separate S3 bucket for models (MODEL_S3_BUCKET)
           Criminal images use AWS_S3_BUCKET_NAME (do NOT mix)
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# S3 Configuration - SEPARATE buckets for models and images
MODEL_S3_BUCKET = os.getenv("MODEL_S3_BUCKET", "forensic-models")
S3_REGION = os.getenv("AWS_REGION", "us-east-1")

# Model definitions: (s3_key, local_path, min_size_mb)
# S3 keys are stored at root level (no "models/" prefix)
MODELS = {
    "facenet512": {
        "s3_key": os.getenv("FACENET_S3_KEY", "facenet512_weights.h5"),
        "local_dir": os.path.join(os.path.expanduser("~"), ".deepface", "weights"),
        "filename": "facenet512_weights.h5",
        "min_size_mb": 80,
    },
    "insightface": {
        "s3_key": os.getenv("INSIGHTFACE_S3_KEY", "w600k_r50.onnx"),
        "local_dir": os.path.join(os.path.expanduser("~"), ".insightface", "models", "buffalo_l"),
        "filename": "w600k_r50.onnx",
        "min_size_mb": 150,
    },
}


def _get_s3_client():
    """Create and return S3 client using credentials from environment."""
    try:
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if not access_key or not secret_key:
            print("[S3] AWS credentials not found in environment")
            return None
        
        client = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        return client
    except Exception as e:
        print(f"[S3] Failed to create S3 client: {e}")
        return None


def _validate_model_file(file_path: str, min_size_mb: int) -> bool:
    """
    Validate that model file exists and meets minimum size requirement.
    
    Args:
        file_path: Path to model file
        min_size_mb: Minimum expected size in MB
    
    Returns:
        True if file is valid, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb < min_size_mb:
        print(f"[S3] File too small: {size_mb:.1f} MB (expected >= {min_size_mb} MB)")
        return False
    
    return True


def _download_from_s3(s3_client, s3_key: str, local_path: str, model_name: str) -> bool:
    """
    Download a file from S3 to local path with progress indication.
    
    Args:
        s3_client: boto3 S3 client
        s3_key: S3 object key (exact key, no prefix)
        local_path: Local destination path
        model_name: Model name for logging
    
    Returns:
        True if download successful, False otherwise
    """
    if not MODEL_S3_BUCKET:
        print(f"[S3] MODEL_S3_BUCKET not configured in .env")
        return False
    
    try:
        # Get file size from S3
        response = s3_client.head_object(Bucket=MODEL_S3_BUCKET, Key=s3_key)
        file_size = response["ContentLength"]
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"[S3] Downloading {model_name} from S3...")
        print(f"[S3]   Bucket: {MODEL_S3_BUCKET}")
        print(f"[S3]   Key: {s3_key}")
        print(f"[S3]   Size: {file_size_mb:.1f} MB")
        print(f"[S3]   Destination: {local_path}")
        
        # Download with progress callback
        downloaded = [0]
        
        def progress_callback(bytes_transferred):
            downloaded[0] += bytes_transferred
            percent = (downloaded[0] / file_size) * 100
            if downloaded[0] % (10 * 1024 * 1024) == 0 or downloaded[0] == file_size:
                print(f"[S3]   Progress: {percent:.1f}% ({downloaded[0] / (1024*1024):.1f} MB)")
        
        # Create temporary file
        temp_path = local_path + ".tmp"
        s3_client.download_file(
            MODEL_S3_BUCKET,
            s3_key,
            temp_path,
            Callback=progress_callback
        )
        
        # Verify download
        if os.path.exists(temp_path):
            actual_size = os.path.getsize(temp_path)
            if actual_size == file_size:
                # Move to final location
                if os.path.exists(local_path):
                    os.remove(local_path)
                os.rename(temp_path, local_path)
                print(f"[S3] [OK] {model_name} downloaded successfully")
                return True
            else:
                print(f"[S3] [FAIL] Size mismatch: expected {file_size}, got {actual_size}")
                os.remove(temp_path)
                return False
        
        return False
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "404":
            print(f"[S3] [FAIL] Model not found in S3: s3://{MODEL_S3_BUCKET}/{s3_key}")
            print(f"[S3] [FAIL] Please upload the model file to S3 at this exact location")
        elif error_code == "403":
            print(f"[S3] [FAIL] Access denied to s3://{MODEL_S3_BUCKET}/{s3_key}")
            print(f"[S3] [FAIL] Check IAM permissions for AWS credentials")
        else:
            print(f"[S3] [FAIL] AWS error: {error_code} - {e}")
        return False
    except NoCredentialsError:
        print(f"[S3] [FAIL] AWS credentials not configured")
        print(f"[S3] [FAIL] Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env")
        return False
    except Exception as e:
        print(f"[S3] [FAIL] Download failed: {e}")
        temp_path = local_path + ".tmp"
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False


def setup_models() -> dict:
    """
    Ensure all required models are present locally.
    Downloads from S3 if missing or invalid.
    
    Returns:
        dict: Status of each model {model_name: bool}
    """
    print("\n" + "=" * 60)
    print("S3 MODEL LOADER - Checking model availability")
    print("=" * 60)
    
    results = {}
    s3_client = None
    
    for model_name, config in MODELS.items():
        local_path = os.path.join(config["local_dir"], config["filename"])
        
        print(f"\n[{model_name.upper()}]")
        print(f"  Local path: {local_path}")
        
        # Check if model already exists and is valid
        if _validate_model_file(local_path, config["min_size_mb"]):
            size_mb = os.path.getsize(local_path) / (1024 * 1024)
            print(f"  Status: EXISTS ({size_mb:.1f} MB)")
            print(f"  Action: SKIP (already present)")
            results[model_name] = True
            continue
        
        # Model missing or invalid - need to download
        print(f"  Status: MISSING or INVALID")
        print(f"  Action: DOWNLOAD from S3")
        
        # Create S3 client if not already created
        if s3_client is None:
            s3_client = _get_s3_client()
            if s3_client is None:
                print(f"  [FAIL] Cannot create S3 client - check AWS credentials")
                results[model_name] = False
                continue
        
        # Ensure local directory exists
        os.makedirs(config["local_dir"], exist_ok=True)
        
        # Download from S3
        success = _download_from_s3(
            s3_client,
            config["s3_key"],
            local_path,
            model_name
        )
        
        if success:
            # Validate downloaded file
            if _validate_model_file(local_path, config["min_size_mb"]):
                size_mb = os.path.getsize(local_path) / (1024 * 1024)
                print(f"  [OK] Validated: {size_mb:.1f} MB")
                results[model_name] = True
            else:
                print(f"  [FAIL] Downloaded file failed validation")
                results[model_name] = False
        else:
            results[model_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("MODEL AVAILABILITY SUMMARY")
    print("=" * 60)
    for model_name, status in results.items():
        status_str = "[OK] READY" if status else "[FAIL] UNAVAILABLE"
        print(f"  {model_name.upper()}: {status_str}")
    print("=" * 60 + "\n")
    
    return results


def get_model_paths() -> dict:
    """
    Get local paths for all models.
    
    Returns:
        dict: {model_name: local_path}
    """
    return {
        model_name: os.path.join(config["local_dir"], config["filename"])
        for model_name, config in MODELS.items()
    }


if __name__ == "__main__":
    # Test the loader
    print("Testing S3 Model Loader...")
    results = setup_models()
    
    print("\nModel paths:")
    for name, path in get_model_paths().items():
        exists = os.path.exists(path)
        print(f"  {name}: {path} ({'EXISTS' if exists else 'MISSING'})")
