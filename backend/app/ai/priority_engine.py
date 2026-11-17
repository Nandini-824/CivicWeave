"""Explainable rule-based priority estimation engine."""

import json
from datetime import datetime, timezone


PRIORITY_LEVELS = ["Low", "Medium", "High", "Critical"]


def estimate_priority(
    related_complaints: int,
    unique_reporters: int,
    support_count: int,
    unresolved_days: int,
    category: str,
    descriptions: list[str],
) -> dict:
    score = 0
    factors = []

    if related_complaints >= 10:
        score += 30
        factors.append(f"{related_complaints} related complaints have been recorded.")
    elif related_complaints >= 5:
        score += 20
        factors.append(f"{related_complaints} related complaints have been recorded.")
    elif related_complaints >= 2:
        score += 10
        factors.append(f"{related_complaints} related complaints have been recorded.")

    if unique_reporters >= 8:
        score += 25
        factors.append(f"{unique_reporters} unique citizens reported the problem.")
    elif unique_reporters >= 4:
        score += 15
        factors.append(f"{unique_reporters} unique citizens reported the problem.")
    elif unique_reporters >= 2:
        score += 8
        factors.append(f"{unique_reporters} unique citizens reported the problem.")

    if support_count >= 5:
        score += 10
        factors.append(f"{support_count} citizens have expressed support for this incident.")

    if unresolved_days >= 14:
        score += 25
        factors.append(f"The incident has remained unresolved for {unresolved_days} days.")
    elif unresolved_days >= 7:
        score += 15
        factors.append(f"The incident has remained unresolved for {unresolved_days} days.")
    elif unresolved_days >= 3:
        score += 8
        factors.append(f"The incident has remained unresolved for {unresolved_days} days.")

    safety_keywords = ["dangerous", "accident", "injury", "unsafe", "hazard", "emergency", "critical"]
    combined_text = " ".join(descriptions).lower()
    if any(kw in combined_text for kw in safety_keywords):
        score += 15
        factors.append("Complaint descriptions indicate possible safety risks.")

    if category in ("Roads and Potholes", "Electricity", "Water Supply") and related_complaints >= 3:
        score += 5

    if score >= 60:
        priority = "Critical"
    elif score >= 40:
        priority = "High"
    elif score >= 20:
        priority = "Medium"
    else:
        priority = "Low"

    explanation = f"Priority: {priority.upper()}\n\nContributing Factors:\n\n"
    explanation += "\n".join(f"• {f}" for f in factors) if factors else "• Limited data available for priority assessment."

    return {
        "recommended_priority": priority,
        "factor_scores": json.dumps({"total_score": score}),
        "explanation": explanation,
        "model_version": "rule_based_v1",
    }
