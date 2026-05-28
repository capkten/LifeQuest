# backend/app/models/note.py
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


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, nullable=False)  # references note_nodes.id
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_type = Column(String(50))
    file_size = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
