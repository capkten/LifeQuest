from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Uuid

from app.database import Base


class CoinSource(str, Enum):
    TASK = "task"
    HABIT = "habit"
    GOAL = "goal"
    CHECKIN = "checkin"
    SHOP = "shop"
    ACHIEVEMENT = "achievement"
    OTHER = "other"


class CoinType(str, Enum):
    EARN = "earn"
    SPEND = "spend"


class CoinTransaction(Base):
    __tablename__ = "coin_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    type = Column(String(10))  # earn / spend
    source = Column(String(20))  # task / habit / goal / checkin / shop / achievement / other
    source_id = Column(String(36), nullable=True)  # UUID of the source entity
    description = Column(String(200))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
