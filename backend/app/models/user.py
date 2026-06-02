import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy import Uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar = Column(String(255))
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    coins = Column(Integer, default=0)
    total_coins_earned = Column(Integer, default=0)
    title = Column(String(50), default="初学者")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
