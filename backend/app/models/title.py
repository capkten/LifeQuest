from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class Title(Base):
    __tablename__ = "titles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200))
    unlock_condition_type = Column(String(50))  # e.g. "level", "achievement_count"
    unlock_condition_value = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserTitle(Base):
    __tablename__ = "user_titles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    title_id = Column(Integer, ForeignKey("titles.id"), nullable=False)
    unlocked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "title_id"),
    )

    title = relationship("Title")
