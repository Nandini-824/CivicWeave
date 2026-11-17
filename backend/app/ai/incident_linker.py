"""Incident Linking Engine - combines semantic, spatial, and temporal signals."""

from datetime import datetime, timezone
from app.config import get_settings
from app.ai.similarity import cosine_similarity, normalize_score
from app.ai.spatial import haversine_distance_meters, spatial_score
from app.ai.temporal import temporal_score

settings = get_settings()


def compute_combined_score(semantic: float, spatial: float, temporal: float) -> float:
    return (
        settings.semantic_weight * semantic
        + settings.spatial_weight * spatial
        + settings.temporal_weight * temporal
    )


def evaluate_complaint_match(
    new_text_embedding,
    existing_text_embedding,
    new_lat: float,
    new_lon: float,
    new_time: datetime,
    existing_lat: float,
    existing_lon: float,
    existing_time: datetime,
    category: str,
) -> dict:
    sem_raw = cosine_similarity(new_text_embedding, existing_text_embedding)
    sem = normalize_score(sem_raw)
    distance = haversine_distance_meters(new_lat, new_lon, existing_lat, existing_lon)
    spat = spatial_score(distance, category)
    temp = temporal_score(new_time, existing_time, category)
    combined = compute_combined_score(sem, spat, temp)

    recommendation = "no_match"
    if combined >= settings.combined_score_threshold and sem >= settings.semantic_similarity_threshold:
        recommendation = "possible_match"
    elif combined >= 0.4:
        recommendation = "weak_match"

    return {
        "semantic_score": round(sem, 4),
        "spatial_score": round(spat, 4),
        "temporal_score": round(temp, 4),
        "combined_score": round(combined, 4),
        "distance_meters": round(distance, 1),
        "recommendation": recommendation,
        "review_status": "pending",
    }
