"""
Image preprocessing utilities for face recognition
Handles basic image operations like loading, conversion, and resizing
"""
import os
import cv2
import numpy as np
import traceback


def load_image(image_path: str) -> np.ndarray:
    """
    Load image from file path with robust validation
    
    Performs comprehensive validation:
    1. Checks if file exists
    2. Attempts to read with cv2.imread()
    3. Validates image is not None
    4. Validates image has valid dimensions
    
    Args:
        image_path: Path to image file
    
    Returns:
        np.ndarray: Loaded image or None if failed
    """
    try:
        # Step 1: Check if file exists
        if not os.path.exists(image_path):
            print(f"  [ERROR] Image file does not exist: {image_path}")
            return None
        
        # Step 2: Attempt to read image
        img = cv2.imread(image_path)
        
        # Step 3: Verify image is not None
        if img is None:
            print(f"  [ERROR] cv2.imread() returned None - image may be corrupted or invalid format: {image_path}")
            return None
        
        # Step 4: Validate image shape (must have valid dimensions)
        if not hasattr(img, 'shape') or len(img.shape) < 2:
            print(f"  [ERROR] Invalid image shape - image does not have valid dimensions: {image_path}")
            return None
        
        # Validate dimensions are positive
        height, width = img.shape[:2]
        if height <= 0 or width <= 0:
            print(f"  [ERROR] Invalid image dimensions: {width}x{height} - {image_path}")
            return None
        
        # Validate reasonable size (not too small, not too large)
        if height < 10 or width < 10:
            print(f"  [ERROR] Image too small: {width}x{height} (minimum 10x10) - {image_path}")
            return None
        
        if height > 10000 or width > 10000:
            print(f"  [ERROR] Image too large: {width}x{height} (maximum 10000x10000) - {image_path}")
            return None
        
        # All validations passed
        return img
        
    except Exception as e:
        print(f"  [ERROR] Exception loading image: {e}")
        traceback.print_exc()
        return None


def convert_to_grayscale(img: np.ndarray) -> np.ndarray:
    """
    Convert image to grayscale
    
    Args:
        img: Input image (BGR or already grayscale)
    
    Returns:
        np.ndarray: Grayscale image
    """
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def convert_to_bgr(img: np.ndarray) -> np.ndarray:
    """
    Convert grayscale image to 3-channel BGR
    
    Args:
        img: Grayscale image
    
    Returns:
        np.ndarray: BGR image
    """
    if len(img.shape) == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def resize_to_arcface_size(img: np.ndarray, target_size: int = 112) -> np.ndarray:
    """
    Resize image to ArcFace native input size (112x112)
    
    Args:
        img: Input image
        target_size: Target size (default 112 for ArcFace)
    
    Returns:
        np.ndarray: Resized image
    """
    return cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)


def apply_canny_edge_detection(gray_img: np.ndarray, threshold1: int = 50, threshold2: int = 150) -> np.ndarray:
    """
    Apply Canny edge detection to grayscale image
    
    Args:
        gray_img: Grayscale image
        threshold1: Lower threshold for Canny
        threshold2: Upper threshold for Canny
    
    Returns:
        np.ndarray: Edge-detected image
    """
    return cv2.Canny(gray_img, threshold1=threshold1, threshold2=threshold2)


def apply_bilateral_filter(gray_img: np.ndarray, d: int = 9, sigma_color: int = 75, sigma_space: int = 75) -> np.ndarray:
    """
    Apply bilateral filter to reduce noise while preserving edges
    
    Args:
        gray_img: Grayscale image
        d: Diameter of pixel neighborhood
        sigma_color: Filter sigma in color space
        sigma_space: Filter sigma in coordinate space
    
    Returns:
        np.ndarray: Filtered image
    """
    return cv2.bilateralFilter(gray_img, d, sigma_color, sigma_space)


def apply_histogram_equalization(gray_img: np.ndarray) -> np.ndarray:
    """
    Apply histogram equalization for consistent brightness
    
    Args:
        gray_img: Grayscale image
    
    Returns:
        np.ndarray: Equalized image
    """
    return cv2.equalizeHist(gray_img)


def validate_image_file(image_path: str) -> bool:
    """
    Validate that image file exists and can be read by cv2
    
    Args:
        image_path: Path to image file
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not os.path.exists(image_path):
        print(f"  [ERROR] Image file does not exist: {image_path}")
        return False
    
    test_img = cv2.imread(image_path)
    if test_img is None:
        print(f"  [ERROR] cv2.imread() failed - image is corrupted or invalid: {image_path}")
        return False
    
    return True


def save_image(img: np.ndarray, output_path: str, quality: int = 95) -> bool:
    """
    Save image to file with validation
    
    Args:
        img: Image to save
        output_path: Output file path
        quality: JPEG quality (0-100)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Write image
        write_success = cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not write_success:
            print(f"  [ERROR] Failed to write image to: {output_path}")
            return False
        
        # Validate file exists
        if not os.path.exists(output_path):
            print(f"  [ERROR] Image file does not exist after write: {output_path}")
            return False
        
        # Validate file can be read
        test_img = cv2.imread(output_path)
        if test_img is None:
            print(f"  [ERROR] cv2.imread() failed on saved file: {output_path}")
            return False
        
        return True
        
    except Exception as e:
        print(f"  [ERROR] Exception saving image: {e}")
        traceback.print_exc()
        return False
