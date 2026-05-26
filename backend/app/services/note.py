import os
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.note import Notebook, Folder, Note, Attachment
from app.repositories.note import (
    NotebookRepository,
    FolderRepository,
    NoteRepository,
    AttachmentRepository,
)
from app.schemas.note import (
    NotebookCreate,
    FolderCreate,
    NoteCreate,
    NoteUpdate,
)


class NoteService:
    def __init__(self, db: Session):
        self.notebook_repo = NotebookRepository(db)
        self.folder_repo = FolderRepository(db)
        self.note_repo = NoteRepository(db)
        self.attachment_repo = AttachmentRepository(db)

    # Notebook operations
    def create_notebook(self, user_id: UUID, notebook_in: NotebookCreate) -> Notebook:
        data = notebook_in.model_dump()
        data["user_id"] = user_id
        return self.notebook_repo.create(data)

    def get_notebooks(self, user_id: UUID) -> List[Notebook]:
        return self.notebook_repo.get_by_user(user_id)

    # Folder operations
    def create_folder(self, folder_in: FolderCreate) -> Folder:
        data = folder_in.model_dump()
        return self.folder_repo.create(data)

    def get_folders(self, notebook_id: UUID) -> List[Folder]:
        return self.folder_repo.get_by_notebook(notebook_id)

    # Note operations
    def create_note(self, note_in: NoteCreate, file_path: str) -> Note:
        data = note_in.model_dump(exclude={"content"})
        data["file_path"] = file_path
        data["word_count"] = len(note_in.content) if note_in.content else 0
        return self.note_repo.create(data)

    def get_notes(self, folder_id: UUID) -> List[Note]:
        return self.note_repo.get_by_folder(folder_id)

    def get_note(self, note_id: UUID) -> Optional[Note]:
        return self.note_repo.get_by_id(note_id)

    def update_note(self, note: Note, note_in: NoteUpdate, file_path: Optional[str] = None) -> Note:
        update_data = note_in.model_dump(exclude_unset=True, exclude={"content"})
        if file_path:
            update_data["file_path"] = file_path
        if note_in.content is not None:
            update_data["word_count"] = len(note_in.content)
        return self.note_repo.update(note, update_data)

    def delete_note(self, note_id: UUID) -> bool:
        return self.note_repo.delete(note_id)

    def search_notes(self, user_id: UUID, query: str) -> List[Note]:
        return self.note_repo.search(user_id, query)

    # Attachment operations
    def create_attachment(self, note_id: UUID, filename: str, file_path: str, file_type: str, file_size: int) -> Attachment:
        return self.attachment_repo.create({
            "note_id": note_id,
            "filename": filename,
            "file_path": file_path,
            "file_type": file_type,
            "file_size": file_size,
        })

    def get_attachments(self, note_id: UUID) -> List[Attachment]:
        return self.attachment_repo.get_by_note(note_id)
