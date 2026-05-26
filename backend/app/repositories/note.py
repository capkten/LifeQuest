from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.note import Notebook, Folder, Note, Attachment
from app.repositories.base import BaseRepository


class NotebookRepository(BaseRepository[Notebook]):
    def __init__(self, db: Session):
        super().__init__(Notebook, db)

    def get_by_user(self, user_id: UUID) -> List[Notebook]:
        return self.db.query(Notebook).filter(Notebook.user_id == user_id).all()


class FolderRepository(BaseRepository[Folder]):
    def __init__(self, db: Session):
        super().__init__(Folder, db)

    def get_by_notebook(self, notebook_id: UUID) -> List[Folder]:
        return self.db.query(Folder).filter(Folder.notebook_id == notebook_id).all()

    def get_by_parent(self, parent_id: UUID) -> List[Folder]:
        return self.db.query(Folder).filter(Folder.parent_id == parent_id).all()


class NoteRepository(BaseRepository[Note]):
    def __init__(self, db: Session):
        super().__init__(Note, db)

    def get_by_folder(self, folder_id: UUID) -> List[Note]:
        return self.db.query(Note).filter(Note.folder_id == folder_id).all()

    def search(self, user_id: UUID, query: str) -> List[Note]:
        return (
            self.db.query(Note)
            .join(Folder)
            .join(Notebook)
            .filter(Notebook.user_id == user_id)
            .filter(
                (Note.title.contains(query)) |
                (Note.summary.contains(query)) |
                (Note.tags.contains(query))
            )
            .all()
        )


class AttachmentRepository(BaseRepository[Attachment]):
    def __init__(self, db: Session):
        super().__init__(Attachment, db)

    def get_by_note(self, note_id: UUID) -> List[Attachment]:
        return self.db.query(Attachment).filter(Attachment.note_id == note_id).all()
