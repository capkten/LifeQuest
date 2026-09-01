import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utc_now():
    return datetime.now(timezone.utc)


class NoteSyncChange(Base):
    """Append-only notebook change log consumed by desktop clients."""

    __tablename__ = "note_sync_changes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    node_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    node_type: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    content_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("notebook_id", "sequence", name="uq_note_sync_change_sequence"),
    )


class NoteSyncOperation(Base):
    """Durable idempotency ledger for remote writes from a desktop device."""

    __tablename__ = "note_sync_operations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_operation_id: Mapped[str] = mapped_column(String(160), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "notebook_id", "client_operation_id", name="uq_note_sync_operation_client_id"
        ),
    )


class NoteSyncConflict(Base):
    """Recoverable conflict metadata; neither side is overwritten implicitly."""

    __tablename__ = "note_sync_conflicts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    notebook_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    local_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    base_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conflict_artifact_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
