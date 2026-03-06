"""
Similarity calculation utilities for face comparison
"""
import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors using numerically stable formula.
    
    Formula: similarity = dot(a, b) / (||a|| * ||b||)
    
    This is more stable than relying on pre-normalized embeddings,
    as it handles any numerical drift from normalization.
    
    Args:
        a: First embedding vector
        b: Second embedding vector
    
    Returns:
        float: Cosine similarity in range [-1, 1], or 0.0 if either vector is zero
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    # Handle zero vectors
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    # Compute cosine similarity
    similarity = np.dot(a, b) / (norm_a * norm_b)
    
    return float(similarity)
