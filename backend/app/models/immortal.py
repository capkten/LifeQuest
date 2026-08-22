import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid, UniqueConstraint

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ImmortalProfile(Base):
    __tablename__ = "immortal_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    realm_key = Column(String(32), nullable=False, default="immortal_foundation")
    stage = Column(Integer, nullable=False, default=1)
    essence = Column(Integer, nullable=False, default=0)
    immortal_stones = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


class AscensionRecord(Base):
    __tablename__ = "ascension_records"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_ascension_record_user"),
        UniqueConstraint("request_key", name="uq_ascension_record_request"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    request_key = Column(String(128), nullable=False)
    source_key = Column(String(128), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)


class CrossRealmSettlement(Base):
    __tablename__ = "cross_realm_settlements"
    __table_args__ = (
        UniqueConstraint("user_id", "source_key", name="uq_cross_realm_user_source"),
        UniqueConstraint("request_key", name="uq_cross_realm_request"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    source_key = Column(String(128), nullable=False)
    request_key = Column(String(128), nullable=False)
    essence_delta = Column(Integer, nullable=False, default=0)
    immortal_stones_delta = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=utc_now)
