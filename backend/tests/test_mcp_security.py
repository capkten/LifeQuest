import pytest
from types import SimpleNamespace
from uuid import UUID

import mcp_server
from app.database import Base
from app.models.user import User
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
    assert mcp_server._resolve_user_id(db_session) == UUID(str(user_a.id))


def test_mcp_context_does_not_switch_between_users(db_session):
    Base.metadata.create_all(bind=db_session.bind)
    user_a = User(username="mcp-context-a", email="mcp-context-a@example.com", password_hash="hashed")
    user_b = User(username="mcp-context-b", email="mcp-context-b@example.com", password_hash="hashed")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    token = mcp_server._auth_user_id.set(user_a.id)
    try:
        assert mcp_server._resolve_user_id(db_session) == user_a.id
        mcp_server._auth_user_id.set(user_b.id)
        assert mcp_server._resolve_user_id(db_session) == user_b.id
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
