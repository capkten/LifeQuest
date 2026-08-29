import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint, Uuid

from app.database import Base


class NotebookMember(Base):
    __tablename__ = "notebook_members"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    notebook_id = Column(Uuid, ForeignKey("notebooks.id"), nullable=False)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False, default="editor")
    status = Column(String(20), nullable=False, default="active")
    invited_by = Column(Uuid, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("notebook_id", "user_id", name="uq_notebook_member_user"),
    )


class NoteUserActivity(Base):
    __tablename__ = "note_user_activity"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, ForeignKey("note_nodes.id"), nullable=False)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    last_opened_at = Column(DateTime, nullable=True)
    is_pinned = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("note_id", "user_id", name="uq_note_activity_user"),
    )


class NoteCollabDocument(Base):
    __tablename__ = "note_collab_documents"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, ForeignKey("note_nodes.id"), nullable=False, unique=True)
    snapshot = Column(LargeBinary, nullable=True)
    snapshot_cursor = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=True)
    initialized = Column(Boolean, nullable=False, default=False)
    init_claimed_at = Column(DateTime, nullable=True)
    init_claimed_by = Column(Uuid, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class NoteCollabEvent(Base):
    __tablename__ = "note_collab_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Uuid, ForeignKey("note_nodes.id"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    update_payload = Column(LargeBinary, nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
