"""
Tests for auth endpoints — profile and JIT provisioning.

With Auth0, we no longer have signup/login endpoints.
Instead we test:
1. GET /api/auth/me returns profile for authenticated users
2. JIT provisioning auto-creates users on first API call
3. Invalid/missing tokens are rejected
4. GET /api/auth/api-key returns the first API key
"""


def test_get_me(client, test_user, auth_headers):
    """GET /api/auth/me with valid Auth0 token should return user profile."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"


def test_get_me_jit_provisioning(client, auth_headers):
    """First API call with a new Auth0 user should auto-create the user."""
    # No test_user fixture — user doesn't exist yet
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert data["id"]  # Should have been auto-created


def test_get_me_no_token(client):
    """GET /api/auth/me without token should return 422 (missing header)."""
    response = client.get("/api/auth/me")
    assert response.status_code == 422


def test_get_me_invalid_token(client):
    """GET /api/auth/me with bad token should return 401."""
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401


def test_get_first_api_key(client, test_user, auth_headers):
    """GET /api/auth/api-key should return the user's first API key."""
    response = client.get("/api/auth/api-key", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["api_key"]
    assert data["api_key"].startswith("al_")


def test_jit_creates_api_key(client, auth_headers, db_session):
    """JIT provisioning should auto-create an API key for new users."""
    from app.models import ApiKey

    # First call — triggers JIT
    client.get("/api/auth/me", headers=auth_headers)

    # Check that an API key was created
    response = client.get("/api/auth/api-key", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["api_key"].startswith("al_")
