"""Tests for POST /api/traces — now requires API key auth."""


SAMPLE_TRACE = {
    "id": "test-exec-001",
    "agent_name": "TestAgent",
    "status": "completed",
    "started_at": "2026-03-20T10:00:00",
    "completed_at": "2026-03-20T10:00:05",
    "duration_ms": 5000,
    "total_cost": 0.0035,
    "total_tokens": 450,
    "llm_calls": [
        {
            "id": "test-llm-001",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt_tokens": 200,
            "completion_tokens": 250,
            "total_tokens": 450,
            "cost": 0.0035,
            "duration_ms": 1200,
            "timestamp": "2026-03-20T10:00:01",
        }
    ],
    "tool_calls": [
        {
            "id": "test-tool-001",
            "tool_name": "search_db",
            "duration_ms": 350,
            "status": "success",
            "timestamp": "2026-03-20T10:00:02",
        }
    ],
}


def test_create_trace(client, api_key_headers):
    """Posting a valid trace with API key should return 201."""
    response = client.post("/api/traces", json=SAMPLE_TRACE, headers=api_key_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ok"
    assert data["execution_id"] == "test-exec-001"


def test_create_trace_no_api_key(client):
    """Posting without an API key should return 422 (missing header)."""
    response = client.post("/api/traces", json=SAMPLE_TRACE)
    assert response.status_code == 422


def test_create_trace_invalid_api_key(client):
    """Posting with an invalid API key should return 401."""
    response = client.post("/api/traces", json=SAMPLE_TRACE, headers={"X-API-Key": "fake_key"})
    assert response.status_code == 401


def test_create_trace_duplicate(client, api_key_headers):
    """Posting the same trace twice should return 409."""
    client.post("/api/traces", json=SAMPLE_TRACE, headers=api_key_headers)
    response = client.post("/api/traces", json=SAMPLE_TRACE, headers=api_key_headers)
    assert response.status_code == 409


def test_create_trace_minimal(client, api_key_headers):
    """A trace with no LLM/tool calls should still work."""
    minimal = {
        "id": "test-minimal-001",
        "agent_name": "MinimalAgent",
        "started_at": "2026-03-20T12:00:00",
    }
    response = client.post("/api/traces", json=minimal, headers=api_key_headers)
    assert response.status_code == 201


def test_create_trace_missing_required_field(client, api_key_headers):
    """A trace missing agent_name should return 422."""
    bad_trace = {
        "id": "test-bad-001",
        "started_at": "2026-03-20T12:00:00",
    }
    response = client.post("/api/traces", json=bad_trace, headers=api_key_headers)
    assert response.status_code == 422


def test_create_trace_failed_execution(client, api_key_headers, auth_headers):
    """A failed execution with error_message should be stored correctly."""
    failed = {
        "id": "test-failed-001",
        "agent_name": "FailingAgent",
        "status": "failed",
        "started_at": "2026-03-20T10:00:00",
        "error_message": "OpenAI API rate limit exceeded",
    }
    client.post("/api/traces", json=failed, headers=api_key_headers)

    # Verify via the authenticated detail endpoint
    detail = client.get("/api/executions/test-failed-001", headers=auth_headers)
    assert detail.json()["error_message"] == "OpenAI API rate limit exceeded"
    assert detail.json()["status"] == "failed"
