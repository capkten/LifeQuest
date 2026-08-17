import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Uuid

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class WorldNode(Base):
    __tablename__ = "world_nodes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    node_key = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    required_realm = Column(String(32), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_hidden = Column(Boolean, nullable=False, default=False)


class Sect(Base):
    __tablename__ = "sects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    sect_key = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    star = Column(Integer, nullable=False, default=1)
    kind = Column(String(20), nullable=False, default="normal")
    task_preference = Column(String(64), nullable=True)
    core_legacy = Column(Text, nullable=True)
    entry_realm = Column(String(32), nullable=True)
    trial_key = Column(String(64), nullable=True)
    world_node_id = Column(Uuid, ForeignKey("world_nodes.id"), nullable=True)


class SectMembership(Base):
    __tablename__ = "sect_memberships"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    sect_id = Column(Uuid, ForeignKey("sects.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="active")
    joined_at = Column(DateTime, nullable=False, default=utc_now)
    left_at = Column(DateTime, nullable=True)


class Npc(Base):
    __tablename__ = "npcs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    sect_id = Column(Uuid, ForeignKey("sects.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    role = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    is_core = Column(Boolean, nullable=False, default=False)


class NpcEvent(Base):
    __tablename__ = "npc_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    npc_id = Column(Uuid, ForeignKey("npcs.id"), nullable=False, index=True)
    event_key = Column(String(64), nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
