"""
FAISS Service Module
Handles FAISS indexing and fast similarity search for face embeddings
"""

import numpy as np
import faiss
import traceback
from typing import Dict, List, Tuple, Optional
from utils.similarity_utils import cosine_similarity


# ============================================================================
# GLOBAL VARIABLES
# ============================================================================

# Precomputed embeddings cache
EMBEDDING_CACHE = {}  # {criminal_id: {'arcface': vector, 'facenet': vector}}
EMBEDDING_VERSION = "dual_arcface_facenet_v2"  # v2: fixed Facenet512 input size 112→160

# FAISS index for fast similarity search
# FAISS (Facebook AI Similarity Search) provides efficient similarity search for high-dimensional vectors
# Using IndexFlatIP (Inner Product) for cosine similarity with L2-normalized embeddings
# This accelerates Stage 1 retrieval from O(N) to O(log N) for large databases
FAISS_INDEX_ARCFACE = None  # FAISS index for ArcFace embeddings (512-D)
FAISS_INDEX_FACENET = None  # FAISS index for Facenet embeddings (512-D)
FAISS_CRIMINAL_IDS = []  # Ordered list of criminal_ids corresponding to FAISS index positions

# FAISS index synchronization flag
# When True, indicates that embedding cache has changed and FAISS index needs rebuilding
FAISS_INDEX_DIRTY = True  # Start as dirty (no index built yet)


# ============================================================================
# EMBEDDING CACHE MANAGEMENT
# ============================================================================

def get_embedding_cache() -> dict:
    """Get the embedding cache dictionary"""
    return EMBEDDING_CACHE


def get_embedding_version() -> str:
    """Get the current embedding version"""
    return EMBEDDING_VERSION


def set_cached_embedding(criminal_id: str, arcface_embedding: np.ndarray, facenet_embedding: np.ndarray):
    """
    Store dual embeddings in cache for a criminal
    
    Automatically marks FAISS index as dirty when embeddings are added/updated.
    The index will be rebuilt before the next search operation.
    
    Args:
        criminal_id: Criminal ID
        arcface_embedding: ArcFace embedding vector (512-D)
        facenet_embedding: Facenet embedding vector (512-D)
    """
    global EMBEDDING_CACHE, FAISS_INDEX_DIRTY
    EMBEDDING_CACHE[criminal_id] = {
        'arcface': arcface_embedding,
        'facenet': facenet_embedding
    }
    # Mark FAISS index as dirty (needs rebuilding)
    FAISS_INDEX_DIRTY = True


def get_cached_embedding(criminal_id: str) -> Optional[dict]:
    """
    Retrieve cached dual embeddings for a criminal
    
    Args:
        criminal_id: Criminal ID
    
    Returns:
        dict: {'arcface': np.ndarray, 'facenet': np.ndarray} or None if not found
    """
    return EMBEDDING_CACHE.get(criminal_id)


def clear_embedding_cache():
    """
    Clear all cached embeddings
    
    Automatically marks FAISS index as dirty when cache is cleared.
    """
    global EMBEDDING_CACHE, FAISS_INDEX_DIRTY
    EMBEDDING_CACHE = {}
    # Mark FAISS index as dirty (needs rebuilding)
    FAISS_INDEX_DIRTY = True


def get_cache_size() -> int:
    """Get the number of cached embeddings"""
    return len(EMBEDDING_CACHE)


# ============================================================================
# FAISS INDEX BUILDING
# ============================================================================

def build_faiss_index():
    """
    Build FAISS index for fast similarity search using cached embeddings.
    Uses IndexFlatIP (Inner Product) for cosine similarity with normalized vectors.
    
    Automatically marks index as clean after successful build.
    """
    global FAISS_INDEX_ARCFACE, FAISS_INDEX_FACENET, FAISS_CRIMINAL_IDS, FAISS_INDEX_DIRTY
    
    print("\n" + "="*60)
    print("BUILDING FAISS INDEX FOR FAST RETRIEVAL")
    print("="*60)
    
    try:
        if len(EMBEDDING_CACHE) == 0:
            print("[WARNING] No embeddings in cache, skipping FAISS index build")
            FAISS_INDEX_DIRTY = False  # Mark as clean (nothing to index)
            return
        
        # Collect all embeddings and criminal IDs in consistent order
        criminal_ids = sorted(EMBEDDING_CACHE.keys())  # Sort for consistency
        arcface_embeddings = []
        facenet_embeddings = []
        
        for criminal_id in criminal_ids:
            embeddings = EMBEDDING_CACHE[criminal_id]
            arcface_embeddings.append(embeddings['arcface'])
            facenet_embeddings.append(embeddings['facenet'])
        
        # Convert to numpy arrays
        arcface_matrix = np.array(arcface_embeddings, dtype=np.float32)
        facenet_matrix = np.array(facenet_embeddings, dtype=np.float32)
        
        print(f"  Collected {len(criminal_ids)} criminal embeddings")
        print(f"  ArcFace matrix shape: {arcface_matrix.shape}")
        print(f"  Facenet matrix shape: {facenet_matrix.shape}")
        
        # Verify embeddings are normalized (for cosine similarity with inner product)
        arcface_norms = np.linalg.norm(arcface_matrix, axis=1)
        facenet_norms = np.linalg.norm(facenet_matrix, axis=1)
        print(f"  ArcFace embedding norms: min={arcface_norms.min():.4f}, max={arcface_norms.max():.4f}, mean={arcface_norms.mean():.4f}")
        print(f"  Facenet embedding norms: min={facenet_norms.min():.4f}, max={facenet_norms.max():.4f}, mean={facenet_norms.mean():.4f}")
        
        # Normalize embeddings if not already normalized (ensure unit vectors for cosine similarity)
        if not np.allclose(arcface_norms, 1.0, atol=0.01):
            print("  [INFO] Normalizing ArcFace embeddings...")
            arcface_matrix = arcface_matrix / arcface_norms[:, np.newaxis]
        
        if not np.allclose(facenet_norms, 1.0, atol=0.01):
            print("  [INFO] Normalizing Facenet embeddings...")
            facenet_matrix = facenet_matrix / facenet_norms[:, np.newaxis]
        
        # Build FAISS index for ArcFace (IndexFlatIP for cosine similarity with normalized vectors)
        embedding_dim = arcface_matrix.shape[1]
        print(f"\n  Building ArcFace FAISS index (dimension={embedding_dim})...")
        FAISS_INDEX_ARCFACE = faiss.IndexFlatIP(embedding_dim)  # Inner Product for cosine similarity
        FAISS_INDEX_ARCFACE.add(arcface_matrix)
        print(f"  [OK] ArcFace index built with {FAISS_INDEX_ARCFACE.ntotal} vectors")
        
        # Build FAISS index for Facenet
        embedding_dim = facenet_matrix.shape[1]
        print(f"\n  Building Facenet FAISS index (dimension={embedding_dim})...")
        FAISS_INDEX_FACENET = faiss.IndexFlatIP(embedding_dim)  # Inner Product for cosine similarity
        FAISS_INDEX_FACENET.add(facenet_matrix)
        print(f"  [OK] Facenet index built with {FAISS_INDEX_FACENET.ntotal} vectors")
        
        # Store criminal IDs in the same order as FAISS index
        FAISS_CRIMINAL_IDS = criminal_ids
        
        # Mark index as clean (synchronized with cache)
        FAISS_INDEX_DIRTY = False
        
        print("\n[FAISS INDEX SUMMARY]")
        print(f"  ArcFace index: {FAISS_INDEX_ARCFACE.ntotal} vectors")
        print(f"  Facenet index: {FAISS_INDEX_FACENET.ntotal} vectors")
        print(f"  Criminal IDs mapped: {len(FAISS_CRIMINAL_IDS)}")
        print("  Index type: IndexFlatIP (Inner Product for cosine similarity)")
        print("  Index status: CLEAN (synchronized with cache)")
        print("  Ready for fast retrieval!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"[ERROR] FAISS index build failed: {e}")
        traceback.print_exc()
        # Set to None so system falls back to linear search
        FAISS_INDEX_ARCFACE = None
        FAISS_INDEX_FACENET = None
        FAISS_CRIMINAL_IDS = []
        FAISS_INDEX_DIRTY = True  # Keep as dirty since build failed


def is_faiss_index_ready() -> bool:
    """
    Check if FAISS index is ready for use
    
    Returns:
        bool: True if FAISS index is built, synchronized, and ready
    """
    global FAISS_INDEX_DIRTY
    
    # Index is ready only if it exists AND is not dirty
    return (FAISS_INDEX_ARCFACE is not None and 
            FAISS_INDEX_FACENET is not None and 
            len(FAISS_CRIMINAL_IDS) > 0 and
            not FAISS_INDEX_DIRTY)


def get_faiss_index_stats() -> dict:
    """
    Get statistics about the FAISS index
    
    Returns:
        dict: Statistics including index size, criminal count, dirty status, etc.
    """
    return {
        'is_ready': is_faiss_index_ready(),
        'is_dirty': FAISS_INDEX_DIRTY,
        'arcface_vectors': FAISS_INDEX_ARCFACE.ntotal if FAISS_INDEX_ARCFACE else 0,
        'facenet_vectors': FAISS_INDEX_FACENET.ntotal if FAISS_INDEX_FACENET else 0,
        'criminal_ids_count': len(FAISS_CRIMINAL_IDS),
        'cache_size': len(EMBEDDING_CACHE),
        'synchronized': not FAISS_INDEX_DIRTY and len(FAISS_CRIMINAL_IDS) == len(EMBEDDING_CACHE)
    }


# ============================================================================
# FAISS SEARCH
# ============================================================================

def search_faiss_index(
    query_arcface: np.ndarray,
    query_facenet: np.ndarray,
    top_k: int = 5
) -> Tuple[bool, List[dict]]:
    """
    Search FAISS index for Top-K nearest neighbors using dual embeddings
    
    Automatically rebuilds index if it's dirty (out of sync with cache).
    
    Args:
        query_arcface: Query ArcFace embedding (512-D)
        query_facenet: Query Facenet embedding (512-D)
        top_k: Number of top candidates to retrieve
    
    Returns:
        Tuple[bool, List[dict]]: (success, candidates)
            success: True if FAISS search succeeded
            candidates: List of dicts with keys:
                - criminal_id: str
                - arcface_similarity: float
                - facenet_similarity: float
                - embedding_fusion: float
    """
    global FAISS_INDEX_ARCFACE, FAISS_INDEX_FACENET, FAISS_CRIMINAL_IDS, FAISS_INDEX_DIRTY
    
    # Auto-rebuild index if dirty (cache has changed)
    if FAISS_INDEX_DIRTY:
        print("  [AUTO-REBUILD] FAISS index is dirty, rebuilding...")
        build_faiss_index()
    
    if not is_faiss_index_ready():
        print("  FAISS index not available")
        return False, []
    
    print("  Attempting FAISS index for fast retrieval...")
    print(f"  Database size: {len(FAISS_CRIMINAL_IDS)} criminals")
    print(f"  Retrieving Top-{top_k} candidates...")
    
    try:
        # Normalize query embeddings (required for cosine similarity with IndexFlatIP)
        query_arcface = query_arcface.reshape(1, -1).astype(np.float32)
        query_facenet = query_facenet.reshape(1, -1).astype(np.float32)
        
        # Ensure query embeddings are normalized
        query_arcface_norm = np.linalg.norm(query_arcface)
        query_facenet_norm = np.linalg.norm(query_facenet)
        
        if query_arcface_norm > 0:
            query_arcface = query_arcface / query_arcface_norm
        if query_facenet_norm > 0:
            query_facenet = query_facenet / query_facenet_norm
        
        # Search FAISS index for Top-K nearest neighbors
        # Retrieve more candidates than needed to allow for fusion
        k_search = min(top_k * 3, len(FAISS_CRIMINAL_IDS))  # Search 3x to account for fusion
        
        # Search ArcFace index
        arcface_distances, arcface_indices = FAISS_INDEX_ARCFACE.search(query_arcface, k_search)
        arcface_distances = arcface_distances[0]  # Shape: (k_search,)
        arcface_indices = arcface_indices[0]  # Shape: (k_search,)
        
        # Search Facenet index
        facenet_distances, facenet_indices = FAISS_INDEX_FACENET.search(query_facenet, k_search)
        facenet_distances = facenet_distances[0]  # Shape: (k_search,)
        facenet_indices = facenet_indices[0]  # Shape: (k_search,)
        
        print("  [OK] FAISS search complete")
        print(f"    ArcFace Top-3: {arcface_distances[:3]}")
        print(f"    Facenet Top-3: {facenet_distances[:3]}")
        
        # Combine results from both models
        # Collect all unique candidates from both searches
        candidate_scores = {}  # {criminal_id: {'arcface': score, 'facenet': score}}
        
        # Process ArcFace results
        for idx, distance in zip(arcface_indices, arcface_distances):
            if idx >= 0 and idx < len(FAISS_CRIMINAL_IDS):  # Valid index
                criminal_id = FAISS_CRIMINAL_IDS[idx]
                if criminal_id not in candidate_scores:
                    candidate_scores[criminal_id] = {'arcface': 0.0, 'facenet': 0.0}
                # FAISS IndexFlatIP returns inner product (cosine similarity for normalized vectors)
                candidate_scores[criminal_id]['arcface'] = float(distance)
        
        # Process Facenet results
        for idx, distance in zip(facenet_indices, facenet_distances):
            if idx >= 0 and idx < len(FAISS_CRIMINAL_IDS):  # Valid index
                criminal_id = FAISS_CRIMINAL_IDS[idx]
                if criminal_id not in candidate_scores:
                    candidate_scores[criminal_id] = {'arcface': 0.0, 'facenet': 0.0}
                candidate_scores[criminal_id]['facenet'] = float(distance)
        
        # For candidates that appear in only one model's results, compute the missing score
        query_arcface_flat = query_arcface.flatten()
        query_facenet_flat = query_facenet.flatten()
        
        for criminal_id in candidate_scores:
            if candidate_scores[criminal_id]['arcface'] == 0.0:
                # Compute ArcFace similarity manually
                if criminal_id in EMBEDDING_CACHE:
                    criminal_embeddings = EMBEDDING_CACHE[criminal_id]
                    candidate_scores[criminal_id]['arcface'] = cosine_similarity(
                        query_arcface_flat, 
                        criminal_embeddings['arcface']
                    )
            if candidate_scores[criminal_id]['facenet'] == 0.0:
                # Compute Facenet similarity manually
                if criminal_id in EMBEDDING_CACHE:
                    criminal_embeddings = EMBEDDING_CACHE[criminal_id]
                    candidate_scores[criminal_id]['facenet'] = cosine_similarity(
                        query_facenet_flat, 
                        criminal_embeddings['facenet']
                    )
        
        # Compute fusion scores and create candidate list
        candidates = []
        for criminal_id, scores in candidate_scores.items():
            arcface_similarity = scores['arcface']
            facenet_similarity = scores['facenet']
            embedding_fusion = 0.5 * arcface_similarity + 0.5 * facenet_similarity
            
            candidates.append({
                'criminal_id': criminal_id,
                'arcface_similarity': arcface_similarity,
                'facenet_similarity': facenet_similarity,
                'embedding_fusion': embedding_fusion
            })
        
        # Sort by fusion score and select Top-K
        candidates.sort(key=lambda x: x['embedding_fusion'], reverse=True)
        top_candidates = candidates[:top_k]
        
        print(f"  [OK] FAISS retrieval complete: {len(candidate_scores)} unique candidates found")
        print(f"  [OK] Selected Top-{len(top_candidates)} for re-ranking")
        for idx, candidate in enumerate(top_candidates, 1):
            print(f"    {idx}. {candidate['criminal_id']}: fusion={candidate['embedding_fusion']:.4f} (arc={candidate['arcface_similarity']:.4f}, face={candidate['facenet_similarity']:.4f})")
        
        return True, top_candidates
        
    except Exception as e:
        print(f"  [ERROR] FAISS search failed: {e}")
        print("  [FALLBACK] Switching to linear search...")
        traceback.print_exc()
        return False, []


# ============================================================================
# LINEAR SEARCH (FALLBACK)
# ============================================================================

def linear_search_embeddings(
    query_arcface: np.ndarray,
    query_facenet: np.ndarray,
    criminal_ids: List[str],
    top_k: int = 5
) -> List[dict]:
    """
    Linear search over cached embeddings (fallback when FAISS not available)
    
    Args:
        query_arcface: Query ArcFace embedding (512-D)
        query_facenet: Query Facenet embedding (512-D)
        criminal_ids: List of criminal IDs to search
        top_k: Number of top candidates to retrieve
    
    Returns:
        List[dict]: List of candidates with keys:
            - criminal_id: str
            - arcface_similarity: float
            - facenet_similarity: float
            - embedding_fusion: float
    """
    print(f"  Using linear search over cached embeddings...")
    print(f"  Comparing against {len(criminal_ids)} criminals using embedding similarity...")
    
    candidates = []
    
    # Fast comparison using only cached embeddings
    for criminal_id in criminal_ids:
        try:
            # Check if precomputed dual embeddings exist in cache
            if criminal_id in EMBEDDING_CACHE:
                # Use precomputed dual embeddings
                criminal_embeddings = EMBEDDING_CACHE[criminal_id]
                
                # Compute similarity for both models using stable cosine similarity
                arcface_similarity = cosine_similarity(query_arcface, criminal_embeddings['arcface'])
                facenet_similarity = cosine_similarity(query_facenet, criminal_embeddings['facenet'])
                
                # Fuse the scores: 50% ArcFace + 50% Facenet
                embedding_fusion = 0.5 * arcface_similarity + 0.5 * facenet_similarity
                
                candidates.append({
                    'criminal_id': criminal_id,
                    'arcface_similarity': arcface_similarity,
                    'facenet_similarity': facenet_similarity,
                    'embedding_fusion': embedding_fusion
                })
            else:
                print(f"  [WARNING] No precomputed dual embeddings for {criminal_id}, skipping...")
                continue
                    
        except Exception as e:
            print(f"  [ERROR] Error comparing with criminal {criminal_id}: {e}")
            continue
    
    # Sort by embedding similarity and select Top-K
    candidates.sort(key=lambda x: x['embedding_fusion'], reverse=True)
    top_candidates = candidates[:top_k]
    
    print(f"  [OK] Linear search complete: {len(candidates)} candidates evaluated")
    print(f"  [OK] Selected Top-{len(top_candidates)} for re-ranking")
    for idx, candidate in enumerate(top_candidates, 1):
        print(f"    {idx}. {candidate['criminal_id']}: fusion={candidate['embedding_fusion']:.4f} (arc={candidate['arcface_similarity']:.4f}, face={candidate['facenet_similarity']:.4f})")
    
    return top_candidates


# ============================================================================
# UNIFIED SEARCH INTERFACE
# ============================================================================

def search_top_k_candidates(
    query_arcface: np.ndarray,
    query_facenet: np.ndarray,
    criminal_ids: List[str],
    top_k: int = 5
) -> Tuple[List[dict], bool]:
    """
    Search for Top-K candidates using FAISS (if available) or linear search (fallback)
    
    Args:
        query_arcface: Query ArcFace embedding (512-D)
        query_facenet: Query Facenet embedding (512-D)
        criminal_ids: List of all criminal IDs in database
        top_k: Number of top candidates to retrieve
    
    Returns:
        Tuple[List[dict], bool]: (candidates, used_faiss)
            candidates: List of dicts with keys:
                - criminal_id: str
                - arcface_similarity: float
                - facenet_similarity: float
                - embedding_fusion: float
            used_faiss: True if FAISS was used, False if linear search was used
    """
    # Try FAISS first
    success, candidates = search_faiss_index(query_arcface, query_facenet, top_k)
    
    if success:
        return candidates, True
    
    # Fallback to linear search
    candidates = linear_search_embeddings(query_arcface, query_facenet, criminal_ids, top_k)
    return candidates, False
