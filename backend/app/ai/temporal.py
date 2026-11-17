"""Temporal verification for complaint timestamps."""

from datetime import datetime, timezone
from app.config import get_settings

settings = get_settings()

CATEGORY_TEMPORAL_WINDOWS = {
    "Street Lighting": 14,
    "Roads and Potholes": 21,
    "Water Supply": 7,
    "Drainage and Sewage": 7,
    "Garbage and Sanitation": 5,
    "Electricity": 7,
    "Public Infrastructure": 14,
    "Other": 7,
}


def get_temporal_window_days(category: str) -> int:
    return CATEGORY_TEMPORAL_WINDOWS.get(category, settings.default_temporal_window_days)


def time_difference_hours(ts1: datetime, ts2: datetime) -> float:
    if ts1.tzinfo is None:
        ts1 = ts1.replace(tzinfo=timezone.utc)
    if ts2.tzinfo is None:
        ts2 = ts2.replace(tzinfo=timezone.utc)
    return abs((ts1 - ts2).total_seconds()) / 3600


def temporal_score(ts1: datetime, ts2: datetime, category: str) -> float:
    """Score 1.0 at same time, decays to 0 at window limit."""
    window_days = get_temporal_window_days(category)
    window_hours = window_days * 24
    diff_hours = time_difference_hours(ts1, ts2)
    if diff_hours >= window_hours:
        return 0.0
    return 1.0 - (diff_hours / window_hours)
