import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    condition_type = Column(String(50))  # task_count, habit_streak, level, coins_earned
    condition_value = Column(Integer)
    coin_reward = Column(Integer, default=0)
    exp_reward = Column(Integer, default=0)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Uuid, ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    achievement = relationship("Achievement", foreign_keys=[achievement_id])
