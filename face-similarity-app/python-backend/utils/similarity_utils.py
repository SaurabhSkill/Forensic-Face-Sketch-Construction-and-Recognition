"""
Similarity calculation utilities for face comparison
"""
import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute raw cosine similarity between two L2-normalized vectors.

    Formula: sim = dot(a, b) / (||a|| * ||b||)

    For L2-normalized embeddings (InsightFace ArcFace), this returns
    values in [-1, 1]:
      - sim =  1.0  → identical vectors (same person)
      - sim =  0.0  → orthogonal (unrelated)
      - sim = -1.0  → opposite (very different)

    Expected ranges for face recognition:
      - Same person:      0.5 – 0.8
      - Different person: 0.0 – 0.4

    Args:
        a: First embedding vector
        b: Second embedding vector

    Returns:
        float: Raw cosine similarity in range [-1, 1]
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    # Ensure L2 normalized before dot product
    a_norm = a / norm_a
    b_norm = b / norm_b

    sim = float(np.dot(a_norm, b_norm))
    return sim
