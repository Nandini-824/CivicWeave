from unittest.mock import patch
import numpy as np
from tests.conftest import auth_header


MOCK_EMBEDDING = np.random.rand(384).astype(np.float32)


def _mock_embedding(*args, **kwargs):
    return MOCK_EMBEDDING


@patch("app.services.complaint_service.generate_embedding", side_effect=_mock_embedding)
def test_complaint_submission(mock_emb, client, citizen_user, departments):
    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.post("/api/complaints", json={
        "title": "Large pothole near ABC Chowk",
        "description": "There is a dangerous pothole causing accidents near ABC Chowk.",
        "latitude": 18.5310,
        "longitude": 73.8446,
        "address": "ABC Chowk, Sample City",
        "city": "Sample City",
    }, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["complaint_number"].startswith("CW-")
    assert data["status"] == "Submitted"
    assert data["category"] == "Roads and Potholes"


@patch("app.services.complaint_service.generate_embedding", side_effect=_mock_embedding)
def test_missing_required_fields(mock_emb, client, citizen_user):
    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.post("/api/complaints", json={
        "title": "Hi",
        "description": "Short",
        "latitude": 18.5310,
        "longitude": 73.8446,
        "address": "ABC",
        "city": "Sample City",
    }, headers=headers)
    assert res.status_code == 422


@patch("app.services.complaint_service.generate_embedding", side_effect=_mock_embedding)
def test_invalid_coordinates(mock_emb, client, citizen_user):
    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.post("/api/complaints", json={
        "title": "Valid title here",
        "description": "Valid description with enough length here.",
        "latitude": 999,
        "longitude": 73.8446,
        "address": "ABC Chowk",
        "city": "Sample City",
    }, headers=headers)
    assert res.status_code == 422


@patch("app.services.complaint_service.generate_embedding", side_effect=_mock_embedding)
def test_complaint_ownership(mock_emb, client, citizen_user, departments, db):
    from app.models.user import User, UserRole
    from app.security.auth import get_password_hash

    other = User(
        full_name="Other Citizen",
        email="other@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.citizen,
    )
    db.add(other)
    db.commit()

    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.post("/api/complaints", json={
        "title": "Test complaint title",
        "description": "Test complaint description with sufficient length.",
        "latitude": 18.5310,
        "longitude": 73.8446,
        "address": "ABC Chowk",
        "city": "Sample City",
    }, headers=headers)
    complaint_id = res.json()["id"]

    other_headers = auth_header(client, "other@test.com", "password123")
    res = client.get(f"/api/complaints/{complaint_id}", headers=other_headers)
    assert res.status_code == 403


def test_image_upload_invalid_type(client, citizen_user):
    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.post(
        "/api/complaints/upload-image",
        files={"file": ("test.txt", b"not an image", "text/plain")},
        headers=headers,
    )
    assert res.status_code == 400
