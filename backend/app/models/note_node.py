import uuid
import re
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base

INVALID_NAME_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f]')
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def normalize_name(name: str) -> str:
    """Normalize a node name for uniqueness comparison.

    Rules:
    - Strip leading/trailing whitespace
    - Reject empty names
    - Reject names containing path separators, control chars, or Windows reserved names
    - Case-insensitive comparison (stored lowercased)
    """
    stripped = name.strip()
    if not stripped:
        raise ValueError("Name cannot be empty")
    if INVALID_NAME_CHARS.search(stripped):
        raise ValueError("Name contains invalid characters")
    upper = stripped.upper().replace(".MD", "")
    if upper in WINDOWS_RESERVED:
        raise ValueError("Name is a reserved system name")
    return stripped.lower()


class NoteNode(Base):
    __tablename__ = "note_nodes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    notebook_id = Column(Uuid, ForeignKey("notebooks.id"), nullable=False)
    parent_id = Column(Uuid, ForeignKey("note_nodes.id"), nullable=True)
    type = Column(String(10), nullable=False)  # "folder" or "note"
    name = Column(String(200), nullable=False)
    normalized_name = Column(String(200), nullable=False)
    path = Column(String(1000), nullable=False)
    content_path = Column(String(1000), nullable=True)  # note only
    summary = Column(Text, nullable=True)  # note only
    tags = Column(String(500), nullable=True)  # note only, JSON string
    is_pinned = Column(Boolean, default=False)  # note only
    word_count = Column(Integer, default=0)  # note only
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("notebook_id", "parent_id", "normalized_name", name="uq_node_sibling_name"),
    )

    notebook = relationship("Notebook", backref="note_nodes")
    parent = relationship("NoteNode", remote_side=[id], backref="children")
