"""
FAISS Service — fast similarity search using InsightFace embeddings only.

Embedding key: 'insightface' — 512-D L2-normalized vector.
"""

import numpy as np
import faiss
import traceback
from typing import Dict, List, Tuple, Optional
from utils.similarity_utils import cosine_similarity


# ============================================================================
# GLOBAL STATE
# ============================================================================

# {criminal_id: {'insightface': np.ndarray}}
EMBEDDING_CACHE: Dict[str, dict] = {}
EMBEDDING_VERSION = "insightface_v2"

FAISS_INDEX_INSIGHTFACE = None
FAISS_CRIMINAL_IDS: List[str] = []
FAISS_INDEX_DIRTY = True

# Kept for API compatibility — always None
FAISS_INDEX_FACENET = None


# ============================================================================
# EMBEDDING CACHE MANAGEMENT
# ============================================================================

def get_embedding_cache() -> dict:
    return EMBEDDING_CACHE


def get_embedding_version() -> str:
    return EMBEDDING_VERSION


def set_cached_embedding(
    criminal_id: str,
    insightface_embedding: np.ndarray,
    facenet_embedding: np.ndarray = None,
):
    """Store InsightFace (and optionally Facenet) embedding for a criminal."""
    global EMBEDDING_CACHE, FAISS_INDEX_DIRTY
    EMBEDDING_CACHE[criminal_id] = {
        "insightface": insightface_embedding,
        "facenet":     facenet_embedding,
    }
    FAISS_INDEX_DIRTY = True


def get_cached_embedding(criminal_id: str) -> Optional[dict]:
    return EMBEDDING_CACHE.get(criminal_id)


def clear_embedding_cache():
    global EMBEDDING_CACHE, FAISS_INDEX_DIRTY
    EMBEDDING_CACHE = {}
    FAISS_INDEX_DIRTY = True


def get_cache_size() -> int:
    return len(EMBEDDING_CACHE)


# ============================================================================
# FAISS INDEX BUILDING
# ============================================================================

def build_faiss_index():
    """Build a single FAISS IndexFlatIP from cached InsightFace embeddings."""
    global FAISS_INDEX_INSIGHTFACE, FAISS_CRIMINAL_IDS, FAISS_INDEX_DIRTY

    print("\n" + "=" * 60)
    print("BUILDING FAISS INDEX (InsightFace)")
    print("=" * 60)

    try:
        if len(EMBEDDING_CACHE) == 0:
            print("[WARNING] No embeddings in cache, skipping FAISS index build")
            FAISS_INDEX_DIRTY = False
            return

        criminal_ids = sorted(EMBEDDING_CACHE.keys())
        embeddings = []
        valid_ids  = []

        for cid in criminal_ids:
            ins = EMBEDDING_CACHE[cid].get("insightface")
            if ins is None:
                print(f"  [WARN] Skipping {cid}: InsightFace embedding is None")
                continue
            embeddings.append(np.array(ins, dtype=np.float32))
            valid_ids.append(cid)

        if not valid_ids:
            print("[WARNING] No valid embeddings to index")
            FAISS_INDEX_DIRTY = False
            return

        matrix = np.array(embeddings, dtype=np.float32)
        print(f"  Collected {len(valid_ids)} embeddings, shape: {matrix.shape}")

        # Normalize
        norms = np.linalg.norm(matrix, axis=1)
        print(f"  Norms: min={norms.min():.4f}, max={norms.max():.4f}")
        if not np.allclose(norms, 1.0, atol=0.01):
            matrix = matrix / norms[:, np.newaxis]

        dim = matrix.shape[1]
        print(f"  Building FAISS IndexFlatIP (dim={dim})...")
        FAISS_INDEX_INSIGHTFACE = faiss.IndexFlatIP(dim)
        FAISS_INDEX_INSIGHTFACE.add(matrix)

        FAISS_CRIMINAL_IDS = valid_ids
        FAISS_INDEX_DIRTY  = False

        print(f"  [OK] InsightFace index: {FAISS_INDEX_INSIGHTFACE.ntotal} vectors")
        print(f"  Criminal IDs mapped: {len(FAISS_CRIMINAL_IDS)}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"[ERROR] FAISS index build failed: {e}")
        traceback.print_exc()
        FAISS_INDEX_INSIGHTFACE = None
        FAISS_CRIMINAL_IDS      = []
        FAISS_INDEX_DIRTY       = True


def is_faiss_index_ready() -> bool:
    return (
        FAISS_INDEX_INSIGHTFACE is not None
        and len(FAISS_CRIMINAL_IDS) > 0
        and not FAISS_INDEX_DIRTY
    )


def get_faiss_index_stats() -> dict:
    return {
        "is_ready":            is_faiss_index_ready(),
        "is_dirty":            FAISS_INDEX_DIRTY,
        "insightface_vectors": FAISS_INDEX_INSIGHTFACE.ntotal if FAISS_INDEX_INSIGHTFACE else 0,
        "facenet_vectors":     0,   # kept for API compatibility
        "criminal_ids_count":  len(FAISS_CRIMINAL_IDS),
        "cache_size":          len(EMBEDDING_CACHE),
        "synchronized":        not FAISS_INDEX_DIRTY and len(FAISS_CRIMINAL_IDS) == len(EMBEDDING_CACHE),
    }


# ============================================================================
# FAISS SEARCH
# ============================================================================

def search_faiss_index(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray = None,   # ignored — kept for API compatibility
    top_k: int = 5,
) -> Tuple[bool, List[dict]]:
    """Search FAISS index using InsightFace embedding."""
    global FAISS_INDEX_INSIGHTFACE, FAISS_CRIMINAL_IDS, FAISS_INDEX_DIRTY

    if FAISS_INDEX_DIRTY:
        print("  [AUTO-REBUILD] FAISS index is dirty, rebuilding...")
        build_faiss_index()

    if not is_faiss_index_ready():
        print("  FAISS index not available")
        return False, []

    print(f"  FAISS search: {len(FAISS_CRIMINAL_IDS)} criminals, Top-{top_k}")

    try:
        q = query_insightface.reshape(1, -1).astype(np.float32)
        n = np.linalg.norm(q)
        if n > 0:
            q = q / n

        k_search = min(top_k * 3, len(FAISS_CRIMINAL_IDS))
        dists, idxs = FAISS_INDEX_INSIGHTFACE.search(q, k_search)
        dists = dists[0]
        idxs  = idxs[0]

        print(f"    InsightFace Top-3: {dists[:3]}")

        candidates = []
        for idx, dist in zip(idxs, dists):
            if 0 <= idx < len(FAISS_CRIMINAL_IDS):
                cid = FAISS_CRIMINAL_IDS[idx]
                candidates.append({
                    "criminal_id":            cid,
                    "insightface_similarity": float(dist),
                    "facenet_similarity":     None,   # kept for API compatibility
                    "embedding_fusion":       float(dist),
                })

        candidates.sort(key=lambda x: x["embedding_fusion"], reverse=True)
        top = candidates[:top_k]

        print(f"  [OK] FAISS: {len(candidates)} candidates, Top-{len(top)} selected")
        for i, c in enumerate(top, 1):
            print(f"    {i}. {c['criminal_id']}: score={c['embedding_fusion']:.4f}")

        return True, top

    except Exception as e:
        print(f"  [ERROR] FAISS search failed: {e}")
        traceback.print_exc()
        return False, []


# ============================================================================
# LINEAR SEARCH (FALLBACK)
# ============================================================================

def linear_search_embeddings(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray = None,   # ignored — kept for API compatibility
    criminal_ids: List[str] = None,
    top_k: int = 5,
) -> List[dict]:
    """Linear search fallback when FAISS is unavailable."""
    if criminal_ids is None:
        criminal_ids = list(EMBEDDING_CACHE.keys())

    print(f"  Linear search over {len(criminal_ids)} criminals...")

    candidates = []
    for cid in criminal_ids:
        cached = EMBEDDING_CACHE.get(cid)
        if cached is None or cached.get("insightface") is None:
            print(f"  [WARNING] No cached embedding for {cid}, skipping")
            continue
        try:
            sim = cosine_similarity(query_insightface, cached["insightface"])
            candidates.append({
                "criminal_id":            cid,
                "insightface_similarity": sim,
                "facenet_similarity":     None,
                "embedding_fusion":       sim,
            })
        except Exception as e:
            print(f"  [ERROR] Comparing {cid}: {e}")

    candidates.sort(key=lambda x: x["embedding_fusion"], reverse=True)
    top = candidates[:top_k]

    print(f"  [OK] Linear search: {len(candidates)} evaluated, Top-{len(top)} selected")
    for i, c in enumerate(top, 1):
        print(f"    {i}. {c['criminal_id']}: score={c['embedding_fusion']:.4f}")

    return top


# ============================================================================
# UNIFIED SEARCH INTERFACE
# ============================================================================

def search_top_k_candidates(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray = None,   # ignored — kept for API compatibility
    criminal_ids: List[str] = None,
    top_k: int = 5,
) -> Tuple[List[dict], bool]:
    """Search Top-K via FAISS (preferred) or linear search (fallback)."""
    success, candidates = search_faiss_index(query_insightface, query_facenet, top_k)
    if success:
        return candidates, True
    candidates = linear_search_embeddings(query_insightface, query_facenet, criminal_ids, top_k)
    return candidates, False
