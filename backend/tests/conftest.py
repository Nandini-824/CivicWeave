import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.models.department import Department
from app.security.auth import get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def departments(db):
    depts = [
        Department(name="Road Maintenance", description="Roads", is_active=True),
        Department(name="Water Supply", description="Water", is_active=True),
    ]
    for d in depts:
        db.add(d)
    db.commit()
    return depts


@pytest.fixture
def citizen_user(db):
    user = User(
        full_name="Test Citizen",
        email="citizen@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.citizen,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def officer_user(db, departments):
    from app.models.user import OfficerAssignment
    user = User(
        full_name="Test Officer",
        email="officer@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.officer,
    )
    db.add(user)
    db.flush()
    db.add(OfficerAssignment(officer_id=user.id, department_id=departments[0].id))
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db):
    user = User(
        full_name="Test Admin",
        email="admin@test.com",
        password_hash=get_password_hash("password123"),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_header(client, email, password):
    res = client.post("/api/auth/login", data={"username": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
