"""Tests for API key management endpoints."""


def test_create_api_key(client, auth_headers):
    """Creating a key should return the full key (only time it's shown)."""
    response = client.post(
        "/api/keys", json={"name": "Production"}, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["key"].startswith("al_")
    assert data["name"] == "Production"


def test_list_api_keys(client, auth_headers):
    """Listing keys should show masked versions."""
    response = client.get("/api/keys", headers=auth_headers)
    assert response.status_code == 200
    keys = response.json()
    assert len(keys) >= 1  # At least the default key from test_user
    for key in keys:
        assert key["key_preview"].startswith("al_...")


def test_delete_api_key(client, auth_headers, test_user):
    """Deleting a key should deactivate it."""
    # Create a key to delete
    create_resp = client.post(
        "/api/keys", json={"name": "ToDelete"}, headers=auth_headers
    )
    key_id = create_resp.json()["id"]

    # Delete it
    delete_resp = client.delete(f"/api/keys/{key_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"

    # Verify it shows as inactive
    keys = client.get("/api/keys", headers=auth_headers).json()
    deleted_key = next(k for k in keys if k["id"] == key_id)
    assert deleted_key["is_active"] is False


def test_delete_nonexistent_key(client, auth_headers):
    """Deleting a non-existent key should return 404."""
    response = client.delete("/api/keys/fake-id", headers=auth_headers)
    assert response.status_code == 404
