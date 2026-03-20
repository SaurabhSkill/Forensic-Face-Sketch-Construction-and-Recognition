"""
services/s3_service.py — AWS S3 image storage integration.

Handles all photo upload/delete/signed-URL operations against a
private S3 bucket. Supabase is used only for the PostgreSQL database.

Public API
----------
upload_criminal_photo(criminal_id, image_bytes, filename) -> str  (S3 object key)
delete_criminal_photo(criminal_id, filename)              -> bool
get_signed_url(object_key, expires_in=3600)               -> str  (presigned URL)
"""

from __future__ import annotations

import mimetypes
import os
import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config — all values from environment
# ---------------------------------------------------------------------------

AWS_ACCESS_KEY_ID: str = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY: str = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET_NAME: str = os.environ["AWS_S3_BUCKET_NAME"]

# ---------------------------------------------------------------------------
# Singleton S3 client
# ---------------------------------------------------------------------------

_s3_client = None


def get_s3_client():
    """Return (and lazily initialise) the boto3 S3 client singleton."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
    return _s3_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_object_key(criminal_id: str, filename: str) -> str:
    """
    Build a unique S3 object key.
    e.g.  criminals/CR-0001-TST/a1b2c3d4-photo.jpg
    """
    safe_filename = os.path.basename(filename) or "photo.jpg"
    _, ext = os.path.splitext(safe_filename)
    if not ext:
        ext = ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"criminals/{criminal_id}/{unique_name}"


def _guess_content_type(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "image/jpeg"


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def upload_criminal_photo(
    criminal_id: str,
    image_bytes: bytes,
    filename: str,
) -> str:
    """
    Upload a criminal photo to S3 (private bucket).

    Parameters
    ----------
    criminal_id : str   e.g. "CR-0001-TST"
    image_bytes : bytes raw image data
    filename    : str   original filename (used to derive content-type and key)

    Returns
    -------
    str  S3 object key (NOT a URL). Store this in the database.

    Raises
    ------
    RuntimeError on upload failure.
    """
    import io

    s3 = get_s3_client()
    object_key = _build_object_key(criminal_id, filename)
    content_type = _guess_content_type(filename)

    try:
        s3.upload_fileobj(
            io.BytesIO(image_bytes),
            S3_BUCKET_NAME,
            object_key,
            ExtraArgs={"ContentType": content_type},
            # No ACL — bucket is private, no public-read
        )
    except ClientError as exc:
        raise RuntimeError(f"S3 upload failed for {object_key}: {exc}") from exc

    return object_key


def delete_criminal_photo(criminal_id: str, object_key: str) -> bool:
    """
    Remove a criminal's photo from S3.

    Parameters
    ----------
    criminal_id : str  (unused but kept for API compatibility)
    object_key  : str  S3 object key stored in the database

    Returns True on success, False on failure.
    """
    if not object_key:
        return False

    s3 = get_s3_client()
    try:
        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=object_key)
        return True
    except ClientError as exc:
        print(f"[S3] delete failed for {object_key}: {exc}")
        return False


def get_signed_url(object_key: str, expires_in: int = 3600) -> Optional[str]:
    """
    Generate a time-limited presigned URL for private S3 object access.

    Parameters
    ----------
    object_key : str  S3 object key stored in the database
    expires_in : int  seconds until the URL expires (default 1 hour)

    Returns
    -------
    str  Presigned URL, or None if generation fails.
    """
    if not object_key:
        return None

    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": object_key},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as exc:
        print(f"[S3] presigned URL generation failed for {object_key}: {exc}")
        return None
