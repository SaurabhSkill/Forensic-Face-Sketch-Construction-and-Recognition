"""
FAISS Service — dual-index similarity search (InsightFace + Facenet).

Two independent IndexFlatIP indexes are maintained:
  - FAISS_INDEX_INSIGHTFACE  (512-D ArcFace embeddings)
  - FAISS_INDEX_FACENET      (512-D Facenet512 embeddings)

Search strategy:
  - Sketch query  → Facenet index primary, InsightFace secondary
  - Photo  query  → InsightFace index primary, Facenet secondary
  - Results from both indexes are merged (union) and deduplicated before
    passing to Stage-2 re-ranking.

Cosine similarity calibration:
  sim_calibrated = (raw_cosine + 1) / 2   → maps [-1,1] to [0,1]
  This prevents extreme negative values from distorting fusion scores.
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
EMBEDDING_VERSION = "dual_v1"

FAISS_INDEX_INSIGHTFACE = None
FAISS_INDEX_FACENET     = None
FAISS_IDS_INSIGHTFACE: List[str] = []   # criminal_id order for InsightFace index
FAISS_IDS_FACENET:     List[str] = []   # criminal_id order for Facenet index
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
    facenet_embedding: np.ndarray = None,
):
    """Store InsightFace and Facenet embeddings for a criminal."""
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
# HELPERS
# ============================================================================

def _calibrate(sim: float) -> float:
    """Map raw cosine similarity [-1, 1] -> [0, 1]."""
    return (float(sim) + 1.0) / 2.0


def _build_index_from_embeddings(
    embeddings: List[np.ndarray],
) -> Optional[faiss.IndexFlatIP]:
    """Build a normalized FAISS IndexFlatIP from a list of 512-D vectors."""
    if not embeddings:
        return None
    matrix = np.array(embeddings, dtype=np.float32)
    norms  = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms  = np.where(norms == 0, 1.0, norms)
    matrix = matrix / norms
    dim    = matrix.shape[1]
    idx    = faiss.IndexFlatIP(dim)
    idx.add(matrix)
    return idx


# ============================================================================
# FAISS INDEX BUILDING
# ============================================================================

def build_faiss_index():
    """Build dual FAISS indexes (InsightFace + Facenet) from the embedding cache."""
    global FAISS_INDEX_INSIGHTFACE, FAISS_INDEX_FACENET
    global FAISS_IDS_INSIGHTFACE, FAISS_IDS_FACENET, FAISS_INDEX_DIRTY

    print("\n" + "=" * 60)
    print("BUILDING DUAL FAISS INDEXES (InsightFace + Facenet)")
    print("=" * 60)

    try:
        if len(EMBEDDING_CACHE) == 0:
            print("[WARNING] No embeddings in cache, skipping FAISS index build")
            FAISS_INDEX_DIRTY = False
            return

        ins_embs, ins_ids   = [], []
        face_embs, face_ids = [], []

        for cid in sorted(EMBEDDING_CACHE.keys()):
            entry = EMBEDDING_CACHE[cid]
            ins  = entry.get("insightface")
            face = entry.get("facenet")

            if ins is not None:
                ins_embs.append(np.array(ins, dtype=np.float32))
                ins_ids.append(cid)
            else:
                print(f"  [WARN] {cid}: InsightFace embedding missing — skipped from InsightFace index")

            if face is not None:
                face_embs.append(np.array(face, dtype=np.float32))
                face_ids.append(cid)
            else:
                print(f"  [WARN] {cid}: Facenet embedding missing — skipped from Facenet index")

        # InsightFace index
        if ins_embs:
            FAISS_INDEX_INSIGHTFACE = _build_index_from_embeddings(ins_embs)
            FAISS_IDS_INSIGHTFACE   = ins_ids
            print(f"  [OK] InsightFace index: {FAISS_INDEX_INSIGHTFACE.ntotal} vectors")
        else:
            FAISS_INDEX_INSIGHTFACE = None
            FAISS_IDS_INSIGHTFACE   = []
            print("  [WARN] InsightFace index: no valid embeddings")

        # Facenet index
        if face_embs:
            FAISS_INDEX_FACENET = _build_index_from_embeddings(face_embs)
            FAISS_IDS_FACENET   = face_ids
            print(f"  [OK] Facenet index: {FAISS_INDEX_FACENET.ntotal} vectors")
        else:
            FAISS_INDEX_FACENET = None
            FAISS_IDS_FACENET   = []
            print("  [WARN] Facenet index: no valid embeddings")

        FAISS_INDEX_DIRTY = False
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"[ERROR] FAISS dual index build failed: {e}")
        traceback.print_exc()
        FAISS_INDEX_INSIGHTFACE = None
        FAISS_INDEX_FACENET     = None
        FAISS_IDS_INSIGHTFACE   = []
        FAISS_IDS_FACENET       = []
        FAISS_INDEX_DIRTY       = True


def is_faiss_index_ready() -> bool:
    return (
        not FAISS_INDEX_DIRTY
        and (FAISS_INDEX_INSIGHTFACE is not None or FAISS_INDEX_FACENET is not None)
    )


def get_faiss_index_stats() -> dict:
    return {
        "is_ready":            is_faiss_index_ready(),
        "is_dirty":            FAISS_INDEX_DIRTY,
        "insightface_vectors": FAISS_INDEX_INSIGHTFACE.ntotal if FAISS_INDEX_INSIGHTFACE else 0,
        "facenet_vectors":     FAISS_INDEX_FACENET.ntotal if FAISS_INDEX_FACENET else 0,
        "criminal_ids_count":  len(set(FAISS_IDS_INSIGHTFACE) | set(FAISS_IDS_FACENET)),
        "cache_size":          len(EMBEDDING_CACHE),
        "synchronized":        not FAISS_INDEX_DIRTY,
    }


# ============================================================================
# SINGLE-INDEX SEARCH HELPER
# ============================================================================

def _search_single_index(
    index: faiss.IndexFlatIP,
    id_list: List[str],
    query: np.ndarray,
    top_k: int,
    model_label: str,
) -> List[dict]:
    """Search one FAISS index, return calibrated candidates."""
    q = query.reshape(1, -1).astype(np.float32)
    n = np.linalg.norm(q)
    if n > 0:
        q = q / n

    k = min(top_k, len(id_list))
    dists, idxs = index.search(q, k)
    dists = dists[0]
    idxs  = idxs[0]

    results = []
    for idx, raw_dist in zip(idxs, dists):
        if 0 <= idx < len(id_list):
            cal = _calibrate(raw_dist)
            results.append({
                "criminal_id":  id_list[idx],
                "raw_score":    float(raw_dist),
                "cal_score":    cal,
                "source_model": model_label,
            })
    return results


# ============================================================================
# DUAL FAISS SEARCH
# ============================================================================

def search_faiss_index(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray = None,
    top_k: int = 10,
    is_sketch: bool = False,
) -> Tuple[bool, List[dict]]:
    """
    Dual-index FAISS search.

    Strategy:
      - Sketch: Facenet primary (weight 0.9), InsightFace secondary (weight 0.1)
      - Photo:  InsightFace primary (weight 0.5), Facenet secondary (weight 0.5)

    Returns merged, deduplicated, fused-score candidates sorted best-first.
    """
    global FAISS_INDEX_DIRTY

    if FAISS_INDEX_DIRTY:
        print("  [AUTO-REBUILD] FAISS index is dirty, rebuilding...")
        build_faiss_index()

    if not is_faiss_index_ready():
        print("  FAISS index not available")
        return False, []

    # Adaptive weights
    if is_sketch:
        w_face = 0.9
        w_ins  = 0.1
    else:
        w_face = 0.5
        w_ins  = 0.5

    print(f"  FAISS dual search: {len(set(FAISS_IDS_INSIGHTFACE) | set(FAISS_IDS_FACENET))} criminals, "
          f"Top-{top_k}, is_sketch={is_sketch}")
    print(f"  Weights: InsightFace={w_ins:.2f}, Facenet={w_face:.2f}")

    # Retrieve from each index
    ins_results  = []
    face_results = []

    if FAISS_INDEX_INSIGHTFACE is not None and query_insightface is not None:
        ins_results = _search_single_index(
            FAISS_INDEX_INSIGHTFACE, FAISS_IDS_INSIGHTFACE,
            query_insightface, top_k * 2, "insightface"
        )
        print(f"  InsightFace top scores: {[round(r['cal_score'], 3) for r in ins_results[:5]]}")

    if FAISS_INDEX_FACENET is not None and query_facenet is not None:
        face_results = _search_single_index(
            FAISS_INDEX_FACENET, FAISS_IDS_FACENET,
            query_facenet, top_k * 2, "facenet"
        )
        print(f"  Facenet top scores: {[round(r['cal_score'], 3) for r in face_results[:5]]}")

    # Build per-criminal score maps
    ins_map  = {r["criminal_id"]: r["cal_score"] for r in ins_results}
    face_map = {r["criminal_id"]: r["cal_score"] for r in face_results}

    # Union of all candidates
    all_ids = set(ins_map.keys()) | set(face_map.keys())

    candidates = []
    for cid in all_ids:
        s_ins  = ins_map.get(cid, 0.5)   # 0.5 = neutral calibrated score if missing
        s_face = face_map.get(cid, 0.5)

        # Clamp Facenet to max calibrated 0.875 (raw 0.75 -> cal 0.875)
        s_face = min(s_face, 0.875)

        fused = w_ins * s_ins + w_face * s_face

        candidates.append({
            "criminal_id":            cid,
            "insightface_similarity": s_ins,
            "facenet_similarity":     s_face if cid in face_map else None,
            "embedding_fusion":       fused,
        })

    candidates.sort(key=lambda x: x["embedding_fusion"], reverse=True)
    top = candidates[:top_k]

    print(f"  [OK] Merged {len(all_ids)} unique candidates, Top-{len(top)} selected")
    for i, c in enumerate(top, 1):
        face_str = f"{c['facenet_similarity']:.4f}" if c['facenet_similarity'] is not None else "N/A"
        print(f"    {i}. {c['criminal_id']}: fused={c['embedding_fusion']:.4f} "
              f"(ins={c['insightface_similarity']:.4f}, face={face_str})")

    return True, top


# ============================================================================
# LINEAR SEARCH (FALLBACK)
# ============================================================================

def linear_search_embeddings(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray = None,
    criminal_ids: List[str] = None,
    top_k: int = 10,
    is_sketch: bool = False,
) -> List[dict]:
    """Linear search fallback when FAISS is unavailable."""
    if criminal_ids is None:
        criminal_ids = list(EMBEDDING_CACHE.keys())

    w_face = 0.9 if is_sketch else 0.5
    w_ins  = 0.1 if is_sketch else 0.5

    print(f"  Linear search over {len(criminal_ids)} criminals "
          f"(ins={w_ins:.2f}, face={w_face:.2f})...")

    candidates = []
    for cid in criminal_ids:
        cached = EMBEDDING_CACHE.get(cid)
        if cached is None:
            continue
        try:
            s_ins  = 0.5
            s_face = 0.5

            if cached.get("insightface") is not None and query_insightface is not None:
                raw   = cosine_similarity(query_insightface, cached["insightface"])
                s_ins = _calibrate(raw)

            if cached.get("facenet") is not None and query_facenet is not None:
                raw    = cosine_similarity(query_facenet, cached["facenet"])
                s_face = min(_calibrate(raw), 0.875)  # clamp

            fused = w_ins * s_ins + w_face * s_face
            candidates.append({
                "criminal_id":            cid,
                "insightface_similarity": s_ins,
                "facenet_similarity":     s_face if cached.get("facenet") is not None else None,
                "embedding_fusion":       fused,
            })
        except Exception as e:
            print(f"  [ERROR] Comparing {cid}: {e}")

    candidates.sort(key=lambda x: x["embedding_fusion"], reverse=True)
    top = candidates[:top_k]

    print(f"  [OK] Linear search: {len(candidates)} evaluated, Top-{len(top)} selected")
    for i, c in enumerate(top, 1):
        print(f"    {i}. {c['criminal_id']}: fused={c['embedding_fusion']:.4f}")

    return top


# ============================================================================
# UNIFIED SEARCH INTERFACE
# ============================================================================

def search_top_k_candidates(
    query_insightface: np.ndarray,
    query_facenet: np.ndarray = None,
    criminal_ids: List[str] = None,
    top_k: int = 10,
    is_sketch: bool = False,
) -> Tuple[List[dict], bool]:
    """Search Top-K via FAISS (preferred) or linear search (fallback)."""
    success, candidates = search_faiss_index(
        query_insightface, query_facenet, top_k, is_sketch
    )
    if success:
        return candidates, True
    candidates = linear_search_embeddings(
        query_insightface, query_facenet, criminal_ids, top_k, is_sketch
    )
    return candidates, False
