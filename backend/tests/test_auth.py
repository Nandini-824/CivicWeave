from tests.conftest import auth_header


def test_citizen_registration(client):
    res = client.post("/api/auth/register", json={
        "full_name": "New Citizen",
        "email": "new@test.com",
        "password": "securepass123",
    })
    assert res.status_code == 200
    assert res.json()["email"] == "new@test.com"
    assert res.json()["role"] == "citizen"


def test_login_success(client, citizen_user):
    res = client.post("/api/auth/login", data={
        "username": "citizen@test.com",
        "password": "password123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client, citizen_user):
    res = client.post("/api/auth/login", data={
        "username": "citizen@test.com",
        "password": "wrongpassword",
    })
    assert res.status_code == 401


def test_unauthorized_access(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_role_based_access(client, citizen_user, officer_user):
    citizen_headers = auth_header(client, "citizen@test.com", "password123")
    res = client.get("/api/officer/dashboard", headers=citizen_headers)
    assert res.status_code == 403

    officer_headers = auth_header(client, "officer@test.com", "password123")
    res = client.get("/api/officer/dashboard", headers=officer_headers)
    assert res.status_code == 200


def test_get_me(client, citizen_user):
    headers = auth_header(client, "citizen@test.com", "password123")
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "citizen@test.com"
