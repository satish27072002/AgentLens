"""
Pytest configuration — shared test fixtures.

Provides:
- db_session: Fresh in-memory database for each test
- client: FastAPI TestClient wired to the test database
- auth_headers: JWT token headers for a pre-created test user
- api_key_headers: API key headers for SDK endpoints
- test_user: A pre-created user for tests that need one
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, ApiKey
from app.auth import hash_password, create_jwt_token, generate_api_key


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """FastAPI TestClient using the test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user and return (user, api_key_value)."""
    user_id = str(uuid.uuid4())
    api_key_value = generate_api_key()

    user = User(
        id=user_id,
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        name="Test User",
    )
    db_session.add(user)

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user_id,
        key_value=api_key_value,
        name="Test Key",
    )
    db_session.add(api_key)
    db_session.commit()

    return user, api_key_value


@pytest.fixture
def auth_headers(test_user):
    """JWT Authorization headers for the test user."""
    user, _ = test_user
    token = create_jwt_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api_key_headers(test_user):
    """API key headers for SDK endpoints."""
    _, api_key_value = test_user
    return {"X-API-Key": api_key_value}
