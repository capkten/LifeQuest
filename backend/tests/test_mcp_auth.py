from app.models.mcp_access_token import MCPAccessToken
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.schemas.mcp_access_token import MCPAccessTokenCreate
from app.services.mcp_access_token import MCPAccessTokenService
import mcp_server
from app.database import Base
from app.models.user import User
from mcp.server.lowlevel.server import request_ctx
from types import SimpleNamespace
from starlette.responses import JSONResponse
from starlette.testclient import TestClient


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


def test_login_with_token_binds_session_without_echoing_token(db_session, monkeypatch):
    Base.metadata.create_all(bind=db_session.bind)
    user = User(username="mcp-token-login", email="mcp-token-login@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.commit()
    raw_token = MCPAccessTokenService(db_session).create_token(
        user.id, MCPAccessTokenCreate(name="test")
    )[1]
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    mcp_server._auth_user_id.set(None)
    mcp_server._auth_token.set(None)
    class Session:
        pass

    mcp_session = Session()
    request_token = request_ctx.set(SimpleNamespace(session=mcp_session))
    try:
        result = mcp_server.login_with_token(raw_token)
        assert raw_token not in str(result)
        assert mcp_server._resolve_user_id(db_session) == user.id
    finally:
        request_ctx.reset(request_token)
        mcp_server._auth_user_id.set(None)
        mcp_server._auth_token.set(None)


def test_mcp_token_middleware_handles_bearer_header_and_compatibility_mode(db_session, monkeypatch):
    Base.metadata.create_all(bind=db_session.bind)
    user = User(username="mcp-sse-user", email="mcp-sse-user@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.commit()
    raw_token = MCPAccessTokenService(db_session).create_token(
        user.id, MCPAccessTokenCreate(name="sse")
    )[1]
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)

    async def endpoint(scope, receive, send):
        await JSONResponse({"user_id": str(mcp_server._auth_user_id.get())})(scope, receive, send)

    # A plain ASGI app avoids coupling this test to FastMCP routing internals.
    wrapped = mcp_server.MCPTokenAuthMiddleware(endpoint)
    client = TestClient(wrapped)
    assert client.get("/", headers={"aUtHoRiZaTiOn": f"Bearer {raw_token}"}).status_code == 200
    invalid = client.get("/", headers={"Authorization": "Bearer lq_mcp_invalid"})
    assert invalid.status_code == 401
    assert invalid.headers["www-authenticate"] == "Bearer"
    assert "lq_mcp_invalid" not in invalid.text
    assert client.get("/").status_code == 200
    client.close()
