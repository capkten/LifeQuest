import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class CultivationRetreat(Base):
    __tablename__ = "cultivation_retreats"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    todo_id = Column(Uuid, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)

    target_duration = Column(Integer, nullable=False)
    actual_duration = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="active", nullable=False)

    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    exp_gained = Column(Integer, default=0, nullable=False)
    coins_gained = Column(Integer, default=0, nullable=False)

    encounter_id = Column(String(50), nullable=True)
    encounter_result = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)


class EncounterEvent(Base):
    __tablename__ = "encounter_events"

    id = Column(String(50), primary_key=True)
    title = Column(String(100), nullable=False)
    story_text = Column(Text, nullable=False)
    rarity = Column(String(20), default="common", nullable=False)
    min_realm_level = Column(Integer, default=1, nullable=False)

    reward_type = Column(String(30), nullable=False)
    reward_payload = Column(JSON, nullable=False, default=dict)
    weight = Column(Integer, default=100, nullable=False)


class UserEncounterRecord(Base):
    __tablename__ = "user_encounter_records"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    encounter_id = Column(String(50), ForeignKey("encounter_events.id"), nullable=False, index=True)

    first_unlocked_at = Column(DateTime, default=utc_now, nullable=False)
    unlock_count = Column(Integer, default=1, nullable=False)
    last_retreat_id = Column(Uuid, nullable=True)
