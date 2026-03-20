"""Tests for the /health endpoint."""


def test_health_returns_ok(client):
    """Health endpoint should return 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "agentlens-backend"
