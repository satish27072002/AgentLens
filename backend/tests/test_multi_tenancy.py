"""
Tests for multi-tenancy — the most important security property.

Verifies: User A can NEVER see User B's data, even if they know the execution ID.

With Auth0, we use mock tokens for two different users:
- User A: "fake-auth0-token-for-tests" → auth0_sub = "auth0|test123"
- User B: "fake-auth0-token-user-2"    → auth0_sub = "auth0|user2"
"""

import uuid
from app.models import User, ApiKey
from app.auth import generate_api_key


def _create_user_with_key(db_session, email, auth0_sub):
    """Helper to create a user with an API key."""
    user_id = str(uuid.uuid4())
    api_key_value = generate_api_key()

    user = User(id=user_id, email=email, auth0_sub=auth0_sub, name=email.split("@")[0])
    db_session.add(user)

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        user_id=user_id,
        key_value=api_key_value,
        name="Default",
    )
    db_session.add(api_key)
    db_session.commit()

    return user, api_key_value


def test_users_see_only_their_own_data(client, db_session):
    """User A's executions should be invisible to User B."""
    # Create two users
    user_a, api_key_a = _create_user_with_key(
        db_session, "alice@example.com", "auth0|test123"
    )
    user_b, api_key_b = _create_user_with_key(
        db_session, "bob@example.com", "auth0|user2"
    )

    token_a = "fake-auth0-token-for-tests"
    token_b = "fake-auth0-token-user-2"

    # User A sends a trace
    client.post(
        "/api/traces",
        json={
            "id": "alice-exec-001",
            "agent_name": "AliceAgent",
            "started_at": "2026-03-20T10:00:00",
            "total_cost": 0.01,
            "total_tokens": 100,
        },
        headers={"X-API-Key": api_key_a},
    )

    # User B sends a trace
    client.post(
        "/api/traces",
        json={
            "id": "bob-exec-001",
            "agent_name": "BobAgent",
            "started_at": "2026-03-20T10:00:00",
            "total_cost": 0.05,
            "total_tokens": 500,
        },
        headers={"X-API-Key": api_key_b},
    )

    # User A should see only their execution
    alice_execs = client.get(
        "/api/executions", headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    assert alice_execs["total"] == 1
    assert alice_execs["executions"][0]["agent_name"] == "AliceAgent"

    # User B should see only their execution
    bob_execs = client.get(
        "/api/executions", headers={"Authorization": f"Bearer {token_b}"}
    ).json()
    assert bob_execs["total"] == 1
    assert bob_execs["executions"][0]["agent_name"] == "BobAgent"

    # User A's stats should reflect only their data
    alice_stats = client.get(
        "/api/stats", headers={"Authorization": f"Bearer {token_a}"}
    ).json()
    assert alice_stats["total_executions"] == 1
    assert alice_stats["total_cost"] == 0.01

    # User B's stats should reflect only their data
    bob_stats = client.get(
        "/api/stats", headers={"Authorization": f"Bearer {token_b}"}
    ).json()
    assert bob_stats["total_executions"] == 1
    assert bob_stats["total_cost"] == 0.05


def test_user_cannot_access_other_users_execution(client, db_session):
    """User A should get 404 when trying to access User B's execution by ID."""
    user_a, _ = _create_user_with_key(db_session, "alice2@example.com", "auth0|test123")
    user_b, api_key_b = _create_user_with_key(
        db_session, "bob2@example.com", "auth0|user2"
    )

    token_a = "fake-auth0-token-for-tests"

    # User B sends a trace
    client.post(
        "/api/traces",
        json={
            "id": "bob-secret-exec",
            "agent_name": "SecretAgent",
            "started_at": "2026-03-20T10:00:00",
        },
        headers={"X-API-Key": api_key_b},
    )

    # User A tries to access User B's execution — should get 404
    response = client.get(
        "/api/executions/bob-secret-exec",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404
