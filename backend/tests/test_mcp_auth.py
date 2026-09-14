from app.models.mcp_access_token import MCPAccessToken
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.schemas.mcp_access_token import MCPAccessTokenCreate
from app.services.mcp_access_token import MCPAccessTokenService


def _auth_headers(client, username="token-owner", email="token-owner@example.com"):
    client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "testpassword123"},
    )
    jwt_token = client.post(
        "/api/auth/login",
        data={"username": username, "password": "testpassword123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {jwt_token}"}


def test_mcp_token_is_returned_once_and_only_hash_is_persisted(client, db_session):
    headers = _auth_headers(client)
    response = client.post(
        "/api/auth/mcp-tokens",
        json={"name": "Claude Desktop", "expires_in_days": 30},
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token"].startswith("lq_mcp_")
    assert payload["status"] == "active"

    stored = db_session.query(MCPAccessToken).filter_by(id=UUID(payload["id"])).one()
    assert stored.token_hash != payload["token"]
    assert len(stored.token_hash) == 64

    listed = client.get("/api/auth/mcp-tokens", headers=headers)
    assert "token" not in listed.json()[0]
    assert "token_hash" not in listed.json()[0]


def test_mcp_token_lifecycle_and_authentication(client, db_session):
    headers = _auth_headers(client)
    created = client.post("/api/auth/mcp-tokens", json={"name": "CLI"}, headers=headers).json()
    service = MCPAccessTokenService(db_session)

    assert service.authenticate(created["token"]) is not None
    token = db_session.query(MCPAccessToken).filter_by(id=UUID(created["id"])).one()
    assert token.last_used_at is not None
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    assert service.authenticate(created["token"]) is None

    token.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    db_session.commit()
    revoked = client.delete(f"/api/auth/mcp-tokens/{created['id']}", headers=headers)
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert "token" not in revoked.json()
    assert service.authenticate(created["token"]) is None
    repeated = client.delete(f"/api/auth/mcp-tokens/{created['id']}", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["revoked_at"] == revoked.json()["revoked_at"]


def test_mcp_token_validation_and_cross_user_revoke(client):
    headers = _auth_headers(client)
    other_headers = _auth_headers(client, "other-owner", "other-owner@example.com")
    assert client.post(
        "/api/auth/mcp-tokens", json={"name": "x" * 101}, headers=headers
    ).status_code == 422
    assert client.post(
        "/api/auth/mcp-tokens", json={"name": "x", "expires_in_days": 0}, headers=headers
    ).status_code == 422
    assert client.post(
        "/api/auth/mcp-tokens", json={"name": "x", "expires_in_days": 366}, headers=headers
    ).status_code == 422
    created = client.post("/api/auth/mcp-tokens", json={"name": "x"}, headers=headers).json()
    assert client.delete(f"/api/auth/mcp-tokens/{created['id']}", headers=other_headers).status_code == 404
    assert client.delete("/api/auth/mcp-tokens/not-a-uuid", headers=headers).status_code == 422


def test_mcp_token_service_rejects_invalid_raw_tokens(client, db_session):
    service = MCPAccessTokenService(db_session)
    assert service.authenticate("") is None
    assert service.authenticate("lq_mcp_invalid") is None
    assert service.authenticate(None) is None
