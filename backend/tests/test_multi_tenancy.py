"""
Tests for multi-tenancy — the most important security property.

Verifies: User A can NEVER see User B's data, even if they know the execution ID.
"""


def test_users_see_only_their_own_data(client):
    """User A's executions should be invisible to User B."""
    # Create User A
    resp_a = client.post("/api/auth/signup", json={
        "email": "alice@example.com",
        "password": "alicepass123",
        "name": "Alice",
    })
    token_a = resp_a.json()["token"]
    api_key_a = resp_a.json()["api_key"]

    # Create User B
    resp_b = client.post("/api/auth/signup", json={
        "email": "bob@example.com",
        "password": "bobpass123",
        "name": "Bob",
    })
    token_b = resp_b.json()["token"]
    api_key_b = resp_b.json()["api_key"]

    # User A sends a trace
    client.post("/api/traces", json={
        "id": "alice-exec-001",
        "agent_name": "AliceAgent",
        "started_at": "2026-03-20T10:00:00",
        "total_cost": 0.01,
        "total_tokens": 100,
    }, headers={"X-API-Key": api_key_a})

    # User B sends a trace
    client.post("/api/traces", json={
        "id": "bob-exec-001",
        "agent_name": "BobAgent",
        "started_at": "2026-03-20T10:00:00",
        "total_cost": 0.05,
        "total_tokens": 500,
    }, headers={"X-API-Key": api_key_b})

    # User A should see only their execution
    alice_execs = client.get("/api/executions", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert alice_execs["total"] == 1
    assert alice_execs["executions"][0]["agent_name"] == "AliceAgent"

    # User B should see only their execution
    bob_execs = client.get("/api/executions", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert bob_execs["total"] == 1
    assert bob_execs["executions"][0]["agent_name"] == "BobAgent"

    # User A's stats should reflect only their data
    alice_stats = client.get("/api/stats", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert alice_stats["total_executions"] == 1
    assert alice_stats["total_cost"] == 0.01

    # User B's stats should reflect only their data
    bob_stats = client.get("/api/stats", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert bob_stats["total_executions"] == 1
    assert bob_stats["total_cost"] == 0.05


def test_user_cannot_access_other_users_execution(client):
    """User A should get 404 when trying to access User B's execution by ID."""
    # Create two users
    resp_a = client.post("/api/auth/signup", json={
        "email": "alice2@example.com", "password": "alicepass123",
    })
    resp_b = client.post("/api/auth/signup", json={
        "email": "bob2@example.com", "password": "bobpass123",
    })
    token_a = resp_a.json()["token"]
    api_key_b = resp_b.json()["api_key"]

    # User B sends a trace
    client.post("/api/traces", json={
        "id": "bob-secret-exec",
        "agent_name": "SecretAgent",
        "started_at": "2026-03-20T10:00:00",
    }, headers={"X-API-Key": api_key_b})

    # User A tries to access User B's execution — should get 404
    response = client.get(
        "/api/executions/bob-secret-exec",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404
