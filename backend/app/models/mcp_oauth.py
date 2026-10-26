"""Separate persisted MCP OAuth credentials; raw secrets never enter these tables."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, JSON
from app.database import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MCPOAuthClient(Base):
    __tablename__ = "mcp_oauth_clients"
    id = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    redirect_uris = Column(JSON, nullable=False)
    auth_method = Column(String(30), nullable=False)
    secret_hash = Column(String(64))
    created_at = Column(DateTime, nullable=False, default=now)


class MCPOAuthRequest(Base):
    __tablename__ = "mcp_oauth_requests"
    request_hash = Column(String(64), primary_key=True)
    client_id = Column(String(100), ForeignKey("mcp_oauth_clients.id"), nullable=False)
    user_id = Column(Uuid, ForeignKey("users.id"))
    redirect_uri = Column(String(2048), nullable=False)
    state = Column(String(4096))
    challenge = Column(String(43), nullable=False)
    resource = Column(String(2048), nullable=False)
    scope = Column(String(100), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime)


class MCPOAuthGrant(Base):
    __tablename__ = "mcp_oauth_grants"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id = Column(String(100), ForeignKey("mcp_oauth_clients.id"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    scope = Column(String(100), nullable=False)
    resource = Column(String(2048), nullable=False)
    created_at = Column(DateTime, nullable=False, default=now)
    revoked_at = Column(DateTime)


class MCPOAuthCode(Base):
    __tablename__ = "mcp_oauth_codes"
    code_hash = Column(String(64), primary_key=True)
    grant_id = Column(Uuid, ForeignKey("mcp_oauth_grants.id"), nullable=False)
    redirect_uri = Column(String(2048), nullable=False)
    challenge = Column(String(43), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed_at = Column(DateTime)


class MCPOAuthToken(Base):
    __tablename__ = "mcp_oauth_tokens"
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    grant_id = Column(Uuid, ForeignKey("mcp_oauth_grants.id"), nullable=False, index=True)
    access_hash = Column(String(64), nullable=False, unique=True, index=True)
    refresh_hash = Column(String(64), nullable=False, unique=True, index=True)
    access_expires_at = Column(DateTime, nullable=False)
    refresh_expires_at = Column(DateTime, nullable=False)
    refresh_consumed_at = Column(DateTime)
