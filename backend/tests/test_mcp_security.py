import pytest
import json
from datetime import date, datetime
from types import SimpleNamespace
from uuid import UUID

import mcp_server
from app.database import Base
from app.models.user import User
from app.schemas.user import UserResponse
from mcp.server.lowlevel.server import request_ctx


def test_mcp_requires_login_or_explicit_service_account(db_session, monkeypatch):
    Base.metadata.create_all(bind=db_session.bind)
    user_a = User(
        username="mcp-a",
        email="mcp-a@example.com",
        password_hash="hashed",
    )
    db_session.add(user_a)
    db_session.commit()

    mcp_server._auth_user_id.set(None)
    monkeypatch.delenv("LIFEQUEST_USER_ID", raising=False)
    monkeypatch.delenv("LIFEQUEST_MCP_SERVICE_USER_ID", raising=False)
    with pytest.raises(RuntimeError, match="请先调用 login"):
        mcp_server._resolve_user_id(db_session)

    monkeypatch.setenv("LIFEQUEST_USER_ID", str(user_a.id))
    with pytest.raises(RuntimeError, match="请先调用 login"):
        mcp_server._resolve_user_id(db_session)

    monkeypatch.setenv("LIFEQUEST_MCP_SERVICE_USER_ID", str(user_a.id))
    with pytest.raises(RuntimeError, match="Token"):
        mcp_server._resolve_user_id(db_session)
    mcp_server._auth_user_id.set(None)
    mcp_server._auth_token_authenticated.set(False)


def test_service_user_id_without_token_is_rejected(db_session, monkeypatch):
    user = User(
        username="mcp-service-user",
        email="mcp-service-user@example.com",
        password_hash="unused",
    )
    db_session.add(user)
    db_session.commit()
    monkeypatch.setenv("LIFEQUEST_MCP_SERVICE_USER_ID", str(user.id))
    monkeypatch.delenv("LIFEQUEST_MCP_TOKEN", raising=False)
    mcp_server._auth_user_id.set(None)
    with pytest.raises(RuntimeError, match="Token"):
        mcp_server._resolve_user_id(db_session)


def test_serialize_supports_pydantic_and_nested_json_values():
    model = UserResponse(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        username="serialized",
        email="serialized@example.com",
        level=1,
        experience=2,
        coins=3,
        total_coins_earned=4,
        title="初学者",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 2),
    )
    result = mcp_server._serialize({"model": model, "day": date(2026, 1, 3)})
    json.dumps(result, ensure_ascii=False)
    assert result["model"]["id"] == "00000000-0000-0000-0000-000000000001"
    assert result["day"] == "2026-01-03"


def test_serialize_converts_supported_non_string_dict_keys():
    result = mcp_server._serialize({
        UUID("00000000-0000-0000-0000-000000000002"): date(2026, 1, 4),
        date(2026, 1, 5): UUID("00000000-0000-0000-0000-000000000003"),
    })
    json.dumps(result)
    assert result["00000000-0000-0000-0000-000000000002"] == "2026-01-04"
    assert result["2026-01-05"] == "00000000-0000-0000-0000-000000000003"


def test_environment_mcp_token_resolves_and_service_id_must_match(db_session, monkeypatch):
    from app.schemas.mcp_access_token import MCPAccessTokenCreate
    from app.services.mcp_access_token import MCPAccessTokenService

    Base.metadata.create_all(bind=db_session.bind)
    user = User(username="mcp-env-user", email="mcp-env-user@example.com", password_hash="hashed")
    other = User(username="mcp-env-other", email="mcp-env-other@example.com", password_hash="hashed")
    db_session.add_all([user, other])
    db_session.commit()
    raw_token = MCPAccessTokenService(db_session).create_token(
        user.id, MCPAccessTokenCreate(name="env")
    )[1]
    mcp_server._auth_user_id.set(None)
    mcp_server._auth_token.set(None)
    mcp_server._auth_token_authenticated.set(False)
    monkeypatch.setenv("LIFEQUEST_MCP_TOKEN", raw_token)
    monkeypatch.setenv("LIFEQUEST_MCP_SERVICE_USER_ID", str(user.id))
    assert mcp_server._resolve_user_id(db_session) == user.id
    mcp_server._auth_user_id.set(None)
    monkeypatch.setenv("LIFEQUEST_MCP_SERVICE_USER_ID", str(other.id))
    mcp_server._auth_token_authenticated.set(False)
    with pytest.raises(RuntimeError, match="不一致"):
        mcp_server._resolve_user_id(db_session)


def test_password_context_cannot_bypass_configured_service_id(db_session, monkeypatch):
    from app.services.auth import get_password_hash

    Base.metadata.create_all(bind=db_session.bind)
    user = User(
        username="mcp-password-config",
        email="mcp-password-config@example.com",
        password_hash=get_password_hash("correct-password"),
    )
    db_session.add(user)
    db_session.commit()
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    mcp_server._auth_user_id.set(None)
    mcp_server._auth_token_authenticated.set(False)
    mcp_server.login("mcp-password-config", "correct-password")
    monkeypatch.setenv("LIFEQUEST_MCP_SERVICE_USER_ID", str(user.id))
    with pytest.raises(RuntimeError, match="Token"):
        mcp_server._resolve_user_id(db_session)
    mcp_server._auth_user_id.set(None)
    mcp_server._auth_token.set(None)
    mcp_server._auth_token_authenticated.set(False)


def test_mcp_context_does_not_switch_between_users(db_session):
    Base.metadata.create_all(bind=db_session.bind)
    user_a = User(username="mcp-context-a", email="mcp-context-a@example.com", password_hash="hashed")
    user_b = User(username="mcp-context-b", email="mcp-context-b@example.com", password_hash="hashed")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    token = mcp_server._auth_user_id.set(user_a.id)
    try:
        assert mcp_server._resolve_user_id(db_session) == user_a.id
        with pytest.raises(RuntimeError, match="switch"):
            mcp_server._set_authenticated_user(user_b.id)
    finally:
        mcp_server._auth_user_id.reset(token)


def test_mcp_login_persists_across_requests_in_same_session(db_session):
    Base.metadata.create_all(bind=db_session.bind)
    user = User(
        username="mcp-session-user",
        email="mcp-session-user@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()

    class Session:
        pass

    session = Session()
    first_request = request_ctx.set(SimpleNamespace(session=session))
    try:
        mcp_server._set_authenticated_user(user.id)
    finally:
        request_ctx.reset(first_request)

    second_request = request_ctx.set(SimpleNamespace(session=session))
    try:
        assert mcp_server._resolve_user_id(db_session) == user.id
    finally:
        request_ctx.reset(second_request)


def test_login_and_profile_never_return_password_hash(db_session, monkeypatch):
    from app.services.auth import get_password_hash

    user = User(
        username="mcp-safe-profile",
        email="mcp-safe-profile@example.com",
        password_hash=get_password_hash("correct-password"),
    )
    db_session.add(user)
    db_session.commit()
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    mcp_server._auth_user_id.set(None)
    result = mcp_server.login("mcp-safe-profile", "correct-password")
    profile = mcp_server.get_profile()
    assert "password_hash" not in result["user"]
    assert "password_hash" not in profile
