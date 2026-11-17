"""Cosine similarity for complaint embeddings."""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def normalize_score(similarity: float) -> float:
    """Normalize cosine similarity to 0-1 range (cosine sim is already -1 to 1, clamp to 0-1)."""
    return max(0.0, min(1.0, similarity))
