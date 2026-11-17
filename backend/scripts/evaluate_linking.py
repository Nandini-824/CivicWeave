"""
Evaluate incident linking strategies on labeled seed scenarios.

Compares:
1. Semantic similarity only
2. Semantic + spatial verification
3. Semantic + spatial + temporal verification

Usage (from backend/):
    python -m scripts.evaluate_linking
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.embeddings import generate_embedding
from app.ai.similarity import cosine_similarity, normalize_score
from app.ai.spatial import haversine_distance_meters, spatial_score
from app.ai.temporal import temporal_score
from app.config import get_settings

settings = get_settings()

# Labeled pairs: (text_a, text_b, lat_a, lon_a, lat_b, lon_b, hours_apart, should_match, category)
LABELED_PAIRS = [
    (
        "There is a huge pothole near ABC Chowk.",
        "The road at ABC Chowk is badly damaged.",
        18.5310, 73.8446, 18.5311, 73.8447, 4, True, "Roads and Potholes",
    ),
    (
        "Water pipe leaking near Market Road.",
        "Continuous water flowing from broken pipeline.",
        18.5280, 73.8475, 18.5281, 73.8476, 3, True, "Water Supply",
    ),
    (
        "Pothole near ABC Chowk.",
        "Pothole near XYZ Nagar.",
        18.5310, 73.8446, 18.5074, 73.8077, 1, False, "Roads and Potholes",
    ),
    (
        "Street light not working.",
        "Water pipe burst near market.",
        18.5200, 73.8500, 18.5201, 73.8501, 1, False, "Street Lighting",
    ),
    (
        "Dangerous hole in road near ABC signal.",
        "Vehicles struggling because of broken road near ABC Chowk.",
        18.5310, 73.8446, 18.5309, 73.8445, 8, True, "Roads and Potholes",
    ),
]


def strategy_semantic_only(emb_a, emb_b, **kwargs) -> bool:
    sem = normalize_score(cosine_similarity(emb_a, emb_b))
    return sem >= settings.semantic_similarity_threshold


def strategy_semantic_spatial(emb_a, emb_b, lat_a, lon_a, lat_b, lon_b, category, **kwargs) -> bool:
    sem = normalize_score(cosine_similarity(emb_a, emb_b))
    if sem < settings.semantic_similarity_threshold:
        return False
    dist = haversine_distance_meters(lat_a, lon_a, lat_b, lon_b)
    spat = spatial_score(dist, category)
    return spat > 0.3


def strategy_full(emb_a, emb_b, lat_a, lon_a, lat_b, lon_b, hours_apart, category, **kwargs) -> bool:
    sem = normalize_score(cosine_similarity(emb_a, emb_b))
    dist = haversine_distance_meters(lat_a, lon_a, lat_b, lon_b)
    spat = spatial_score(dist, category)
    now = datetime.now(timezone.utc)
    temp = temporal_score(now, now - timedelta(hours=hours_apart), category)
    combined = settings.semantic_weight * sem + settings.spatial_weight * spat + settings.temporal_weight * temp
    return combined >= settings.combined_score_threshold and sem >= settings.semantic_similarity_threshold


def evaluate_strategy(name, strategy_fn):
    tp = fp = fn = tn = 0
    for text_a, text_b, lat_a, lon_a, lat_b, lon_b, hours, should_match, category in LABELED_PAIRS:
        emb_a = generate_embedding(text_a)
        emb_b = generate_embedding(text_b)
        predicted = strategy_fn(
            emb_a, emb_b,
            lat_a=lat_a, lon_a=lon_a, lat_b=lat_b, lon_b=lon_b,
            hours_apart=hours, category=category,
        )
        if predicted and should_match:
            tp += 1
        elif predicted and not should_match:
            fp += 1
        elif not predicted and should_match:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"strategy": name, "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": precision, "recall": recall, "f1": f1}


def main():
    print("CivicWeave Incident Linking Evaluation")
    print("=" * 50)
    print(f"Labeled pairs: {len(LABELED_PAIRS)}")
    print(f"Thresholds: semantic={settings.semantic_similarity_threshold}, combined={settings.combined_score_threshold}")
    print()

    strategies = [
        ("Semantic Only", strategy_semantic_only),
        ("Semantic + Spatial", strategy_semantic_spatial),
        ("Semantic + Spatial + Temporal", strategy_full),
    ]

    for name, fn in strategies:
        result = evaluate_strategy(name, fn)
        print(f"--- {result['strategy']} ---")
        print(f"  TP={result['tp']} FP={result['fp']} FN={result['fn']} TN={result['tn']}")
        print(f"  Precision: {result['precision']:.2%}")
        print(f"  Recall:    {result['recall']:.2%}")
        print(f"  F1:        {result['f1']:.2%}")
        print()

    print("Note: Metrics computed on labeled demo pairs only — not experimentally validated.")


if __name__ == "__main__":
    main()
