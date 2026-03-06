"""
File handling utilities for temporary file management
"""
import os
import uuid
import hashlib
import cv2
from typing import Optional


# Temp uploads directory (will be set by app initialization)
TEMP_UPLOADS_DIR = None


def set_temp_uploads_dir(directory: str):
    """
    Set the temp uploads directory path
    
    Args:
        directory: Path to temp uploads directory
    """
    global TEMP_UPLOADS_DIR
    TEMP_UPLOADS_DIR = directory
    os.makedirs(TEMP_UPLOADS_DIR, exist_ok=True)


def get_temp_uploads_dir() -> str:
    """
    Get the temp uploads directory path
    
    Returns:
        str: Path to temp uploads directory
    """
    return TEMP_UPLOADS_DIR


def generate_temp_filepath(original_filename: str = None, prefix: str = '') -> str:
    """
    Generate a unique filepath in temp_uploads folder
    
    Args:
        original_filename: Original filename (optional, for extension)
        prefix: Prefix for the filename (e.g., 'sketch', 'photo', 'preprocessed')
    
    Returns:
        str: Full path to temp file
    """
    unique_id = str(uuid.uuid4())
    
    # Extract extension from original filename if provided
    if original_filename:
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.jpg'
    else:
        ext = '.jpg'
    
    # Build filename
    if prefix:
        filename = f"{prefix}_{unique_id}{ext}"
    else:
        filename = f"{unique_id}{ext}"
    
    return os.path.join(TEMP_UPLOADS_DIR, filename)


def cleanup_temp_file(filepath: str):
    """
    Safely delete a temp file
    
    Args:
        filepath: Path to file to delete
    """
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"[WARNING] Failed to cleanup temp file {filepath}: {e}")


def get_file_hash(file_path: str) -> Optional[str]:
    """
    Generate MD5 hash of file content for caching using chunked reading
    
    Uses chunked reading to avoid loading entire file into memory,
    which is important for large image files.
    
    Args:
        file_path: Path to file
    
    Returns:
        str: MD5 hash of file content, or None if error
    """
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            # Read file in 8KB chunks to avoid memory issues with large files
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"[WARNING] Failed to compute file hash for {file_path}: {e}")
        return None


def save_temp_file(file_storage) -> str:
    """
    Save uploaded file to temp_uploads folder
    
    Args:
        file_storage: Flask FileStorage object
    
    Returns:
        str: Path to saved file
    """
    filepath = generate_temp_filepath(original_filename=file_storage.filename, prefix='upload')
    file_storage.save(filepath)
    
    # Validate file was saved
    if not os.path.exists(filepath):
        raise IOError(f"Failed to save uploaded file to: {filepath}")
    
    # Validate file can be read by cv2
    test_img = cv2.imread(filepath)
    if test_img is None:
        cleanup_temp_file(filepath)
        raise IOError(f"Uploaded file is corrupted or invalid format: {file_storage.filename}")
    
    return filepath


def save_bytes_to_temp(data: bytes, original_filename: str) -> str:
    """
    Save bytes data to temp_uploads folder
    
    Args:
        data: Image data as bytes
        original_filename: Original filename (for extension)
    
    Returns:
        str: Path to saved file
    """
    filepath = generate_temp_filepath(original_filename=original_filename, prefix='bytes')
    with open(filepath, 'wb') as f:
        f.write(data)
    
    # Validate file was saved
    if not os.path.exists(filepath):
        raise IOError(f"Failed to save bytes to file: {filepath}")
    
    # Validate file can be read by cv2
    test_img = cv2.imread(filepath)
    if test_img is None:
        cleanup_temp_file(filepath)
        raise IOError(f"Saved bytes data is corrupted or invalid format")
    
    return filepath
