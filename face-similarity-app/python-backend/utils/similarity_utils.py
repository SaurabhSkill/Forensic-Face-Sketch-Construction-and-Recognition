"""
Similarity calculation utilities for face comparison
"""
import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors, normalized to [0, 1].

    Raw cosine similarity is in [-1, 1]. For face embeddings, InsightFace
    (ArcFace) embeddings can produce negative cosine values for non-matching
    pairs, which causes fusion scores to be near zero or negative.

    We map to [0, 1] using: normalized = (cosine + 1) / 2
      - cosine = -1  → 0.0  (completely opposite)
      - cosine =  0  → 0.5  (orthogonal / unrelated)
      - cosine = +1  → 1.0  (identical)

    This ensures InsightFace scores are always positive and meaningful
    when fused with Facenet scores.

    Args:
        a: First embedding vector
        b: Second embedding vector

    Returns:
        float: Normalized cosine similarity in range [0, 1]
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    raw = float(np.dot(a, b) / (norm_a * norm_b))

    # Normalize from [-1, 1] to [0, 1]
    return (raw + 1.0) / 2.0
