import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.mcp_access_token import MCPAccessToken
from app.schemas.mcp_access_token import MCPAccessTokenCreate


class MCPAccessTokenService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _metadata(cls, token: MCPAccessToken) -> dict:
        now = datetime.now(timezone.utc)
        expires_at = cls._utc(token.expires_at)
        status = "revoked" if token.revoked_at else "expired" if expires_at <= now else "active"
        return {
            "id": token.id,
            "name": token.name,
            "token_prefix": token.token_prefix,
            "created_at": token.created_at,
            "last_used_at": token.last_used_at,
            "expires_at": token.expires_at,
            "revoked_at": token.revoked_at,
            "status": status,
        }

    def create_token(self, user_id: UUID, data: MCPAccessTokenCreate) -> tuple[MCPAccessToken, str]:
        raw_token = f"lq_mcp_{secrets.token_urlsafe(32)}"
        token = MCPAccessToken(
            user_id=user_id,
            name=data.name,
            token_prefix=raw_token[:16],
            token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=data.expires_in_days),
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token, raw_token

    def list_tokens(self, user_id: UUID) -> list[dict]:
        tokens = (
            self.db.query(MCPAccessToken)
            .filter(MCPAccessToken.user_id == user_id)
            .order_by(MCPAccessToken.created_at.desc())
            .all()
        )
        return [self._metadata(token) for token in tokens]

    def authenticate(self, raw_token: str) -> Optional[UUID]:
        if not isinstance(raw_token, str) or not raw_token.startswith("lq_mcp_"):
            return None
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        token = self.db.query(MCPAccessToken).filter(MCPAccessToken.token_hash == token_hash).first()
        if token is None or token.revoked_at is not None:
            return None
        if self._utc(token.expires_at) <= datetime.now(timezone.utc):
            return None
        token.last_used_at = datetime.now(timezone.utc)
        self.db.commit()
        return token.user_id

    def revoke(self, token_id: UUID, user_id: UUID) -> dict:
        token = (
            self.db.query(MCPAccessToken)
            .filter(MCPAccessToken.id == token_id, MCPAccessToken.user_id == user_id)
            .first()
        )
        if token is None:
            raise ValueError("MCP token not found")
        if token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(token)
        return self._metadata(token)
