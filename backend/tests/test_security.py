from unittest.mock import patch
import numpy as np
from tests.conftest import auth_header

MOCK_EMBEDDING = np.random.rand(384).astype(np.float32)


def test_citizen_cannot_access_admin(client, citizen_user):
    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.get("/api/admin/dashboard", headers=headers)
    assert res.status_code == 403


def test_citizen_cannot_access_officer_endpoints(client, citizen_user):
    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.get("/api/officer/incidents", headers=headers)
    assert res.status_code == 403


@patch("app.services.complaint_service.generate_embedding", side_effect=lambda *a, **k: MOCK_EMBEDDING)
def test_officer_department_isolation(mock_emb, client, citizen_user, officer_user, departments, db):
    from app.models.user import User, UserRole, OfficerAssignment
    from app.security.auth import get_password_hash

    water_dept = departments[1]
    water_officer = User(
        full_name="Water Officer",
        email="water.officer@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.officer,
    )
    db.add(water_officer)
    db.flush()
    db.add(OfficerAssignment(officer_id=water_officer.id, department_id=water_dept.id))
    db.commit()

    citizen_headers = auth_header(client, "citizen@test.com", "password123")
    client.post("/api/complaints", json={
        "title": "Large pothole on Road A",
        "description": "Dangerous pothole on Road A needing immediate repair work.",
        "latitude": 18.5310,
        "longitude": 73.8446,
        "address": "Road A",
        "city": "Sample City",
    }, headers=citizen_headers)

    water_headers = auth_header(client, "water.officer@test.com", "password123")
    res = client.get("/api/officer/incidents", headers=water_headers)
    assert res.status_code == 200
    assert len(res.json()) == 0
