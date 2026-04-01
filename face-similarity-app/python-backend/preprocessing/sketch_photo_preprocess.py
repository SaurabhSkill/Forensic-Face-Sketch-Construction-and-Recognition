"""
Sketch and photo preprocessing utilities for cross-domain face matching
Handles domain gap reduction between sketches and photos
"""
import os
import cv2
import numpy as np
import uuid
import traceback
from deepface import DeepFace

# Import from sibling modules
from preprocessing.image_preprocessing import (
    load_image,
    convert_to_grayscale,
    convert_to_bgr,
    resize_to_arcface_size,
    apply_canny_edge_detection,
    apply_bilateral_filter,
    apply_histogram_equalization,
    save_image
)
from utils.file_utils import generate_temp_filepath, cleanup_temp_file
from utils.similarity_utils import cosine_similarity


def is_sketch_image(image_path: str) -> bool:
    """
    Detect if an image is a sketch based on characteristics:
    - Low color saturation (mostly grayscale)
    - High edge density
    
    DETERMINISTIC: Uses fixed thresholds for consistent classification
    NOTE: This is for logging/debugging only - does NOT affect preprocessing
    
    Thresholds (improved for reliability):
    - Saturation: < 25 (was 30) - More strict to avoid low-saturation photos
    - Edge density: > 0.08 (was 0.05) - More strict to require clear sketch lines
    
    Args:
        image_path: Path to image file
    
    Returns:
        bool: True if image is a sketch, False otherwise
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            return False
        
        # Convert to HSV to check saturation
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        avg_saturation = float(np.mean(saturation))
        
        # Sketches have very low saturation (< 25)
        # Photos have higher saturation (> 30)
        # Improved threshold: 25 (was 30) - more strict
        is_low_saturation = avg_saturation < 25
        
        # Check edge density (sketches have more edges)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = float(np.sum(edges > 0)) / float(edges.size)
        
        # Sketches have higher edge density (> 0.08)
        # Improved threshold: 0.08 (was 0.05) - more strict
        is_high_edges = edge_density > 0.08
        
        # Calculate confidence scores
        # Saturation confidence: how far from threshold
        saturation_threshold = 25
        saturation_confidence = max(0.0, min(1.0, (saturation_threshold - avg_saturation) / saturation_threshold))
        
        # Edge density confidence: how far from threshold
        edge_threshold = 0.08
        edge_confidence = max(0.0, min(1.0, (edge_density - edge_threshold) / edge_threshold))
        
        # Overall confidence: average of both
        overall_confidence = (saturation_confidence + edge_confidence) / 2.0 if (is_low_saturation and is_high_edges) else 0.0
        
        # Debug output with confidence
        print(f"  [SKETCH DETECTION]")
        print(f"    Saturation: {avg_saturation:.2f} (threshold: < {saturation_threshold}) - {'[LOW]' if is_low_saturation else '[HIGH]'}")
        print(f"    Edge density: {edge_density:.4f} (threshold: > {edge_threshold}) - {'[HIGH]' if is_high_edges else '[LOW]'}")
        print(f"    Saturation confidence: {saturation_confidence:.2%}")
        print(f"    Edge confidence: {edge_confidence:.2%}")
        print(f"    Overall confidence: {overall_confidence:.2%}")
        
        # Both conditions must be met
        result = is_low_saturation and is_high_edges
        
        if result:
            print(f"    Classification: SKETCH (confidence: {overall_confidence:.2%})")
        else:
            print(f"    Classification: PHOTO")
            if is_low_saturation and not is_high_edges:
                print(f"      Reason: Low saturation but insufficient edge density")
            elif not is_low_saturation and is_high_edges:
                print(f"      Reason: High edge density but too much color saturation")
            else:
                print(f"      Reason: Neither low saturation nor high edge density")
        
        return result
        
    except Exception as e:
        print(f"  [SKETCH DETECTION ERROR] {e}")
        return False


def preprocess_for_edge_based_matching(image_path: str, is_sketch: bool = False) -> str:
    """
    STEP 2: Edge-based preprocessing to reduce sketch-photo domain gap
    
    **USAGE:** Test endpoints only (/api/test/edge-preprocessing, /api/test/compare-edges)
    **PRODUCTION:** Main flow uses preprocess_for_cross_domain_matching() instead
    
    For PHOTOS: Extract edges to make them look more like sketches
    For SKETCHES: Minimal processing (just enhancement)
    
    This reduces the domain gap by converting both to edge-based representations.
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
    
    Returns:
        str: Path to preprocessed image file
    """
    try:
        img = load_image(image_path)
        if img is None:
            return image_path
        
        # Convert to grayscale
        gray = convert_to_grayscale(img)
        
        if not is_sketch:
            # PHOTO PREPROCESSING: Convert to sketch-like representation
            print("  [STEP 2] Photo -> Edge extraction (sketch-like)")
            
            # 1. Reduce noise while preserving edges
            gray = apply_bilateral_filter(gray, 9, 75, 75)
            
            # 2. Extract edges using Canny
            edges = apply_canny_edge_detection(gray, 30, 100)
            
            # 3. Invert edges (white background, black lines like sketch)
            edges = cv2.bitwise_not(edges)
            
            # 4. Blend edges with original for structure preservation
            # 50% edges + 50% original
            result = cv2.addWeighted(gray, 0.5, edges, 0.5, 0)
            
        else:
            # SKETCH PREPROCESSING: Minimal enhancement
            print("  [STEP 2] Sketch -> Minimal enhancement")
            
            # Just apply histogram equalization for consistent brightness
            result = apply_histogram_equalization(gray)
        
        # Convert back to BGR for DeepFace compatibility
        result_bgr = convert_to_bgr(result)
        
        # Save to temp_uploads folder with unique filename
        file_hash = uuid.uuid4().hex[:8]
        mode = "sketch" if is_sketch else "photo"
        processed_path = generate_temp_filepath(prefix=f'edge_{mode}_{file_hash}')
        cv2.imwrite(processed_path, result_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        return processed_path
        
    except Exception as e:
        print(f"Edge preprocessing error: {e}")
        return image_path


def preprocess_for_cross_domain_matching(image_path: str, is_sketch: bool = False, 
                                         canny_threshold: tuple = None) -> str:
    """
    EDGE-BASED: Preprocessing to reduce sketch-to-photo domain gap
    
    **USAGE:** Production endpoints (/api/compare, /api/criminals/search)
    **CALLED BY:** forensic_face_comparison()
    
    APPROACH:
    - For PHOTOS: Convert to grayscale -> Apply Canny edge detection -> Create sketch-like representation
    - For SKETCHES: Convert to grayscale only -> Keep sketch intact (no edge detection)
    - Both: Convert to 3-channel BGR -> Resize to 112x112 (ArcFace native size)
    
    This approach converts photos into edge-based representations to match sketches,
    while keeping original sketches intact, reducing the domain gap.
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
        canny_threshold: Tuple of (threshold1, threshold2) for Canny edge detection
                        If None, uses default (50, 150)
    
    Returns:
        str: Path to preprocessed image file, or None if failed
    
    DETERMINISTIC: All operations use fixed parameters for consistent results
    """
    try:
        img = load_image(image_path)
        if img is None:
            print(f"  [ERROR] Failed to read image: {image_path}")
            return None
        
        # Use default thresholds if not specified
        if canny_threshold is None:
            canny_threshold = (50, 150)
        
        print(f"  [PREPROCESSING] {'Sketch' if is_sketch else 'Photo'} - Input size: {img.shape}")
        
        # STEP 1: Convert to grayscale
        gray = convert_to_grayscale(img)
        print(f"    [OK] Step 1: Converted to grayscale")
        
        if is_sketch:
            # SKETCH: Normalize contrast + smooth to reduce noise, keep lines intact
            print(f"    [OK] Step 2: Sketch — contrast normalization + smoothing")
            # CLAHE for adaptive contrast normalization
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            processed = clahe.apply(gray)
            # Gentle Gaussian blur to reduce scan/compression noise
            processed = cv2.GaussianBlur(processed, (3, 3), 0)
        else:
            # PHOTO: Apply Canny edge detection to create sketch-like representation
            edges = apply_canny_edge_detection(gray, canny_threshold[0], canny_threshold[1])
            print(f"    [OK] Step 2: Photo - applied Canny edge detection with thresholds {canny_threshold}")
            processed = edges
        
        # STEP 3: Convert to 3-channel BGR (ArcFace expects 3 channels)
        bgr = convert_to_bgr(processed)
        print(f"    [OK] Step 3: Converted to 3-channel BGR")
        
        # STEP 4: Resize to 112x112 (ArcFace native size)
        target_size = 112
        resized = resize_to_arcface_size(bgr, target_size)
        print(f"    [OK] Step 4: Resized to {target_size}x{target_size} (ArcFace native size)")
        print(f"    [OK] Final output: {'Sketch (intact)' if is_sketch else 'Edge-based'} representation, size {resized.shape} (ready for ArcFace)")
        
        # Save preprocessed image to temp_uploads folder
        file_hash = uuid.uuid4().hex[:8]
        mode = "sketch" if is_sketch else "photo"
        threshold_str = f"{canny_threshold[0]}_{canny_threshold[1]}"
        processed_path = generate_temp_filepath(prefix=f'edge_preprocessed_{mode}_{threshold_str}_{file_hash}')
        
        # Save and validate
        if not save_image(resized, processed_path, quality=95):
            return None
        
        print(f"  [PREPROCESSING] Complete - saved to: {processed_path}")
        return processed_path
        
    except Exception as e:
        print(f"  [PREPROCESSING ERROR] {e}")
        traceback.print_exc()
        return None


def preprocess_with_adaptive_canny(image_path: str, is_sketch: bool = False, 
                                   reference_embedding: np.ndarray = None) -> tuple:
    """
    ADAPTIVE: Test multiple Canny thresholds and select the best one
    
    **USAGE:** Production endpoints when adaptive threshold selection is needed
    **OPTIMIZED:** Extracts embeddings directly from numpy arrays (no disk I/O)
    
    Tests multiple Canny threshold combinations:
    - (30, 120) - More edges (sensitive)
    - (50, 150) - Balanced (default)
    - (70, 200) - Fewer edges (conservative)
    
    If reference_embedding is provided, selects the threshold that produces
    the highest embedding similarity. Otherwise, returns default (50, 150).
    
    Args:
        image_path: Path to image file
        is_sketch: True if image is a sketch, False if photo
        reference_embedding: Reference embedding to compare against (optional)
    
    Returns:
        tuple: (best_preprocessed_path, best_threshold, threshold_results)
    """
    # Threshold combinations to test
    threshold_combinations = [
        (30, 120),  # More edges (sensitive)
        (50, 150),  # Balanced (default)
        (70, 200)   # Fewer edges (conservative)
    ]
    
    print(f"\n[ADAPTIVE CANNY] Testing {len(threshold_combinations)} threshold combinations...")
    
    # If no reference embedding, just use default
    if reference_embedding is None or is_sketch:
        print(f"  No reference embedding or is sketch - using default (50, 150)")
        best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
        return best_path, (50, 150), None
    
    threshold_results = []
    best_processed_img = None
    
    try:
        # Load image once
        img = load_image(image_path)
        if img is None:
            print(f"  [ERROR] Failed to load image: {image_path}")
            best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
            return best_path, (50, 150), None
        
        # Convert to grayscale once
        gray = convert_to_grayscale(img)
        
        # Test each threshold combination
        for threshold in threshold_combinations:
            print(f"\n  Testing threshold {threshold}...")
            
            try:
                # Apply Canny edge detection with this threshold
                edges = apply_canny_edge_detection(gray, threshold[0], threshold[1])
                
                # Convert to 3-channel BGR
                bgr = convert_to_bgr(edges)
                
                # Resize to InsightFace input size (112x112)
                target_size = 112
                resized = resize_to_arcface_size(bgr, target_size)

                # Extract embedding using InsightFace
                from models.insightface_model import (
                    extract_insightface_embedding,
                    is_insightface_initialized,
                )
                if not is_insightface_initialized():
                    raise RuntimeError("InsightFace not initialized")
                embedding = extract_insightface_embedding(resized)
                
                # Compute similarity with reference embedding using stable cosine similarity
                similarity = cosine_similarity(embedding, reference_embedding)
                
                threshold_results.append({
                    'threshold': threshold,
                    'similarity': float(similarity),
                    'processed_img': resized  # Store numpy array instead of path
                })
                
                print(f"    Similarity: {similarity:.4f} ({similarity*100:.1f}%)")
                
            except Exception as e:
                print(f"    [ERROR] Threshold {threshold} failed: {e}")
                continue
        
        # Select best threshold based on highest similarity
        if len(threshold_results) > 0:
            best_result = max(threshold_results, key=lambda x: x['similarity'])
            best_threshold = best_result['threshold']
            best_processed_img = best_result['processed_img']
            best_similarity = best_result['similarity']
            
            print(f"\n  [BEST THRESHOLD] {best_threshold} with similarity {best_similarity:.4f} ({best_similarity*100:.1f}%)")
            
            # Save only the best preprocessed image to disk
            file_hash = uuid.uuid4().hex[:8]
            mode = "photo"  # Only photos use adaptive Canny
            threshold_str = f"{best_threshold[0]}_{best_threshold[1]}"
            best_path = generate_temp_filepath(prefix=f'edge_adaptive_{mode}_{threshold_str}_{file_hash}')
            
            if not save_image(best_processed_img, best_path, quality=95):
                print(f"  [ERROR] Failed to save best preprocessed image")
                best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
                return best_path, (50, 150), None
            
            print(f"  [SAVED] Best preprocessed image: {best_path}")
            
            return best_path, best_threshold, threshold_results
        else:
            print(f"  [ERROR] All thresholds failed, using default")
            best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
            return best_path, (50, 150), None
            
    except Exception as e:
        print(f"  [ADAPTIVE CANNY ERROR] {e}")
        traceback.print_exc()
        
        # Fallback to default
        best_path = preprocess_for_cross_domain_matching(image_path, is_sketch, (50, 150))
        return best_path, (50, 150), None
