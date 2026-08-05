# backend/app/repositories/note.py
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.note import Notebook, Attachment
from app.models.note_node import NoteNode
from app.repositories.base import BaseRepository


class NotebookRepository(BaseRepository[Notebook]):
    def __init__(self, db: Session):
        super().__init__(Notebook, db)

    def get_by_user(self, user_id: UUID) -> List[Notebook]:
        return self.db.query(Notebook).filter(Notebook.user_id == user_id).all()


class NoteNodeRepository(BaseRepository[NoteNode]):
    def __init__(self, db: Session):
        super().__init__(NoteNode, db)

    def get_children(self, notebook_id: UUID, parent_id: Optional[UUID]) -> List[NoteNode]:
        """Get direct children of a node. parent_id=None means root level."""
        q = self.db.query(NoteNode).filter(NoteNode.notebook_id == notebook_id)
        if parent_id is None:
            q = q.filter(NoteNode.parent_id.is_(None))
        else:
            q = q.filter(NoteNode.parent_id == parent_id)
        return q.order_by(NoteNode.type.desc(), NoteNode.name).all()

    def get_tree(self, notebook_id: UUID) -> List[NoteNode]:
        """Get ALL nodes in a notebook (for building client-side tree)."""
        return (
            self.db.query(NoteNode)
            .filter(NoteNode.notebook_id == notebook_id)
            .order_by(NoteNode.path)
            .all()
        )

    def check_name_conflict(self, notebook_id: UUID, parent_id: Optional[UUID], normalized_name: str) -> bool:
        """Check if a node with the same normalized name exists in the same directory."""
        q = self.db.query(NoteNode).filter(
            NoteNode.notebook_id == notebook_id,
            NoteNode.normalized_name == normalized_name,
        )
        if parent_id is None:
            q = q.filter(NoteNode.parent_id.is_(None))
        else:
            q = q.filter(NoteNode.parent_id == parent_id)
        return q.first() is not None

    def get_descendants(self, node_id: UUID) -> List[NoteNode]:
        """Get all descendants of a node (for recursive delete)."""
        node = self.get_by_id(node_id)
        if not node:
            return []
        return (
            self.db.query(NoteNode)
            .filter(NoteNode.notebook_id == node.notebook_id, NoteNode.path.startswith(node.path + "/"))
            .all()
        )

    def get_by_notebook(self, notebook_id: UUID) -> List[NoteNode]:
        return self.db.query(NoteNode).filter(NoteNode.notebook_id == notebook_id).all()

    def search(self, user_id: UUID, query: str) -> List[NoteNode]:
        return (
            self.db.query(NoteNode)
            .join(Notebook)
            .filter(
                Notebook.user_id == user_id,
                NoteNode.type == "note",
                (NoteNode.name.contains(query)) |
                (NoteNode.summary.contains(query)) |
                (NoteNode.tags.contains(query)),
            )
            .all()
        )

    def get_recent_by_user(self, user_id: UUID, limit: int) -> List[NoteNode]:
        return (
            self.db.query(NoteNode)
            .join(Notebook)
            .filter(
                Notebook.user_id == user_id,
                NoteNode.type == "note",
                NoteNode.last_opened_at.is_not(None),
            )
            .order_by(
                NoteNode.last_opened_at.desc().nullslast(),
                NoteNode.updated_at.desc(),
            )
            .limit(limit)
            .all()
        )

    def discover(
        self,
        user_id: UUID,
        sort: str,
        notebook_id: Optional[UUID] = None,
        tag: Optional[str] = None,
        pinned: Optional[bool] = None,
        updated_after=None,
        updated_before=None,
        limit: int = 50,
    ) -> List[NoteNode]:
        query = (
            self.db.query(NoteNode)
            .join(Notebook)
            .filter(Notebook.user_id == user_id, NoteNode.type == "note")
        )
        if notebook_id is not None:
            query = query.filter(NoteNode.notebook_id == notebook_id)
        if tag is not None:
            normalized_tag = tag.strip()
            if not normalized_tag:
                return []
            escaped_tag = normalized_tag.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            tokenized_tags = func.coalesce(NoteNode.tags, "")
            query = query.filter(
                ("," + tokenized_tags + ",").like(f"%,{escaped_tag},%", escape="\\")
            )
        if pinned is not None:
            query = query.filter(NoteNode.is_pinned == pinned)
        if updated_after is not None:
            query = query.filter(NoteNode.updated_at >= updated_after)
        if updated_before is not None:
            query = query.filter(NoteNode.updated_at <= updated_before)

        sort_columns = {
            "last_opened": (NoteNode.last_opened_at.desc().nullslast(), NoteNode.updated_at.desc()),
            "updated": (NoteNode.updated_at.desc().nullslast(),),
            "created": (NoteNode.created_at.desc().nullslast(),),
            "title": (NoteNode.name.asc(),),
        }
        if sort not in sort_columns:
            raise ValueError("Unknown note sort")
        ordered_query = query.order_by(*sort_columns[sort], NoteNode.name.asc())
        return ordered_query.limit(limit).all()


class AttachmentRepository(BaseRepository[Attachment]):
    def __init__(self, db: Session):
        super().__init__(Attachment, db)

    def get_by_note(self, note_id: UUID) -> List[Attachment]:
        return self.db.query(Attachment).filter(Attachment.note_id == note_id).all()
