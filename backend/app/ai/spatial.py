"""Spatial verification using Haversine distance."""

import math
from app.config import get_settings

settings = get_settings()

CATEGORY_SPATIAL_RADIUS = {
    "Street Lighting": 150.0,
    "Roads and Potholes": 300.0,
    "Water Supply": 400.0,
    "Drainage and Sewage": 350.0,
    "Garbage and Sanitation": 250.0,
    "Electricity": 200.0,
    "Public Infrastructure": 300.0,
    "Other": 300.0,
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_spatial_radius(category: str) -> float:
    return CATEGORY_SPATIAL_RADIUS.get(category, settings.default_spatial_radius_meters)


def spatial_score(distance_meters: float, category: str) -> float:
    """Score 1.0 at 0m, decays to 0 at radius threshold."""
    radius = get_spatial_radius(category)
    if distance_meters >= radius:
        return 0.0
    return 1.0 - (distance_meters / radius)
