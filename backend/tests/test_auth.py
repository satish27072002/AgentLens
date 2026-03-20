"""Tests for auth endpoints — signup, login, profile."""


def test_signup(client):
    """Signup should create user and return JWT + API key."""
    response = client.post("/api/auth/signup", json={
        "email": "new@example.com",
        "password": "securepass123",
        "name": "New User",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"]
    assert data["token"]
    assert data["api_key"]
    assert data["api_key"].startswith("al_")


def test_signup_duplicate_email(client):
    """Signing up with an existing email should return 409."""
    client.post("/api/auth/signup", json={
        "email": "dupe@example.com",
        "password": "securepass123",
    })
    response = client.post("/api/auth/signup", json={
        "email": "dupe@example.com",
        "password": "anotherpass123",
    })
    assert response.status_code == 409


def test_signup_short_password(client):
    """Password under 8 characters should return 400."""
    response = client.post("/api/auth/signup", json={
        "email": "short@example.com",
        "password": "abc",
    })
    assert response.status_code == 400


def test_login(client):
    """Login with correct credentials should return JWT."""
    # First signup
    client.post("/api/auth/signup", json={
        "email": "login@example.com",
        "password": "securepass123",
    })
    # Then login
    response = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "securepass123",
    })
    assert response.status_code == 200
    assert response.json()["token"]


def test_login_wrong_password(client):
    """Login with wrong password should return 401."""
    client.post("/api/auth/signup", json={
        "email": "wrong@example.com",
        "password": "securepass123",
    })
    response = client.post("/api/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Login with non-existent email should return 401."""
    response = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "anything",
    })
    assert response.status_code == 401


def test_get_me(client, auth_headers):
    """GET /api/auth/me with valid token should return user profile."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"


def test_get_me_no_token(client):
    """GET /api/auth/me without token should return 422 (missing header)."""
    response = client.get("/api/auth/me")
    assert response.status_code == 422


def test_get_me_invalid_token(client):
    """GET /api/auth/me with bad token should return 401."""
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert response.status_code == 401
