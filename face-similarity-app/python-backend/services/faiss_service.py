"""
FAISS Service — fast similarity search for dual embeddings.

Embedding keys: 'insightface' (replaces 'arcface') + 'facenet'
Both are 512-D L2-normalized vectors.
"""

import numpy as np
import faiss
import traceback
from typing import Dict, List, Tuple, Optional
from utils.similarity_utils import cosine_similarity


# ============================================================================
# GLOBAL STATE
# ============================================================================

# {criminal_id: {'insightface': np.ndarray, 'facenet': np.ndarray}}
EMBEDDING_CACHE: Dict[str, dict] = {}
EMBEDDING_VERSION = "dual_insightface_facenet_v1"

FAISS_INDEX_INSIGHTFACE = None   # 512-D InsightFace index
FAISS_INDEX_FACENET     = None   # 512-D Facenet index
FAISS_CRIMINAL_IDS: List[str] = []
FAISS_INDEX_DIRTY = True


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
    facenet_embedding: np.ndarray,
):
    """Store dual embeddings for a criminal and mark FAISS index dirty."""
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
    """Build dual FAISS IndexFlatIP indices from cached embeddings."""
    global FAISS_INDEX_INSIGHTFACE, FAISS_INDEX_FACENET, FAISS_CRIMINAL_IDS, FAISS_INDEX_DIRTY

    print("\n" + "=" * 60)
    print("BUILDING FAISS INDEX FOR FAST RETRIEVAL")
    print("=" * 60)

    try:
        if len(EMBEDDING_CACHE) == 0:
            print("[WARNING] No embeddings in cache, skipping FAISS index build")
            FAISS_INDEX_DIRTY = False
            return

        criminal_ids = sorted(EMBEDDING_CACHE.keys())
        insightface_embeddings = []
        facenet_embeddings = []
        valid_ids = []

        for cid in criminal_ids:
            embs = EMBEDDING_CACHE[cid]
            ins  = embs.get("insightface")
            face = embs.get("facenet")

            if ins is None and face is None:
                print(f"  [WARN] Skipping {cid}: both embeddings are None")
                continue

            # Mirror missing slot so FAISS always gets a valid vector
            if ins  is None: ins  = face
            if face is None: face = ins

            insightface_embeddings.append(np.array(ins,  dtype=np.float32))
            facenet_embeddings.append(    np.array(face, dtype=np.float32))
            valid_ids.append(cid)

        if not valid_ids:
            print("[WARNING] No valid embeddings to index")
            FAISS_INDEX_DIRTY = False
            return

        ins_matrix  = np.array(insightface_embeddings, dtype=np.float32)
        face_matrix = np.array(facenet_embeddings,     dtype=np.float32)

        print(f"  Collected {len(valid_ids)} criminal embeddings")
        print(f"  InsightFace matrix shape: {ins_matrix.shape}")
        print(f"  Facenet     matrix shape: {face_matrix.shape}")

        # Normalize if needed
        ins_norms  = np.linalg.norm(ins_matrix,  axis=1)
        face_norms = np.linalg.norm(face_matrix, axis=1)
        print(f"  InsightFace norms: min={ins_norms.min():.4f}, max={ins_norms.max():.4f}")
        print(f"  Facenet     norms: min={face_norms.min():.4f}, max={face_norms.max():.4f}")

        if not np.allclose(ins_norms,  1.0, atol=0.01):
            ins_matrix  = ins_matrix  / ins_norms[:, np.newaxis]
        if not np.allclose(face_norms, 1.0, atol=0.01):
            face_matrix = face_matrix / face_norms[:, np.newaxis]

        dim = ins_matrix.shape[1]
        print(f"\n  Building InsightFace FAISS index (dim={dim})...")
        FAISS_INDEX_INSIGHTFACE = faiss.IndexFlatIP(dim)
        FAISS_INDEX_INSIGHTFACE.add(ins_matrix)
        print(f"  [OK] InsightFace index: {FAISS_INDEX_INSIGHTFACE.ntotal} vectors")

        dim = face_matrix.shape[1]
        print(f"\n  Building Facenet FAISS index (dim={dim})...")
        FAISS_INDEX_FACENET = faiss.IndexFlatIP(dim)
        FAISS_INDEX_FACENET.add(face_matrix)
        print(f"  [OK] Facenet index: {FAISS_INDEX_FACENET.ntotal} vectors")

        FAISS_CRIMINAL_IDS = valid_ids
        FAISS_INDEX_DIRTY  = False

        print("\n[FAISS INDEX SUMMARY]")
        print(f"  InsightFace index: {FAISS_INDEX_INSIGHTFACE.ntotal} vectors")
        print(f"  Facenet     index: {FAISS_INDEX_FACENET.ntotal} vectors")
        print(f"  Criminal IDs mapped: {len(FAISS_CRIMINAL_IDS)}")
        print("  Index type: IndexFlatIP (cosine similarity)")
        print("  Index status: CLEAN")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"[ERROR] FAISS index build failed: {e}")
        traceback.print_exc()
        FAISS_INDEX_INSIGHTFACE = None
        FAISS_INDEX_FACENET     = None
        FAISS_CRIMINAL_IDS      = []
        FAISS_INDEX_DIRTY       = True


def is_faiss_index_ready() -> bool:
    return (
        FAISS_INDEX_INSIGHTFACE is not None
        and FAISS_INDEX_FACENET is not None
        and len(FAISS_CRIMINAL_IDS) > 0
        and not FAISS_INDEX_DIRTY
    )


def get_faiss_index_stats() -> dict:
    return {
        "is_ready":          is_faiss_index_ready(),
        "is_dirty":          FAISS_INDEX_DIRTY,
        "insightface_vectors": FAISS_INDEX_INSIGHTFACE.ntotal if FAISS_INDEX_INSIGHTFACE else 0,
        "facenet_vectors":   FAISS_INDEX_FACENET.ntotal     if FAISS_INDEX_FACENET     else 0,
        "criminal_ids_count": len(FAISS_CRIMINAL_IDS),
        "cache_size":        len(EMBEDDING_CACHE),
        "synchronized":      not FAISS_INDEX_DIRTY and len(FAISS_CRIMINAL_IDS) == len(EMBEDDING_CACHE),
    }


# ============================================================================
# FAISS SEARCH
# ============================================================================

def search_faiss_index(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray,
    top_k: int = 5,
) -> Tuple[bool, List[dict]]:
    """
    Search FAISS index for Top-K nearest neighbors using dual embeddings.
    Auto-rebuilds index if dirty.

    Returns (success, candidates) where each candidate has:
        criminal_id, insightface_similarity, facenet_similarity, embedding_fusion
    """
    global FAISS_INDEX_INSIGHTFACE, FAISS_INDEX_FACENET, FAISS_CRIMINAL_IDS, FAISS_INDEX_DIRTY

    if FAISS_INDEX_DIRTY:
        print("  [AUTO-REBUILD] FAISS index is dirty, rebuilding...")
        build_faiss_index()

    if not is_faiss_index_ready():
        print("  FAISS index not available")
        return False, []

    print(f"  FAISS search: {len(FAISS_CRIMINAL_IDS)} criminals, Top-{top_k}")

    try:
        # Normalize query vectors
        q_ins  = query_insightface.reshape(1, -1).astype(np.float32)
        q_face = query_facenet.reshape(1, -1).astype(np.float32)

        n_ins  = np.linalg.norm(q_ins)
        n_face = np.linalg.norm(q_face)
        if n_ins  > 0: q_ins  = q_ins  / n_ins
        if n_face > 0: q_face = q_face / n_face

        k_search = min(top_k * 3, len(FAISS_CRIMINAL_IDS))

        ins_dists,  ins_idxs  = FAISS_INDEX_INSIGHTFACE.search(q_ins,  k_search)
        face_dists, face_idxs = FAISS_INDEX_FACENET.search(    q_face, k_search)

        ins_dists  = ins_dists[0];  ins_idxs  = ins_idxs[0]
        face_dists = face_dists[0]; face_idxs = face_idxs[0]

        print(f"    InsightFace Top-3: {ins_dists[:3]}")
        print(f"    Facenet     Top-3: {face_dists[:3]}")

        candidate_scores: Dict[str, dict] = {}

        for idx, dist in zip(ins_idxs, ins_dists):
            if 0 <= idx < len(FAISS_CRIMINAL_IDS):
                cid = FAISS_CRIMINAL_IDS[idx]
                candidate_scores.setdefault(cid, {"insightface": 0.0, "facenet": 0.0})
                candidate_scores[cid]["insightface"] = float(dist)

        for idx, dist in zip(face_idxs, face_dists):
            if 0 <= idx < len(FAISS_CRIMINAL_IDS):
                cid = FAISS_CRIMINAL_IDS[idx]
                candidate_scores.setdefault(cid, {"insightface": 0.0, "facenet": 0.0})
                candidate_scores[cid]["facenet"] = float(dist)

        # Fill missing scores from cache
        q_ins_flat  = q_ins.flatten()
        q_face_flat = q_face.flatten()

        for cid, scores in candidate_scores.items():
            cached = EMBEDDING_CACHE.get(cid, {})
            if scores["insightface"] == 0.0 and cached.get("insightface") is not None:
                scores["insightface"] = cosine_similarity(q_ins_flat,  cached["insightface"])
            if scores["facenet"] == 0.0 and cached.get("facenet") is not None:
                scores["facenet"] = cosine_similarity(q_face_flat, cached["facenet"])

        candidates = [
            {
                "criminal_id":            cid,
                "insightface_similarity": s["insightface"],
                "facenet_similarity":     s["facenet"],
                # Facenet is more robust for sketch-to-photo; InsightFace supplements
                "embedding_fusion":       0.1 * s["insightface"] + 0.9 * s["facenet"],
            }
            for cid, s in candidate_scores.items()
        ]
        candidates.sort(key=lambda x: x["embedding_fusion"], reverse=True)
        top = candidates[:top_k]

        print(f"  [OK] FAISS: {len(candidate_scores)} unique candidates, Top-{len(top)} selected")
        for i, c in enumerate(top, 1):
            print(f"    {i}. {c['criminal_id']}: fusion={c['embedding_fusion']:.4f} "
                  f"(ins={c['insightface_similarity']:.4f}, face={c['facenet_similarity']:.4f})")

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
    query_facenet: np.ndarray,
    criminal_ids: List[str],
    top_k: int = 5,
) -> List[dict]:
    """Linear search fallback when FAISS is unavailable."""
    print(f"  Linear search over {len(criminal_ids)} criminals...")

    candidates = []
    for cid in criminal_ids:
        cached = EMBEDDING_CACHE.get(cid)
        if cached is None:
            print(f"  [WARNING] No cached embeddings for {cid}, skipping")
            continue
        try:
            ins_sim  = cosine_similarity(query_insightface, cached["insightface"])
            face_sim = cosine_similarity(query_facenet,     cached["facenet"])
            # Facenet is more robust for sketch-to-photo; InsightFace supplements
            fusion   = 0.1 * ins_sim + 0.9 * face_sim
            candidates.append({
                "criminal_id":            cid,
                "insightface_similarity": ins_sim,
                "facenet_similarity":     face_sim,
                "embedding_fusion":       fusion,
            })
        except Exception as e:
            print(f"  [ERROR] Comparing {cid}: {e}")

    candidates.sort(key=lambda x: x["embedding_fusion"], reverse=True)
    top = candidates[:top_k]

    print(f"  [OK] Linear search: {len(candidates)} evaluated, Top-{len(top)} selected")
    for i, c in enumerate(top, 1):
        print(f"    {i}. {c['criminal_id']}: fusion={c['embedding_fusion']:.4f}")

    return top


# ============================================================================
# UNIFIED SEARCH INTERFACE
# ============================================================================

def search_top_k_candidates(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray,
    criminal_ids: List[str],
    top_k: int = 5,
) -> Tuple[List[dict], bool]:
    """
    Search Top-K candidates via FAISS (preferred) or linear search (fallback).

    Returns (candidates, used_faiss).
    """
    success, candidates = search_faiss_index(query_insightface, query_facenet, top_k)
    if success:
        return candidates, True
    candidates = linear_search_embeddings(query_insightface, query_facenet, criminal_ids, top_k)
    return candidates, False
