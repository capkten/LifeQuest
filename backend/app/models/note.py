import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    folders = relationship("Folder", back_populates="notebook")


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    notebook_id = Column(Uuid, ForeignKey("notebooks.id"), nullable=False)
    parent_id = Column(Uuid, ForeignKey("folders.id"))
    name = Column(String(100), nullable=False)
    path = Column(String(500))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    notebook = relationship("Notebook", back_populates="folders")
    parent = relationship("Folder", remote_side=[id])
    notes = relationship("Note", back_populates="folder")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    folder_id = Column(Uuid, ForeignKey("folders.id"), nullable=False)
    title = Column(String(200), nullable=False)
    file_path = Column(String(500))
    summary = Column(Text)
    tags = Column(String(500))  # JSON string
    is_pinned = Column(Boolean, default=False)
    word_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    folder = relationship("Folder", back_populates="notes")
    attachments = relationship("Attachment", back_populates="note")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, ForeignKey("notes.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_type = Column(String(50))
    file_size = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    note = relationship("Note", back_populates="attachments")
