"""
Pytest configuration — shared test fixtures.

Provides:
- db_session: Fresh in-memory database for each test
- client: FastAPI TestClient wired to the test database + mocked Auth0
- auth_headers: Auth0 JWT headers for a pre-created test user
- api_key_headers: API key headers for SDK endpoints
- test_user: A pre-created user for tests that need one

Auth0 mocking:
In tests, we mock verify_auth0_token() to skip the real Auth0 call.
Instead, it returns a fake payload with the test user's auth0_sub.
This lets all tests run without internet access or Auth0 credentials.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import User, ApiKey
from app.auth import generate_api_key


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Fake Auth0 sub for test users
TEST_AUTH0_SUB = "auth0|test123"
TEST_AUTH0_TOKEN = "fake-auth0-token-for-tests"


def _mock_verify_auth0_token(token: str) -> dict:
    """
    Mock Auth0 token verification for tests.

    Returns a fake payload as if Auth0 had verified the token.
    The 'sub' matches the test user's auth0_sub.
    """
    if token == TEST_AUTH0_TOKEN:
        return {
            "sub": TEST_AUTH0_SUB,
            "email": "test@example.com",
            "name": "Test User",
        }
    # For multi-tenancy tests — a second user
    if token == "fake-auth0-token-user-2":
        return {
            "sub": "auth0|user2",
            "email": "user2@example.com",
            "name": "User Two",
        }
    from app.auth0 import Auth0Error
    raise Auth0Error("Invalid test token")


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
    """FastAPI TestClient using the test database + mocked Auth0."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock Auth0 verification so tests don't need real Auth0 tokens
    with patch("app.dependencies.verify_auth0_token", side_effect=_mock_verify_auth0_token):
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
        auth0_sub=TEST_AUTH0_SUB,
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
def auth_headers():
    """Auth0 JWT Authorization headers for the test user."""
    return {"Authorization": f"Bearer {TEST_AUTH0_TOKEN}"}


@pytest.fixture
def api_key_headers(test_user):
    """API key headers for SDK endpoints."""
    _, api_key_value = test_user
    return {"X-API-Key": api_key_value}
