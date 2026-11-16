import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, JSON, String, UniqueConstraint, Uuid

from app.database import Base


class CaveRequest(Base):
    __tablename__ = 'cave_requests'
    __table_args__ = (UniqueConstraint('user_id', 'request_id', name='uq_cave_user_request'),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False, index=True)
    request_id = Column(Uuid, nullable=False)
    operation = Column(String(30), nullable=False)
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class CaveDailyState(Base):
    __tablename__ = 'cave_daily_states'
    __table_args__ = (UniqueConstraint('user_id', 'plan_date', name='uq_cave_daily_user_date'),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False, index=True)
    plan_date = Column(Date, nullable=False)
    omen_key = Column(String(30), nullable=False)
    sign_task_ids = Column(JSON, nullable=False, default=list)
    reroll_used = Column(Boolean, nullable=False, default=False)
    had_signs = Column(Boolean, nullable=False, default=False)
    offline_note_key = Column(String(80), nullable=True)
    offline_note = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CaveOnboardingState(Base):
    __tablename__ = 'cave_onboarding_states'

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False)
    first_opened_at = Column(DateTime, nullable=False)
    completed_session_id = Column(Uuid, ForeignKey('cultivation_retreats.id'), nullable=True)


class CaveCompanionState(Base):
    __tablename__ = 'cave_companion_states'

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False, unique=True, index=True)
    active_pet_key = Column(String(30), nullable=True)
    pet_unlocks = Column(JSON, nullable=False, default=dict)


class CaveLetter(Base):
    __tablename__ = 'cave_letters'
    __table_args__ = (UniqueConstraint('user_id', 'senior_key', 'week_start', name='uq_cave_letter_user_senior_week'),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False, index=True)
    senior_key = Column(String(30), nullable=False)
    week_start = Column(Date, nullable=False)
    delivered_at = Column(DateTime, nullable=False)
    content = Column(JSON, nullable=False)
    state = Column(JSON, nullable=False, default=dict)


class CaveTrialAcceptance(Base):
    __tablename__ = 'cave_trial_acceptances'
    __table_args__ = (UniqueConstraint('user_id', 'week_start', name='uq_cave_trial_user_week'),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    letter_id = Column(Uuid, ForeignKey('cave_letters.id'), nullable=False)
    accepted_at = Column(DateTime, nullable=False)


class CaveEvent(Base):
    __tablename__ = 'cave_events'
    __table_args__ = (UniqueConstraint('user_id', 'request_id', name='uq_cave_event_request'),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id'), nullable=False, index=True)
    request_id = Column(Uuid, nullable=False)
    event = Column(String(30), nullable=False)
    source = Column(String(40), nullable=False)
    mode = Column(String(10), nullable=False)
    has_active_session = Column(Boolean, nullable=False)
    session_id = Column(Uuid, ForeignKey('cultivation_retreats.id'), nullable=True, index=True)
    facts = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
