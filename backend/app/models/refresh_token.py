import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Uuid

from app.database import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    jti = Column(String(128), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_id = Column(Uuid, ForeignKey("refresh_tokens.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
