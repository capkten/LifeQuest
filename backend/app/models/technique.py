import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Technique(Base):
    __tablename__ = "techniques"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    technique_key = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    technique_type = Column(String(20), nullable=False)
    required_realm = Column(String(32), nullable=True)
    spirit_stone_cost = Column(Integer, nullable=False, default=0)
    slot_count = Column(Integer, nullable=False, default=1)


class TechniqueSlot(Base):
    __tablename__ = "technique_slots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    slot_type = Column(String(20), nullable=False)
    slot_index = Column(Integer, nullable=False)
    technique_id = Column(Uuid, ForeignKey("techniques.id"), nullable=True)


class LearnedTechnique(Base):
    __tablename__ = "learned_techniques"
    __table_args__ = (UniqueConstraint("user_id", "technique_id", name="uq_learned_technique_user_technique"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    technique_id = Column(Uuid, ForeignKey("techniques.id"), nullable=False, index=True)
    learned_at = Column(DateTime, nullable=False, default=utc_now)
    level = Column(Integer, nullable=False, default=1)
