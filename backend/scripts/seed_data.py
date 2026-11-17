"""
Seed CivicWeave with fictional development data.

Usage (from backend/):
    python -m scripts.seed_data
    python -m scripts.seed_data --reset
"""

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole, OfficerAssignment
from app.models.department import Department, Jurisdiction
from app.models.complaint import Complaint, ComplaintAnalysis, ComplaintStatus, CATEGORY_DEPARTMENT_MAP, ComplaintCategory
from app.models.incident import (
    Incident, IncidentComplaint, IncidentSupport, LinkStatus,
    IncidentStatus, PriorityAssessment, StatusHistory,
)
from app.models.notification import Notification
from app.security.auth import get_password_hash
from app.ai.classifier import classify_complaint
from app.ai.embeddings import generate_embedding, embedding_to_json
from app.ai.incident_linker import evaluate_complaint_match
from app.ai.priority_engine import estimate_priority
from app.services.number_generator import generate_complaint_number, generate_incident_number
from app.services.status_service import record_status_change

# Sample City center (Pune, India — fictional demo coordinates)
CITY = "Sample City"
ABC_CHOWK = (18.5310, 73.8446)
XYZ_NAGAR = (18.5074, 73.8077)
MARKET_ROAD = (18.5280, 73.8475)
STATION_AREA = (18.5325, 73.8740)

DEPARTMENTS = [
    ("Road Maintenance", "Roads, potholes, and pavement issues"),
    ("Water Supply", "Water pipes, leaks, and supply disruptions"),
    ("Drainage and Sewage", "Drainage and sewer infrastructure"),
    ("Sanitation", "Garbage collection and sanitation"),
    ("Street Lighting", "Street lights and public lighting"),
]

ROAD_DAMAGE_COMPLAINTS = [
    ("Large pothole near ABC Chowk", "There is a large pothole near ABC Chowk that has caused several accidents over the last three days."),
    ("Road surface badly damaged at ABC Chowk", "The road at ABC Chowk is badly damaged. Vehicles are struggling to pass safely."),
    ("Dangerous hole in road near ABC signal", "Vehicles are struggling because of a broken road near ABC Chowk signal."),
    ("Huge pothole blocking traffic at ABC Chowk", "A huge pothole near ABC Chowk is blocking one lane of traffic."),
    ("Cracked asphalt near ABC Chowk junction", "The asphalt is cracked and sinking near ABC Chowk junction."),
]

WATER_LEAK_COMPLAINTS = [
    ("Water pipe leaking near Market Road", "Continuous water flowing from a broken pipeline near Market Road."),
    ("Water supply pipe burst near the market", "Water supply pipe burst near the market area causing flooding."),
    ("Broken pipeline on Market Road", "A broken water pipeline is wasting water on Market Road since morning."),
]

XYZ_POTHOLE = [
    ("Pothole near XYZ Nagar", "There is a deep pothole near XYZ Nagar main gate."),
    ("Road damage at XYZ Nagar", "The road surface is damaged at XYZ Nagar entrance."),
]

OTHER_COMPLAINTS = [
    ("Streetlight not working on Station Road", "The streetlight on Station Road has been off for a week.", "Street Lighting", STATION_AREA),
    ("Garbage overflow near bus stand", "Garbage bins are overflowing near the central bus stand.", "Garbage and Sanitation", (18.5204, 73.8567)),
    ("Blocked drain on MG Road", "Drain is blocked causing water stagnation on MG Road.", "Drainage and Sewage", (18.5190, 73.8520)),
    ("Power outage in Sector 5", "No electricity in Sector 5 since yesterday evening.", "Electricity", (18.5150, 73.8600)),
    ("Broken footpath near park", "Public footpath tiles are broken near the city park.", "Public Infrastructure", (18.5250, 73.8500)),
    ("Sewage smell from manhole", "Strong sewage smell coming from an open manhole on Lake Road.", "Drainage and Sewage", (18.5180, 73.8480)),
    ("Water shortage in Block C", "No water supply in Block C for two days.", "Water Supply", (18.5220, 73.8550)),
    ("Flickering street lights", "Multiple street lights flickering on Ring Road.", "Street Lighting", (18.5100, 73.8650)),
]


def reset_database(db):
    """Drop and recreate all tables."""
    db.close()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            conn.commit()
    except Exception:
        pass
    return SessionLocal()


def seed_departments(db):
    depts = {}
    for name, desc in DEPARTMENTS:
        d = Department(name=name, description=desc, is_active=True)
        db.add(d)
        db.flush()
        depts[name] = d
    return depts


def seed_jurisdictions(db, depts):
    j1 = Jurisdiction(
        name="Central Zone",
        center_latitude=ABC_CHOWK[0],
        center_longitude=ABC_CHOWK[1],
        radius_meters=5000,
        department_id=depts["Road Maintenance"].id,
    )
    j2 = Jurisdiction(
        name="Market Zone",
        center_latitude=MARKET_ROAD[0],
        center_longitude=MARKET_ROAD[1],
        radius_meters=4000,
        department_id=depts["Water Supply"].id,
    )
    db.add_all([j1, j2])
    db.flush()
    return j1, j2


def seed_users(db, depts, j1, j2):
    admin = User(
        full_name="Super Admin",
        email="admin@civicweave.demo",
        password_hash=get_password_hash("admin123"),
        role=UserRole.admin,
    )
    db.add(admin)
    db.flush()

    officers = []
    officer_data = [
        ("Rajesh Kumar", "officer.roads@civicweave.demo", "Road Maintenance", j1.id),
        ("Priya Sharma", "officer.water@civicweave.demo", "Water Supply", j2.id),
        ("Amit Patel", "officer.sanitation@civicweave.demo", "Sanitation", j1.id),
    ]
    for name, email, dept_name, jur_id in officer_data:
        o = User(
            full_name=name,
            email=email,
            password_hash=get_password_hash("officer123"),
            role=UserRole.officer,
        )
        db.add(o)
        db.flush()
        db.add(OfficerAssignment(officer_id=o.id, department_id=depts[dept_name].id, jurisdiction_id=jur_id))
        officers.append(o)

    citizens = []
    for i in range(1, 31):
        c = User(
            full_name=f"Citizen {i:02d}",
            email=f"citizen{i:02d}@demo.local",
            password_hash=get_password_hash("citizen123"),
            role=UserRole.citizen,
            phone=f"98765{i:05d}",
        )
        db.add(c)
        citizens.append(c)
    db.flush()
    return admin, officers, citizens


def _dept_for_category(db, category: str):
    for cat_enum, dept_name in CATEGORY_DEPARTMENT_MAP.items():
        if cat_enum.value == category:
            return db.query(Department).filter(Department.name == dept_name).first()
    return None


def _add_complaint_with_analysis(
    db, citizen_id, title, description, lat, lon, created_at, category=None, dept=None,
):
    classification = classify_complaint(title, description)
    if category:
        classification["category"] = category
    if not dept:
        dept = _dept_for_category(db, classification["category"])

    complaint = Complaint(
        complaint_number=generate_complaint_number(db),
        citizen_id=citizen_id,
        title=title,
        description=description,
        category=classification["category"],
        suggested_department_id=dept.id if dept else None,
        assigned_department_id=dept.id if dept else None,
        latitude=lat,
        longitude=lon,
        address=f"Near {title.split()[-1] if title else 'location'}",
        city=CITY,
        status=ComplaintStatus.submitted.value,
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(complaint)
    db.flush()

    text_content = f"{title}. {description}"
    embedding = generate_embedding(text_content)
    db.add(ComplaintAnalysis(
        complaint_id=complaint.id,
        predicted_category=classification["category"],
        prediction_method=classification["method"],
        classification_confidence=classification["confidence"],
        embedding_reference=embedding_to_json(embedding),
        analyzed_at=created_at,
    ))
    record_status_change(db, "complaint", complaint.id, None, ComplaintStatus.submitted.value, citizen_id, "Complaint submitted")
    return complaint, embedding


def _create_incident_from_complaints(db, complaints, title, description, category, dept, base_time):
    lat = sum(c.latitude for c in complaints) / len(complaints)
    lon = sum(c.longitude for c in complaints) / len(complaints)
    first = min(c.created_at for c in complaints)
    last = max(c.created_at for c in complaints)

    incident = Incident(
        incident_number=generate_incident_number(db),
        title=title,
        description=description,
        category=category,
        department_id=dept.id if dept else None,
        center_latitude=lat,
        center_longitude=lon,
        first_reported_at=first,
        last_reported_at=last,
        status=IncidentStatus.under_review.value,
    )
    db.add(incident)
    db.flush()

    db.flush()
    for complaint in complaints:
        db.refresh(complaint)

    for i, complaint in enumerate(complaints):
        ref = complaints[0]
        if complaint.id != ref.id and ref.analysis and complaint.analysis:
            from app.ai.embeddings import embedding_from_json
            emb_new = embedding_from_json(complaint.analysis.embedding_reference)
            emb_ref = embedding_from_json(ref.analysis.embedding_reference)
            match = evaluate_complaint_match(
                emb_new, emb_ref,
                complaint.latitude, complaint.longitude, complaint.created_at,
                ref.latitude, ref.longitude, ref.created_at,
                category,
            )
            link_status = LinkStatus.pending.value if i > 0 else LinkStatus.confirmed.value
        else:
            match = {"semantic_score": 1.0, "spatial_score": 1.0, "temporal_score": 1.0, "combined_score": 1.0}
            link_status = LinkStatus.confirmed.value

        db.add(IncidentComplaint(
            incident_id=incident.id,
            complaint_id=complaint.id,
            semantic_score=match["semantic_score"],
            spatial_score=match["spatial_score"],
            temporal_score=match["temporal_score"],
            combined_score=match["combined_score"],
            link_status=link_status,
        ))

    unique_reporters = len(set(c.citizen_id for c in complaints))
    unresolved_days = max(0, (datetime.now(timezone.utc) - first.replace(tzinfo=timezone.utc if first.tzinfo is None else first.tzinfo)).days)
    result = estimate_priority(
        related_complaints=len(complaints),
        unique_reporters=unique_reporters,
        support_count=0,
        unresolved_days=unresolved_days,
        category=category,
        descriptions=[c.description for c in complaints],
    )
    incident.recommended_priority = result["recommended_priority"]
    incident.approved_priority = result["recommended_priority"]
    db.add(PriorityAssessment(
        incident_id=incident.id,
        recommended_priority=result["recommended_priority"],
        factor_scores=result["factor_scores"],
        explanation=result["explanation"],
        model_version=result["model_version"],
    ))
    record_status_change(db, "incident", incident.id, None, IncidentStatus.under_review.value, None, "Incident created from seed data")
    return incident


def seed_complaints_and_incidents(db, citizens, depts):
    now = datetime.now(timezone.utc)
    base = now - timedelta(days=5)
    all_complaints = []

    # Scenario 1: Road damage at ABC Chowk (5 complaints, same incident)
    road_complaints = []
    dept = depts["Road Maintenance"]
    for i, (title, desc) in enumerate(ROAD_DAMAGE_COMPLAINTS):
        citizen = citizens[i % len(citizens)]
        ts = base + timedelta(hours=i * 4)
        lat = ABC_CHOWK[0] + random.uniform(-0.0003, 0.0003)
        lon = ABC_CHOWK[1] + random.uniform(-0.0003, 0.0003)
        c, _ = _add_complaint_with_analysis(db, citizen.id, title, desc, lat, lon, ts, "Roads and Potholes", dept)
        road_complaints.append(c)
        all_complaints.append(c)

    _create_incident_from_complaints(
        db, road_complaints,
        "Road Damage Near ABC Chowk",
        "Multiple reports of road damage and potholes near ABC Chowk junction.",
        "Roads and Potholes", dept, base,
    )

    # Scenario 2: Water leakage at Market Road (3 complaints)
    water_complaints = []
    dept = depts["Water Supply"]
    for i, (title, desc) in enumerate(WATER_LEAK_COMPLAINTS):
        citizen = citizens[(i + 5) % len(citizens)]
        ts = base + timedelta(days=1, hours=i * 3)
        lat = MARKET_ROAD[0] + random.uniform(-0.0002, 0.0002)
        lon = MARKET_ROAD[1] + random.uniform(-0.0002, 0.0002)
        c, _ = _add_complaint_with_analysis(db, citizen.id, title, desc, lat, lon, ts, "Water Supply", dept)
        water_complaints.append(c)
        all_complaints.append(c)

    _create_incident_from_complaints(
        db, water_complaints,
        "Water Leakage Near Market Road",
        "Water pipeline leak reported by multiple citizens near Market Road.",
        "Water Supply", dept, base,
    )

    # Scenario 3: Separate pothole at XYZ Nagar (must NOT link to ABC Chowk)
    xyz_complaints = []
    for i, (title, desc) in enumerate(XYZ_POTHOLE):
        citizen = citizens[(i + 10) % len(citizens)]
        ts = base + timedelta(days=2, hours=i * 6)
        lat = XYZ_NAGAR[0] + random.uniform(-0.0002, 0.0002)
        lon = XYZ_NAGAR[1] + random.uniform(-0.0002, 0.0002)
        c, _ = _add_complaint_with_analysis(db, citizen.id, title, desc, lat, lon, ts, "Roads and Potholes", depts["Road Maintenance"])
        xyz_complaints.append(c)
        all_complaints.append(c)

    _create_incident_from_complaints(
        db, xyz_complaints,
        "Road Damage Near XYZ Nagar",
        "Pothole reports from XYZ Nagar area — geographically distinct from ABC Chowk.",
        "Roads and Potholes", depts["Road Maintenance"], base,
    )

    # Additional standalone complaints to reach 60+
    extra_templates = [
        ("Broken streetlight on Main Street", "Street light pole is broken and dark at night.", "Street Lighting"),
        ("Garbage not collected for 3 days", "Garbage bins overflowing on Park Lane.", "Garbage and Sanitation"),
        ("Open manhole without cover", "Dangerous open manhole on Temple Road.", "Drainage and Sewage"),
        ("Water logging after rain", "Water stagnation on College Road after rainfall.", "Drainage and Sewage"),
        ("Damaged speed bump", "Speed bump crumbling on School Road.", "Roads and Potholes"),
        ("Low water pressure", "Very low water pressure in Housing Society B.", "Water Supply"),
        ("Fallen electric wire", "Loose electric wire hanging near shop.", "Electricity"),
        ("Missing drain cover", "Drain cover missing on Bridge Road.", "Drainage and Sewage"),
        ("Uncollected waste near clinic", "Medical waste mixed with garbage near clinic.", "Garbage and Sanitation"),
        ("Faded road markings", "Zebra crossing markings faded on Highway Road.", "Roads and Potholes"),
    ]

    for idx, (title, desc, cat) in enumerate(extra_templates):
        for j in range(3):
            citizen = citizens[(idx * 3 + j + 15) % len(citizens)]
            ts = base + timedelta(days=random.randint(0, 4), hours=random.randint(0, 12))
            lat = 18.5204 + random.uniform(-0.015, 0.015)
            lon = 73.8567 + random.uniform(-0.015, 0.015)
            c, _ = _add_complaint_with_analysis(db, citizen.id, title, desc, lat, lon, ts, cat)
            all_complaints.append(c)
            dept = _dept_for_category(db, cat)
            inc = Incident(
                incident_number=generate_incident_number(db),
                title=title,
                description=desc,
                category=cat,
                department_id=dept.id if dept else None,
                center_latitude=lat,
                center_longitude=lon,
                first_reported_at=ts,
                last_reported_at=ts,
                status=random.choice([IncidentStatus.under_review.value, IncidentStatus.in_progress.value, IncidentStatus.submitted.value]),
                recommended_priority=random.choice(["Low", "Medium", "High"]),
                approved_priority=random.choice(["Low", "Medium", "High"]),
            )
            db.add(inc)
            db.flush()
            db.add(IncidentComplaint(
                incident_id=inc.id, complaint_id=c.id,
                semantic_score=1.0, spatial_score=1.0, temporal_score=1.0, combined_score=1.0,
                link_status=LinkStatus.confirmed.value,
            ))

    for title, desc, cat, coords in OTHER_COMPLAINTS:
        citizen = random.choice(citizens)
        ts = base + timedelta(days=random.randint(1, 4))
        c, _ = _add_complaint_with_analysis(db, citizen.id, title, desc, coords[0], coords[1], ts, cat)
        all_complaints.append(c)

    db.commit()
    return len(all_complaints)


def main():
    parser = argparse.ArgumentParser(description="Seed CivicWeave demo data")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before seeding")
    args = parser.parse_args()

    print("CivicWeave Seed Script — Fictional Development Data")
    print("=" * 50)

    db = SessionLocal()
    if args.reset:
        print("Resetting database...")
        db = reset_database(db)

    print("Creating departments...")
    depts = seed_departments(db)
    j1, j2 = seed_jurisdictions(db, depts)
    print("Creating users...")
    admin, officers, citizens = seed_users(db, depts, j1, j2)
    print("Creating complaints and incidents (this may take a minute for AI embeddings)...")
    count = seed_complaints_and_incidents(db, citizens, depts)

    print("\nSeed complete!")
    print(f"  Complaints: {count}+")
    print(f"  Citizens: 30")
    print(f"  Officers: 3")
    print(f"  Admin: 1")
    print("\nDemo accounts:")
    print("  Admin:    admin@civicweave.demo / admin123")
    print("  Officer:  officer.roads@civicweave.demo / officer123")
    print("  Citizen:  citizen01@demo.local / citizen123")
    print("\nKey demo scenario: Submit a pothole complaint near ABC Chowk (18.5310, 73.8446)")
    print("  to see incident linking with existing road damage reports.")

    db.close()


if __name__ == "__main__":
    main()
