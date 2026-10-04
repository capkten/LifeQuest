import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Uuid

from app.database import Base


class MCPAccessToken(Base):
    __tablename__ = "mcp_access_tokens"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    token_prefix = Column(String(16), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
