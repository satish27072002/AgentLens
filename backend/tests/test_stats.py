"""Tests for GET /api/stats — now requires JWT auth."""


def _post_trace(client, api_key_headers, exec_id, status="completed", cost=0.002, duration_ms=3000):
    """Helper to create a trace."""
    client.post("/api/traces", json={
        "id": exec_id,
        "agent_name": "StatsTestAgent",
        "status": status,
        "started_at": "2026-03-20T10:00:00",
        "duration_ms": duration_ms,
        "total_cost": cost,
        "total_tokens": 300,
    }, headers=api_key_headers)


def test_stats_empty_database(client, auth_headers):
    """Stats on empty database should return zeroes."""
    response = client.get("/api/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_executions"] == 0
    assert data["total_cost"] == 0.0
    assert data["success_rate"] == 0.0


def test_stats_with_data(client, auth_headers, api_key_headers):
    """Stats should reflect the current user's data."""
    _post_trace(client, api_key_headers, "s1", cost=0.01, duration_ms=2000)
    _post_trace(client, api_key_headers, "s2", cost=0.02, duration_ms=4000)
    _post_trace(client, api_key_headers, "s3", status="failed", cost=0.005, duration_ms=1000)

    response = client.get("/api/stats", headers=auth_headers)
    data = response.json()

    assert data["total_executions"] == 3
    assert data["total_cost"] == 0.035
    assert 2333 <= data["avg_duration_ms"] <= 2334
    assert 66.6 <= data["success_rate"] <= 66.8
