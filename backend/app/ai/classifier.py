"""Complaint classification module - rule-based fallback with optional TF-IDF model."""

import re
from app.models.complaint import ComplaintCategory, CATEGORY_DEPARTMENT_MAP

CATEGORY_KEYWORDS = {
    ComplaintCategory.roads_potholes: [
        "pothole", "road", "pavement", "asphalt", "crack", "damage", "hole",
        "street surface", "broken road", "road damage", "speed bump",
    ],
    ComplaintCategory.water_supply: [
        "water", "pipe", "leak", "leaking", "supply", "burst", "flowing",
        "pipeline", "tap", "drinking water", "no water",
    ],
    ComplaintCategory.drainage_sewage: [
        "drain", "drainage", "sewage", "sewer", "overflow", "blocked drain",
        "manhole", "stagnant water", "flooding",
    ],
    ComplaintCategory.garbage_sanitation: [
        "garbage", "trash", "waste", "sanitation", "dump", "litter",
        "rubbish", "bin", "collection", "filth",
    ],
    ComplaintCategory.street_lighting: [
        "streetlight", "street light", "lamp", "lighting", "dark", "bulb",
        "pole light", "not working light",
    ],
    ComplaintCategory.electricity: [
        "electricity", "power", "electrical", "wire", "transformer",
        "outage", "blackout", "cable", "short circuit",
    ],
    ComplaintCategory.public_infrastructure: [
        "bridge", "park", "bench", "public building", "footpath", "sidewalk",
        "infrastructure", "playground", "public toilet",
    ],
}


def preprocess_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def classify_complaint(title: str, description: str) -> dict:
    """
    Classify complaint using rule-based keyword matching.
    Returns method='rule_based' with confidence=null as specified.
    """
    combined = preprocess_text(f"{title} {description}")
    best_category = ComplaintCategory.other
    best_score = 0

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_category = category

    department_name = CATEGORY_DEPARTMENT_MAP.get(best_category, "General Administration")

    return {
        "category": best_category.value,
        "department": department_name,
        "confidence": None,
        "method": "rule_based",
    }
