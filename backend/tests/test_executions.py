"""Tests for GET /api/executions — now requires JWT auth + filters by user."""


def _post_trace(client, api_key_headers, exec_id, agent_name="TestAgent", status="completed"):
    """Helper to create a trace for testing."""
    client.post("/api/traces", json={
        "id": exec_id,
        "agent_name": agent_name,
        "status": status,
        "started_at": "2026-03-20T10:00:00",
        "duration_ms": 3000,
        "total_cost": 0.002,
        "total_tokens": 300,
        "llm_calls": [
            {
                "id": f"{exec_id}-llm",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "total_tokens": 300,
                "cost": 0.002,
                "duration_ms": 1000,
            }
        ],
        "tool_calls": [
            {
                "id": f"{exec_id}-tool",
                "tool_name": "calculator",
                "duration_ms": 50,
                "status": "success",
            }
        ],
    }, headers=api_key_headers)


def test_list_executions_empty(client, auth_headers):
    """Empty database should return empty list."""
    response = client.get("/api/executions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["executions"] == []
    assert data["total"] == 0


def test_list_executions_with_data(client, auth_headers, api_key_headers):
    """Should return executions belonging to the current user."""
    _post_trace(client, api_key_headers, "exec-a")
    _post_trace(client, api_key_headers, "exec-b")

    response = client.get("/api/executions", headers=auth_headers)
    data = response.json()
    assert data["total"] == 2
    assert len(data["executions"]) == 2


def test_list_executions_pagination(client, auth_headers, api_key_headers):
    """Pagination should work correctly."""
    for i in range(5):
        _post_trace(client, api_key_headers, f"exec-{i}")

    response = client.get("/api/executions?skip=2&limit=2", headers=auth_headers)
    data = response.json()
    assert data["total"] == 5
    assert len(data["executions"]) == 2


def test_list_executions_filter_by_agent_name(client, auth_headers, api_key_headers):
    """Filtering by agent_name should return only matching executions."""
    _post_trace(client, api_key_headers, "exec-a", agent_name="AgentAlpha")
    _post_trace(client, api_key_headers, "exec-b", agent_name="AgentBeta")
    _post_trace(client, api_key_headers, "exec-c", agent_name="AgentAlpha")

    response = client.get("/api/executions?agent_name=AgentAlpha", headers=auth_headers)
    data = response.json()
    assert data["total"] == 2


def test_list_executions_filter_by_status(client, auth_headers, api_key_headers):
    """Filtering by status should return only matching executions."""
    _post_trace(client, api_key_headers, "exec-ok", status="completed")
    _post_trace(client, api_key_headers, "exec-fail", status="failed")

    response = client.get("/api/executions?status=failed", headers=auth_headers)
    data = response.json()
    assert data["total"] == 1
    assert data["executions"][0]["status"] == "failed"


def test_get_execution_detail(client, auth_headers, api_key_headers):
    """Detail endpoint should return execution with nested calls."""
    _post_trace(client, api_key_headers, "exec-detail")

    response = client.get("/api/executions/exec-detail", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "exec-detail"
    assert len(data["llm_calls"]) == 1
    assert len(data["tool_calls"]) == 1


def test_get_execution_not_found(client, auth_headers):
    """Requesting a non-existent execution should return 404."""
    response = client.get("/api/executions/does-not-exist", headers=auth_headers)
    assert response.status_code == 404


def test_no_auth_returns_error(client):
    """Requesting without auth should fail."""
    response = client.get("/api/executions")
    assert response.status_code == 422
