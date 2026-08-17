import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Uuid, UniqueConstraint

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class CultivationProfile(Base):
    __tablename__ = "cultivation_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    realm_key = Column(String(32), nullable=False, default="qi_refining")
    minor_stage = Column(Integer, nullable=False, default=1)
    cultivation = Column(Integer, nullable=False, default=0)
    spirit_stones = Column(Integer, nullable=False, default=0)
    merit = Column(Integer, nullable=False, default=0)
    contribution = Column(Integer, nullable=False, default=0)
    mind_state = Column(Integer, nullable=False, default=50)
    aptitude_points = Column(Integer, nullable=False, default=0)
    cultivation_efficiency = Column(Float, nullable=False, default=1.0)


class CultivationLog(Base):
    __tablename__ = "cultivation_logs"
    __table_args__ = (UniqueConstraint("source_key", name="uq_cultivation_log_source_key"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String(64), nullable=False)
    source_key = Column(String(128), nullable=True, index=True)
    cultivation_delta = Column(Integer, nullable=False, default=0)
    spirit_stones_delta = Column(Integer, nullable=False, default=0)
    merit_delta = Column(Integer, nullable=False, default=0)
    contribution_delta = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class TribulationAttempt(Base):
    __tablename__ = "tribulation_attempts"
    __table_args__ = (UniqueConstraint("user_id", "attempted_date", name="uq_tribulation_attempt_user_day"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    target_realm = Column(String(32), nullable=False)
    base_probability = Column(Float, nullable=False)
    readiness_score = Column(Float, nullable=False)
    pill_bonus = Column(Float, nullable=False, default=0.0)
    final_probability = Column(Float, nullable=False)
    roll = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False)
    cultivation_loss = Column(Integer, nullable=False, default=0)
    attempted_date = Column(Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    attempted_at = Column(DateTime, nullable=False, default=utc_now)
