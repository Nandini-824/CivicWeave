import numpy as np
from datetime import datetime, timezone, timedelta
from app.ai.classifier import classify_complaint
from app.ai.spatial import haversine_distance_meters, spatial_score
from app.ai.temporal import temporal_score
from app.ai.similarity import cosine_similarity
from app.ai.incident_linker import evaluate_complaint_match


def test_classify_road_complaint():
    result = classify_complaint(
        "Large pothole near ABC Chowk",
        "The road is badly damaged with a dangerous hole.",
    )
    assert result["category"] == "Roads and Potholes"
    assert result["method"] == "rule_based"
    assert result["confidence"] is None


def test_classify_water_complaint():
    result = classify_complaint(
        "Water pipe leaking",
        "Continuous water flowing from broken pipeline near market.",
    )
    assert result["category"] == "Water Supply"


def test_semantic_similar_wording():
    from app.ai.embeddings import generate_embedding
    emb_a = generate_embedding("There is a huge pothole near ABC Chowk.")
    emb_b = generate_embedding("The road at ABC Chowk is badly damaged.")
    sim = cosine_similarity(emb_a, emb_b)
    assert sim > 0.3


def test_semantic_different_categories():
    from app.ai.embeddings import generate_embedding
    emb_a = generate_embedding("Street light not working on Main Road.")
    emb_b = generate_embedding("Water pipe burst near the market.")
    sim = cosine_similarity(emb_a, emb_b)
    assert sim < 0.6


def test_spatial_same_location():
    dist = haversine_distance_meters(18.5310, 73.8446, 18.5311, 73.8447)
    assert dist < 100
    score = spatial_score(dist, "Roads and Potholes")
    assert score > 0.5


def test_spatial_distant_locations():
    dist = haversine_distance_meters(18.5310, 73.8446, 18.5074, 73.8077)
    assert dist > 1000
    score = spatial_score(dist, "Roads and Potholes")
    assert score == 0.0


def test_temporal_close_times():
    t1 = datetime.now(timezone.utc)
    t2 = t1 + timedelta(hours=4)
    score = temporal_score(t1, t2, "Roads and Potholes")
    assert score > 0.5


def test_temporal_far_apart():
    t1 = datetime.now(timezone.utc)
    t2 = t1 - timedelta(days=60)
    score = temporal_score(t1, t2, "Garbage and Sanitation")
    assert score == 0.0


def test_combined_match_same_incident():
    from app.ai.embeddings import generate_embedding
    emb_a = generate_embedding("There is a huge pothole near ABC Chowk.")
    emb_b = generate_embedding("Dangerous hole in road near ABC Chowk signal.")
    now = datetime.now(timezone.utc)
    result = evaluate_complaint_match(
        emb_a, emb_b,
        18.5310, 73.8446, now,
        18.5311, 73.8447, now - timedelta(hours=3),
        "Roads and Potholes",
    )
    assert result["recommendation"] in ("possible_match", "weak_match")
    assert result["combined_score"] > 0.4


def test_combined_no_match_distant():
    from app.ai.embeddings import generate_embedding
    emb_a = generate_embedding("Pothole near ABC Chowk.")
    emb_b = generate_embedding("Pothole near XYZ Nagar.")
    now = datetime.now(timezone.utc)
    result = evaluate_complaint_match(
        emb_a, emb_b,
        18.5310, 73.8446, now,
        18.5074, 73.8077, now,
        "Roads and Potholes",
    )
    assert result["spatial_score"] == 0.0
    assert result["recommendation"] != "possible_match"
