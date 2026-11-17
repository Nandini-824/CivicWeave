from unittest.mock import patch
import numpy as np
from datetime import datetime, timezone
from tests.conftest import auth_header

MOCK_EMBEDDING = np.random.rand(384).astype(np.float32)


@patch("app.services.complaint_service.generate_embedding", side_effect=lambda *a, **k: MOCK_EMBEDDING)
def test_incident_created_on_complaint(mock_emb, client, citizen_user, departments, db):
    headers = auth_header(client, "citizen@test.com", "password123")
    client.post("/api/complaints", json={
        "title": "Broken streetlight on Main",
        "description": "Street light has been off for several days on Main Street.",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "address": "Main Street",
        "city": "Sample City",
    }, headers=headers)

    from app.models.incident import Incident
    incidents = db.query(Incident).all()
    assert len(incidents) >= 1


@patch("app.services.complaint_service.generate_embedding", side_effect=lambda *a, **k: MOCK_EMBEDDING)
def test_officer_confirm_link(mock_emb, client, citizen_user, officer_user, departments, db):
    from app.models.complaint import Complaint
    from app.models.incident import Incident, IncidentComplaint, LinkStatus

    headers = auth_header(client, "citizen@test.com", "password123")
    client.post("/api/complaints", json={
        "title": "Water leak on Market Road",
        "description": "Continuous water flowing from broken pipeline on Market Road.",
        "latitude": 18.5280,
        "longitude": 73.8475,
        "address": "Market Road",
        "city": "Sample City",
    }, headers=headers)

    link = db.query(IncidentComplaint).first()
    assert link is not None

    officer_headers = auth_header(client, "officer@test.com", "password123")
    res = client.post(f"/api/officer/incident-links/{link.id}/confirm", headers=officer_headers)
    assert res.status_code == 200

    db.refresh(link)
    assert link.link_status == LinkStatus.confirmed.value


@patch("app.services.complaint_service.generate_embedding", side_effect=lambda *a, **k: MOCK_EMBEDDING)
def test_officer_reject_link(mock_emb, client, citizen_user, officer_user, departments, db):
    from app.models.incident import IncidentComplaint, LinkStatus

    headers = auth_header(client, "citizen@test.com", "password123")
    client.post("/api/complaints", json={
        "title": "Garbage overflow near park",
        "description": "Garbage bins overflowing near the city park for three days.",
        "latitude": 18.5250,
        "longitude": 73.8500,
        "address": "City Park",
        "city": "Sample City",
    }, headers=headers)

    link = db.query(IncidentComplaint).first()
    officer_headers = auth_header(client, "officer@test.com", "password123")
    client.post(f"/api/officer/incident-links/{link.id}/reject", headers=officer_headers)
    db.refresh(link)
    assert link.link_status == LinkStatus.rejected.value


@patch("app.services.complaint_service.generate_embedding", side_effect=lambda *a, **k: MOCK_EMBEDDING)
def test_duplicate_support_prevention(mock_emb, client, citizen_user, departments, db):
    headers = auth_header(client, "citizen@test.com", "password123")
    client.post("/api/complaints", json={
        "title": "Drain blocked on Lake Road",
        "description": "Drain is completely blocked causing water stagnation on Lake Road.",
        "latitude": 18.5180,
        "longitude": 73.8480,
        "address": "Lake Road",
        "city": "Sample City",
    }, headers=headers)

    from app.models.incident import Incident
    incident = db.query(Incident).first()
    res = client.post(f"/api/incidents/{incident.id}/support", headers=headers)
    assert res.status_code == 200
    res = client.post(f"/api/incidents/{incident.id}/support", headers=headers)
    assert res.status_code == 400
