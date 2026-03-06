"""
Service for comparing faces and calculating similarity
Handles dual embedding comparison, fusion scoring, geometric similarity, and hybrid scoring
"""
import os
import cv2
import numpy as np
import uuid
import time
import traceback

# Import from sibling modules
from services.embedding_service import (
    initialize_models,
    extract_dual_embeddings,
    extract_embedding_with_tta
)
from preprocessing.sketch_photo_preprocess import is_sketch_image
from utils.file_utils import get_file_hash
from utils.similarity_utils import cosine_similarity
from utils.cache_utils import get_cached_result, set_cached_result


def extract_facial_regions(aligned_face: np.ndarray) -> dict:
    """
    Extract facial regions from aligned face for region-based embedding extraction.
    
    Regions extracted:
    - Full face (entire aligned face)
    - Eyes region (upper 40% of face, centered)
    - Nose region (middle 30% of face, centered)
    - Mouth region (lower 30% of face, centered)
    
    Args:
        aligned_face: Aligned face image (numpy array)
    
    Returns:
        dict: {
            'full_face': np.ndarray,
            'eyes': np.ndarray,
            'nose': np.ndarray,
            'mouth': np.ndarray,
            'success': bool
        }
    """
    try:
        h, w = aligned_face.shape[:2]
        
        # Full face (entire image)
        full_face = aligned_face.copy()
        
        # Eyes region: top 40% of face, centered horizontally
        eyes_top = 0
        eyes_bottom = int(h * 0.40)
        eyes_left = int(w * 0.15)
        eyes_right = int(w * 0.85)
        eyes_region = aligned_face[eyes_top:eyes_bottom, eyes_left:eyes_right]
        
        # Nose region: middle 30% vertically, centered horizontally
        nose_top = int(h * 0.35)
        nose_bottom = int(h * 0.65)
        nose_left = int(w * 0.30)
        nose_right = int(w * 0.70)
        nose_region = aligned_face[nose_top:nose_bottom, nose_left:nose_right]
        
        # Mouth region: bottom 30% of face, centered horizontally
        mouth_top = int(h * 0.60)
        mouth_bottom = h
        mouth_left = int(w * 0.25)
        mouth_right = int(w * 0.75)
        mouth_region = aligned_face[mouth_top:mouth_bottom, mouth_left:mouth_right]
        
        return {
            'full_face': full_face,
            'eyes': eyes_region,
            'nose': nose_region,
            'mouth': mouth_region,
            'success': True
        }
        
    except Exception as e:
        print(f"[WARNING] Failed to extract facial regions: {e}")
        return {
            'full_face': aligned_face,
            'eyes': None,
            'nose': None,
            'mouth': None,
            'success': False
        }


def extract_region_embeddings(aligned_face: np.ndarray, is_sketch: bool = False) -> dict:
    """
    Extract ArcFace embeddings from multiple facial regions for enhanced matching.
    Uses Test-Time Augmentation (TTA) for robust embedding extraction.
    
    Extracts embeddings from:
    - Full face
    - Eyes region
    - Nose region
    - Mouth region
    
    Args:
        aligned_face: Aligned face image (numpy array)
        is_sketch: True if image is a sketch, False if photo
    
    Returns:
        dict: {
            'full_face': np.ndarray (512-D, L2 normalized),
            'eyes': np.ndarray (512-D, L2 normalized) or None,
            'nose': np.ndarray (512-D, L2 normalized) or None,
            'mouth': np.ndarray (512-D, L2 normalized) or None,
            'success': bool
        }
    """
    try:
        # Extract facial regions
        regions = extract_facial_regions(aligned_face)
        
        if not regions['success']:
            print(f"  [WARNING] Region extraction failed, using full face only")
        
        region_embeddings = {}
        
        # Process each region
        for region_name in ['full_face', 'eyes', 'nose', 'mouth']:
            region_img = regions.get(region_name)
            
            if region_img is None or region_img.size == 0:
                region_embeddings[region_name] = None
                continue
            
            try:
                # Apply edge detection if photo (same as main pipeline)
                if not is_sketch:
                    # Convert to grayscale
                    if len(region_img.shape) == 3:
                        gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = region_img
                    
                    # Apply Canny edge detection
                    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
                    processed_region = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
                else:
                    # Sketch - keep as is
                    if len(region_img.shape) == 3:
                        gray = cv2.cvtColor(region_img, cv2.COLOR_BGR2GRAY)
                    else:
                        gray = region_img
                    processed_region = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                
                # Extract embedding with TTA (same as main pipeline)
                embedding = extract_embedding_with_tta(
                    processed_region, 
                    'ArcFace'
                )
                
                region_embeddings[region_name] = embedding
                    
            except Exception as e:
                print(f"  [WARNING] Failed to extract {region_name} embedding with TTA: {e}")
                region_embeddings[region_name] = None
        
        # Check if at least full face succeeded
        success = region_embeddings.get('full_face') is not None
        
        return {
            'full_face': region_embeddings.get('full_face'),
            'eyes': region_embeddings.get('eyes'),
            'nose': region_embeddings.get('nose'),
            'mouth': region_embeddings.get('mouth'),
            'success': success
        }
        
    except Exception as e:
        print(f"[ERROR] Region embedding extraction failed: {e}")
        traceback.print_exc()
        return {
            'full_face': None,
            'eyes': None,
            'nose': None,
            'mouth': None,
            'success': False
        }


def compute_multi_region_similarity(regions1: dict, regions2: dict) -> dict:
    """
    Compute similarity scores for multiple facial regions and combine them.
    
    Weighted fusion:
    - Full face: 55%
    - Eyes: 20%
    - Nose: 15%
    - Mouth: 10%
    
    Args:
        regions1: Region embeddings from image 1
        regions2: Region embeddings from image 2
    
    Returns:
        dict: {
            'full_face_similarity': float,
            'eyes_similarity': float,
            'nose_similarity': float,
            'mouth_similarity': float,
            'combined_similarity': float,
            'regions_used': list
        }
    """
    try:
        similarities = {}
        regions_used = []
        
        # Compute similarity for each region
        for region_name in ['full_face', 'eyes', 'nose', 'mouth']:
            emb1 = regions1.get(region_name)
            emb2 = regions2.get(region_name)
            
            if emb1 is not None and emb2 is not None:
                sim = cosine_similarity(emb1, emb2)
                similarities[region_name] = sim
                regions_used.append(region_name)
            else:
                similarities[region_name] = None
        
        # Weighted fusion (fallback to full face if regions missing)
        if similarities['full_face'] is not None:
            # Define weights
            weights = {
                'full_face': 0.55,
                'eyes': 0.20,
                'nose': 0.15,
                'mouth': 0.10
            }
            
            # Compute weighted average (redistribute weights if regions missing)
            total_weight = 0.0
            weighted_sum = 0.0
            
            for region_name, weight in weights.items():
                if similarities[region_name] is not None:
                    weighted_sum += weight * similarities[region_name]
                    total_weight += weight
            
            # Normalize by actual total weight
            if total_weight > 0:
                combined_similarity = weighted_sum / total_weight
            else:
                combined_similarity = 0.0
        else:
            combined_similarity = 0.0
        
        return {
            'full_face_similarity': similarities.get('full_face', 0.0),
            'eyes_similarity': similarities.get('eyes'),
            'nose_similarity': similarities.get('nose'),
            'mouth_similarity': similarities.get('mouth'),
            'combined_similarity': combined_similarity,
            'regions_used': regions_used
        }
        
    except Exception as e:
        print(f"[ERROR] Multi-region similarity computation failed: {e}")
        return {
            'full_face_similarity': 0.0,
            'eyes_similarity': None,
            'nose_similarity': None,
            'mouth_similarity': None,
            'combined_similarity': 0.0,
            'regions_used': []
        }


def compute_geometric_similarity(img1_path: str, img2_path: str) -> float:
    """
    Lightweight geometric scoring based on facial landmarks
    
    LEGACY: This function re-detects faces from original images.
    Use compute_geometric_similarity_from_aligned() for consistency with embeddings.
    
    Returns:
        float: Geometric similarity score (0-1)
    """
    try:
        # Read images
        img1 = cv2.imread(img1_path)
        img2 = cv2.imread(img2_path)
        
        if img1 is None or img2 is None:
            return 0.5  # Neutral score if can't read
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Detect faces using Haar Cascade (lightweight)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        faces1 = face_cascade.detectMultiScale(gray1, 1.1, 4)
        faces2 = face_cascade.detectMultiScale(gray2, 1.1, 4)
        
        if len(faces1) == 0 or len(faces2) == 0:
            return 0.5  # Neutral score if no face detected
        
        # Get largest face (assume it's the main face)
        face1 = max(faces1, key=lambda f: f[2] * f[3])  # (x, y, w, h)
        face2 = max(faces2, key=lambda f: f[2] * f[3])
        
        # Extract face regions
        x1, y1, w1, h1 = face1
        x2, y2, w2, h2 = face2
        
        # Compute aspect ratio similarity
        aspect1 = w1 / h1 if h1 > 0 else 1.0
        aspect2 = w2 / h2 if h2 > 0 else 1.0
        aspect_similarity = 1.0 - abs(aspect1 - aspect2) / max(aspect1, aspect2)
        
        # Compute size similarity (normalized)
        size1 = w1 * h1
        size2 = w2 * h2
        size_similarity = min(size1, size2) / max(size1, size2) if max(size1, size2) > 0 else 0.5
        
        # Compute position similarity (center of face)
        center1_x = x1 + w1 / 2
        center1_y = y1 + h1 / 2
        center2_x = x2 + w2 / 2
        center2_y = y2 + h2 / 2
        
        # Normalize by image size
        h_img1, w_img1 = gray1.shape
        h_img2, w_img2 = gray2.shape
        
        center1_x_norm = center1_x / w_img1 if w_img1 > 0 else 0.5
        center1_y_norm = center1_y / h_img1 if h_img1 > 0 else 0.5
        center2_x_norm = center2_x / w_img2 if w_img2 > 0 else 0.5
        center2_y_norm = center2_y / h_img2 if h_img2 > 0 else 0.5
        
        position_similarity = 1.0 - (abs(center1_x_norm - center2_x_norm) + abs(center1_y_norm - center2_y_norm)) / 2.0
        
        # Weighted combination
        geometric_score = (
            0.4 * aspect_similarity +
            0.3 * size_similarity +
            0.3 * position_similarity
        )
        
        return max(0.0, min(1.0, geometric_score))
        
    except Exception as e:
        print(f"[WARNING] Geometric scoring failed: {e}")
        return 0.5  # Neutral score on error


def compute_geometric_similarity_from_aligned(aligned_face1: np.ndarray, aligned_face2: np.ndarray) -> float:
    """
    Compute geometric similarity from already-aligned face images
    
    This ensures consistency with embedding extraction which uses aligned faces.
    Uses the SAME aligned faces that were used for embedding extraction.
    
    Args:
        aligned_face1: Aligned face image 1 (numpy array)
        aligned_face2: Aligned face image 2 (numpy array)
    
    Returns:
        float: Geometric similarity score (0-1)
    """
    try:
        if aligned_face1 is None or aligned_face2 is None:
            return 0.5  # Neutral score if invalid input
        
        # Convert to grayscale if needed
        if len(aligned_face1.shape) == 3:
            gray1 = cv2.cvtColor(aligned_face1, cv2.COLOR_BGR2GRAY)
        else:
            gray1 = aligned_face1
            
        if len(aligned_face2.shape) == 3:
            gray2 = cv2.cvtColor(aligned_face2, cv2.COLOR_BGR2GRAY)
        else:
            gray2 = aligned_face2
        
        # Since faces are already aligned and cropped, we can use the entire image
        h1, w1 = gray1.shape
        h2, w2 = gray2.shape
        
        # Compute aspect ratio similarity
        aspect1 = w1 / h1 if h1 > 0 else 1.0
        aspect2 = w2 / h2 if h2 > 0 else 1.0
        aspect_similarity = 1.0 - abs(aspect1 - aspect2) / max(aspect1, aspect2)
        
        # Compute size similarity (normalized)
        size1 = w1 * h1
        size2 = w2 * h2
        size_similarity = min(size1, size2) / max(size1, size2) if max(size1, size2) > 0 else 0.5
        
        # For aligned faces, position is already normalized (face is centered)
        # So we give high position similarity
        position_similarity = 0.95
        
        # Compute histogram similarity for texture/structure comparison
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        
        # Normalize histograms
        cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        
        # Compare histograms using correlation
        hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        hist_similarity = max(0.0, hist_similarity)  # Clamp to [0, 1]
        
        # Weighted combination (emphasize histogram for aligned faces)
        geometric_score = (
            0.25 * aspect_similarity +
            0.20 * size_similarity +
            0.15 * position_similarity +
            0.40 * hist_similarity
        )
        
        return max(0.0, min(1.0, geometric_score))
        
    except Exception as e:
        print(f"[WARNING] Geometric scoring from aligned faces failed: {e}")
        traceback.print_exc()
        return 0.5  # Neutral score on error



def forensic_face_comparison(sketch_path: str, photo_path: str, use_cache: bool = True) -> dict:
    """
    HYBRID: Forensic-grade face comparison with hybrid scoring
    
    **USAGE:** Production endpoints (/api/compare, /api/criminals/search)
    **PREPROCESSING:** Detect face first, then apply edge detection to aligned face
    
    HYBRID SCORING:
    - 85% Final embedding (70% fusion + 30% multi-region)
    - 15% Geometric similarity
    - Fusion: 50% ArcFace + 50% Facenet
    - Multi-region: 55% full + 20% eyes + 15% nose + 10% mouth
    
    Args:
        sketch_path: Path to sketch/query image
        photo_path: Path to photo/reference image
        use_cache: Whether to use result caching
    
    Returns:
        dict: Comprehensive comparison results with all similarity scores
    
    DETERMINISTIC: All operations use fixed parameters for consistent results
    """
    # Ensure models are initialized
    initialize_models()
    
    start_time = time.time()
    print(f"\n{'='*60}")
    print("FORENSIC FACE COMPARISON - HYBRID SCORING")
    print(f"{'='*60}")
    print(f"  Query Image: {os.path.basename(sketch_path)}")
    print(f"  Reference Image: {os.path.basename(photo_path)}")
    
    # Detect if images are sketches
    is_img1_sketch = is_sketch_image(sketch_path)
    is_img2_sketch = is_sketch_image(photo_path)
    
    print(f"  Query is sketch: {is_img1_sketch}")
    print(f"  Reference is sketch: {is_img2_sketch}")
    
    # Determine comparison type
    is_cross_domain = is_img1_sketch != is_img2_sketch
    comparison_type = "cross-domain (sketch-to-photo)" if is_cross_domain else "same-domain"
    print(f"  Comparison type: {comparison_type}")
    
    # Check result cache
    cache_key = None
    if use_cache:
        hash1 = get_file_hash(sketch_path)
        hash2 = get_file_hash(photo_path)
        if hash1 and hash2:
            cache_key = f"{hash1}_{hash2}_{is_img1_sketch}_{is_img2_sketch}_hybrid_v1"
            cached_result = get_cached_result(cache_key)
            if cached_result:
                cached_result = cached_result.copy()
                cached_result['from_cache'] = True
                cached_result['processing_time'] = round(time.time() - start_time, 3)
                print(f"[CACHE] Result retrieved from cache")
                print(f"{'='*60}\n")
                return cached_result
    
    try:
        # Extract DUAL embeddings (ArcFace + Facenet) using align-then-edge approach
        print(f"[DUAL EMBEDDING EXTRACTION] Extracting dual embeddings (ArcFace + Facenet)...")
        
        # Extract dual embeddings for image 1 (query) - no adaptive Canny yet
        print(f"\n  Extracting dual embeddings 1 (query)...")
        embeddings1 = extract_dual_embeddings(sketch_path, is_sketch=is_img1_sketch, use_adaptive_canny=False)
        
        if embeddings1 is None or not embeddings1['success']:
            return {
                'distance': 1.0,
                'similarity': 0.0,
                'embedding_similarity': 0.0,
                'arcface_similarity': 0.0,
                'facenet_similarity': 0.0,
                'geometric_similarity': 0.0,
                'similarity_category': 'ERROR',
                'confidence_level': 'error',
                'confidence_score': 0.0,
                'match_quality': 'Failed to extract dual embeddings from image 1',
                'is_cross_domain': is_cross_domain,
                'comparison_type': 'error',
                'model_used': 'failed',
                'metric_used': 'none',
                'processing_time': round(time.time() - start_time, 3),
                'error': 'Failed to extract dual embeddings from image 1',
                'from_cache': False,
                'forensic_note': 'Dual embedding extraction failed for image 1.'
            }
        
        # Extract dual embeddings for image 2 (reference)
        # Use adaptive Canny if it's a photo and we're doing cross-domain comparison
        print(f"\n  Extracting dual embeddings 2 (reference)...")
        use_adaptive = is_cross_domain and not is_img2_sketch  # Only for photos in cross-domain
        reference_emb = embeddings1['arcface'] if use_adaptive else None
        
        embeddings2 = extract_dual_embeddings(
            photo_path, 
            is_sketch=is_img2_sketch,
            use_adaptive_canny=use_adaptive,
            reference_embedding=reference_emb
        )
        
        if embeddings2 is None or not embeddings2['success']:
            return {
                'distance': 1.0,
                'similarity': 0.0,
                'embedding_similarity': 0.0,
                'arcface_similarity': 0.0,
                'facenet_similarity': 0.0,
                'geometric_similarity': 0.0,
                'similarity_category': 'ERROR',
                'confidence_level': 'error',
                'confidence_score': 0.0,
                'match_quality': 'Failed to extract dual embeddings from image 2',
                'is_cross_domain': is_cross_domain,
                'comparison_type': 'error',
                'model_used': 'failed',
                'metric_used': 'none',
                'processing_time': round(time.time() - start_time, 3),
                'error': 'Failed to extract dual embeddings from image 2',
                'from_cache': False,
                'forensic_note': 'Dual embedding extraction failed for image 2.'
            }
        
        # Log embedding details
        print(f"\n[DUAL EMBEDDING DETAILS]")
        print(f"  ArcFace embedding 1 length: {len(embeddings1['arcface'])}")
        print(f"  ArcFace embedding 2 length: {len(embeddings2['arcface'])}")
        print(f"  Facenet embedding 1 length: {len(embeddings1['facenet'])}")
        print(f"  Facenet embedding 2 length: {len(embeddings2['facenet'])}")
        print(f"  All embeddings are L2 normalized")
        
        # Compute similarity for both models using dot product (embeddings are L2 normalized)
        print(f"\n[DUAL EMBEDDING SIMILARITY]")
        
        # ArcFace similarity using stable cosine similarity
        arcface_similarity = cosine_similarity(embeddings1['arcface'], embeddings2['arcface'])
        print(f"  ArcFace similarity: {arcface_similarity:.6f} ({arcface_similarity*100:.2f}%)")
        
        # Facenet similarity using stable cosine similarity
        facenet_similarity = cosine_similarity(embeddings1['facenet'], embeddings2['facenet'])
        print(f"  Facenet similarity: {facenet_similarity:.6f} ({facenet_similarity*100:.2f}%)")
        
        # Fuse the scores: 50% ArcFace + 50% Facenet
        embedding_fusion = 0.5 * arcface_similarity + 0.5 * facenet_similarity
        print(f"\n[EMBEDDING FUSION]")
        print(f"  ArcFace weight: 50%")
        print(f"  Facenet weight: 50%")
        print(f"  Fused embedding similarity: {embedding_fusion:.6f} ({embedding_fusion*100:.2f}%)")
        
        # Multi-region similarity (ArcFace only, for enhanced matching)
        print(f"\n[MULTI-REGION SIMILARITY]")
        print(f"  Extracting region embeddings for enhanced matching...")
        
        try:
            regions1 = extract_region_embeddings(embeddings1['aligned_face'], is_sketch=is_img1_sketch)
            regions2 = extract_region_embeddings(embeddings2['aligned_face'], is_sketch=is_img2_sketch)
            
            if regions1['success'] and regions2['success']:
                region_results = compute_multi_region_similarity(regions1, regions2)
                
                print(f"  Regions used: {', '.join(region_results['regions_used'])}")
                if region_results['full_face_similarity'] is not None:
                    print(f"  Full face: {region_results['full_face_similarity']:.6f} ({region_results['full_face_similarity']*100:.2f}%)")
                if region_results['eyes_similarity'] is not None:
                    print(f"  Eyes: {region_results['eyes_similarity']:.6f} ({region_results['eyes_similarity']*100:.2f}%)")
                if region_results['nose_similarity'] is not None:
                    print(f"  Nose: {region_results['nose_similarity']:.6f} ({region_results['nose_similarity']*100:.2f}%)")
                if region_results['mouth_similarity'] is not None:
                    print(f"  Mouth: {region_results['mouth_similarity']:.6f} ({region_results['mouth_similarity']*100:.2f}%)")
                print(f"  Combined region similarity: {region_results['combined_similarity']:.6f} ({region_results['combined_similarity']*100:.2f}%)")
                
                # Use region-based similarity as an additional component
                multi_region_similarity = region_results['combined_similarity']
            else:
                print(f"  [WARNING] Region extraction failed, using full face embedding only")
                multi_region_similarity = embedding_fusion  # Fallback to combined embedding
                region_results = None
        except Exception as e:
            print(f"  [ERROR] Multi-region similarity failed: {e}")
            multi_region_similarity = embedding_fusion  # Fallback to combined embedding
            region_results = None
        
        # Compute geometric similarity using aligned faces (same faces used for embeddings)
        print(f"\n[GEOMETRIC SIMILARITY]")
        geometric_similarity = compute_geometric_similarity_from_aligned(
            embeddings1['aligned_face'], 
            embeddings2['aligned_face']
        )
        print(f"  Geometric similarity: {geometric_similarity:.6f} ({geometric_similarity*100:.2f}%)")
        print(f"  Note: Using aligned faces (consistent with embedding extraction)")
        
        # Final hybrid score with multi-region integration
        # Step 1: Combine embedding fusion with multi-region similarity
        # Step 2: Combine with geometric similarity
        print(f"\n[FINAL HYBRID SCORING]")
        print(f"  Step 1: Combine embedding fusion with multi-region similarity")
        print(f"    Embedding fusion: {embedding_fusion:.6f} ({embedding_fusion*100:.2f}%)")
        print(f"    Multi-region similarity: {multi_region_similarity:.6f} ({multi_region_similarity*100:.2f}%)")
        
        final_embedding = 0.7 * embedding_fusion + 0.3 * multi_region_similarity
        print(f"    Final embedding = 0.7 * embedding_fusion + 0.3 * multi_region")
        print(f"    Final embedding: {final_embedding:.6f} ({final_embedding*100:.2f}%)")
        
        print(f"\n  Step 2: Combine final embedding with geometric similarity")
        print(f"    Final embedding: {final_embedding:.6f} ({final_embedding*100:.2f}%)")
        print(f"    Geometric similarity: {geometric_similarity:.6f} ({geometric_similarity*100:.2f}%)")
        
        hybrid_similarity = 0.85 * final_embedding + 0.15 * geometric_similarity
        hybrid_distance = 1.0 - hybrid_similarity
        
        print(f"    Final similarity = 0.85 * final_embedding + 0.15 * geometric")
        print(f"    Final hybrid similarity: {hybrid_similarity:.6f} ({hybrid_similarity*100:.2f}%)")
        print(f"    Final hybrid distance: {hybrid_distance:.6f}")
        
        print(f"\n  [SCORING BREAKDOWN]")
        print(f"    Embedding fusion weight in final: 70% * 85% = 59.5%")
        print(f"    Multi-region weight in final: 30% * 85% = 25.5%")
        print(f"    Geometric weight in final: 15%")
        print(f"    Total: 100%")
        
        # Determine similarity category based on hybrid similarity
        print(f"\n[ANALYSIS]")
        print(f"  Comparison type: {comparison_type}")
        print(f"  Final hybrid similarity: {hybrid_similarity:.6f} ({hybrid_similarity*100:.2f}%)")
        
        if is_cross_domain:
            # Cross-domain (sketch-to-photo) thresholds
            # Adjusted for realistic sketch-to-photo matching (lower similarities expected)
            if hybrid_similarity > 0.55:
                similarity_category = 'VERY_STRONG'
                confidence_level = 'very_strong_match'
                confidence_score = 90.0
                match_quality = 'Very Strong Match - High priority for investigation'
            elif hybrid_similarity > 0.45:
                similarity_category = 'STRONG'
                confidence_level = 'strong_match'
                confidence_score = 75.0
                match_quality = 'Strong Match - Recommended for investigation'
            elif hybrid_similarity > 0.35:
                similarity_category = 'POSSIBLE'
                confidence_level = 'possible_match'
                confidence_score = 55.0
                match_quality = 'Possible Match - Consider for investigation'
            else:
                similarity_category = 'LOW'
                confidence_level = 'low_similarity'
                confidence_score = 30.0
                match_quality = 'Low Similarity - Unlikely match'
        else:
            # Same-domain (photo-to-photo) thresholds
            if hybrid_similarity > 0.70:
                similarity_category = 'HIGH'
                confidence_level = 'high_similarity'
                confidence_score = 95.0
                match_quality = 'High Similarity - Strong match'
            elif hybrid_similarity >= 0.60:
                similarity_category = 'MEDIUM'
                confidence_level = 'medium_similarity'
                confidence_score = 80.0
                match_quality = 'Medium Similarity - Good match'
            else:
                similarity_category = 'LOW'
                confidence_level = 'low_similarity'
                confidence_score = 50.0
                match_quality = 'Low Similarity - Weak match'
        
        elapsed_time = time.time() - start_time
        
        print(f"\n[RESULTS]")
        print(f"  ArcFace similarity: {arcface_similarity:.4f} ({arcface_similarity*100:.1f}%)")
        print(f"  Facenet similarity: {facenet_similarity:.4f} ({facenet_similarity*100:.1f}%)")
        print(f"  Embedding fusion similarity: {embedding_fusion:.4f} ({embedding_fusion*100:.1f}%)")
        print(f"  Multi-region similarity: {multi_region_similarity:.4f} ({multi_region_similarity*100:.1f}%)")
        print(f"  Final embedding similarity: {final_embedding:.4f} ({final_embedding*100:.1f}%)")
        print(f"  Geometric similarity: {geometric_similarity:.4f} ({geometric_similarity*100:.1f}%)")
        print(f"  Hybrid similarity: {hybrid_similarity:.4f} ({hybrid_similarity*100:.1f}%)")
        print(f"  Hybrid distance: {hybrid_distance:.4f}")
        print(f"  Similarity category: {similarity_category}")
        print(f"  Confidence level: {confidence_level}")
        print(f"  Confidence score: {confidence_score:.1f}%")
        print(f"  Match quality: {match_quality}")
        print(f"  Processing time: {elapsed_time:.3f}s")
        print(f"{'='*60}\n")
        
        # ================================================================
        # SCORE NORMALIZATION FOR UI PRESENTATION
        # ================================================================
        # Apply presentation-level normalization to make scores more interpretable
        # for sketch-to-photo matching where raw cosine similarities are typically low
        # 
        # Formula: display_similarity = min(95, max(5, raw_similarity * 250))
        # 
        # This transformation:
        # - Maps raw similarity [0, 1] to display range [5, 95]
        # - Amplifies low similarities for better UI presentation
        # - Maintains relative ordering for ranking
        # 
        # Both raw and display values are returned:
        # - raw_similarity: Used for internal ranking and forensic calculations
        # - display_similarity: Used for frontend visualization only
        
        print(f"[SCORE NORMALIZATION FOR UI]")
        print(f"  Raw similarity: {hybrid_similarity:.4f}")
        print(f"  Transformation: display = min(95, max(5, raw * 250))")
        
        def normalize_for_display(raw_score):
            """Convert raw similarity to display percentage"""
            return min(95.0, max(5.0, raw_score * 250.0))
        
        # Apply display normalization to all similarity scores
        display_hybrid = normalize_for_display(hybrid_similarity)
        display_final_embedding = normalize_for_display(final_embedding)
        display_fusion = normalize_for_display(embedding_fusion)
        display_arcface = normalize_for_display(arcface_similarity)
        display_facenet = normalize_for_display(facenet_similarity)
        display_geometric = normalize_for_display(geometric_similarity)
        display_multi_region = normalize_for_display(multi_region_similarity)
        
        print(f"  Display similarity: {display_hybrid:.1f}%")
        print(f"  Note: Raw scores preserved for ranking, display scores for UI only")
        
        result_dict = {
            'distance': float(hybrid_distance),
            'raw_similarity': float(hybrid_similarity),  # Raw score for ranking and forensic calculations
            'display_similarity': float(display_hybrid),  # Display score for UI presentation (5-95 range)
            'similarity': float(display_hybrid),  # Alias for display_similarity (for backward compatibility)
            'final_embedding_similarity': float(display_final_embedding),  # Display: Final embedding (fusion + region)
            'embedding_fusion': float(display_fusion),  # Display: Fusion score
            'arcface_similarity': float(display_arcface),  # Display: ArcFace score
            'facenet_similarity': float(display_facenet),  # Display: Facenet score
            'geometric_similarity': float(display_geometric),  # Display: Geometric score
            'multi_region_similarity': float(display_multi_region),  # Display: Multi-region combined
            'raw_final_embedding_similarity': float(final_embedding),  # Raw final embedding
            'raw_embedding_fusion': float(embedding_fusion),  # Raw fusion score
            'raw_arcface_similarity': float(arcface_similarity),  # Raw ArcFace score
            'raw_facenet_similarity': float(facenet_similarity),  # Raw Facenet score
            'raw_geometric_similarity': float(geometric_similarity),  # Raw geometric score
            'raw_multi_region_similarity': float(multi_region_similarity),  # Raw multi-region score
            'similarity_category': similarity_category,
            'confidence_level': confidence_level,
            'confidence_score': float(confidence_score),
            'match_quality': match_quality,
            'is_cross_domain': bool(is_cross_domain),
            'comparison_type': comparison_type,
            'model_used': 'ArcFace + Facenet (Dual Fusion) + Multi-Region',
            'metric_used': 'hybrid: 85% final_embedding + 15% geometric | final_embedding: 70% fusion + 30% multi-region | fusion: 50% ArcFace + 50% Facenet | multi-region: 55% full + 20% eyes + 15% nose + 10% mouth',
            'scoring_formula': {
                'final_similarity': '0.85 * final_embedding + 0.15 * geometric',
                'final_embedding': '0.7 * embedding_fusion + 0.3 * multi_region',
                'embedding_fusion': '0.5 * arcface + 0.5 * facenet',
                'multi_region': '0.55 * full_face + 0.20 * eyes + 0.15 * nose + 0.10 * mouth',
                'effective_weights': {
                    'embedding_fusion': '59.5%',
                    'multi_region': '25.5%',
                    'geometric': '15.0%'
                }
            },
            'arcface_embedding_length': int(len(embeddings1['arcface'])),
            'facenet_embedding_length': int(len(embeddings1['facenet'])),
            'embeddings_normalized': True,
            'score_normalization': 'Presentation-level normalization: display = min(95, max(5, raw * 250)). Use raw_similarity for ranking, display_similarity for UI visualization.',
            'processing_time': round(elapsed_time, 3),
            'from_cache': False,
            'preprocessing_method': 'align-then-edge (face detected on original, edge applied to aligned face)',
            'forensic_note': 'Test-Time Augmentation (TTA) with 3 augmentations applied for robust embeddings. Final scoring: 59.5% embedding fusion + 25.5% multi-region + 15% geometric. Dual embedding fusion: 50% ArcFace + 50% Facenet. Multi-region embeddings: 55% full face + 20% eyes + 15% nose + 10% mouth. All embeddings L2 normalized. Investigation assistant - not identity confirmation.' if is_cross_domain else 'Test-Time Augmentation (TTA) with 3 augmentations applied. Final scoring with multi-region enhancement for higher reliability. All embeddings L2 normalized.'
        }
        
        # Add region-specific details if available
        if region_results is not None:
            result_dict['region_details'] = {
                'full_face': float(normalize_for_display(region_results['full_face_similarity'])) if region_results['full_face_similarity'] is not None else None,
                'eyes': float(normalize_for_display(region_results['eyes_similarity'])) if region_results['eyes_similarity'] is not None else None,
                'nose': float(normalize_for_display(region_results['nose_similarity'])) if region_results['nose_similarity'] is not None else None,
                'mouth': float(normalize_for_display(region_results['mouth_similarity'])) if region_results['mouth_similarity'] is not None else None,
                'regions_used': region_results['regions_used'],
                'raw_full_face': float(region_results['full_face_similarity']) if region_results['full_face_similarity'] is not None else None,
                'raw_eyes': float(region_results['eyes_similarity']) if region_results['eyes_similarity'] is not None else None,
                'raw_nose': float(region_results['nose_similarity']) if region_results['nose_similarity'] is not None else None,
                'raw_mouth': float(region_results['mouth_similarity']) if region_results['mouth_similarity'] is not None else None
            }
        
        # Cache the result
        if use_cache and cache_key:
            set_cached_result(cache_key, result_dict.copy())
        
        return result_dict
        
    except Exception as e:
        print(f"[ERROR] Comparison failed: {e}")
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        elapsed_time = time.time() - start_time
        return {
            'distance': 1.0,
            'similarity': 0.0,
            'embedding_similarity': 0.0,
            'geometric_similarity': 0.0,
            'similarity_category': 'ERROR',
            'confidence_level': 'error',
            'confidence_score': 0.0,
            'match_quality': 'Comparison failed',
            'is_cross_domain': False,
            'comparison_type': 'error',
            'model_used': 'failed',
            'metric_used': 'none',
            'embedding_length': 0,
            'embedding_norm_1': 0.0,
            'embedding_norm_2': 0.0,
            'processing_time': round(elapsed_time, 3),
            'error': str(e),
            'from_cache': False,
            'forensic_note': 'Comparison failed due to technical error.'
        }
