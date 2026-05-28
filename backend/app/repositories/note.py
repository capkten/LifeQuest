# backend/app/repositories/note.py
from typing import List, Optional
from uuid import UUID

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


class AttachmentRepository(BaseRepository[Attachment]):
    def __init__(self, db: Session):
        super().__init__(Attachment, db)

    def get_by_note(self, note_id: UUID) -> List[Attachment]:
        return self.db.query(Attachment).filter(Attachment.note_id == note_id).all()
