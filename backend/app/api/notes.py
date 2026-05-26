import os
import pathlib
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.note import (
    NotebookCreate,
    NotebookUpdate,
    NotebookResponse,
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    NoteCreate,
    NoteUpdate,
    NoteResponse,
)
from app.services.note import NoteService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/notes", tags=["notes"])

# Create notes directory if it doesn't exist (absolute path)
BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
NOTES_DIR = BACKEND_DIR / "notes_data"
NOTES_DIR.mkdir(exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Remove path separators and other dangerous characters from a filename."""
    return re.sub(r'[/\\:*?"<>|]', '_', name)


@router.post("/notebooks", response_model=NotebookResponse)
def create_notebook(
    notebook_in: NotebookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    return service.create_notebook(current_user.id, notebook_in)


@router.get("/notebooks", response_model=List[NotebookResponse])
def get_notebooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    return service.get_notebooks(current_user.id)


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
def get_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    notebook = service.notebook_repo.get_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


@router.get("/notebooks/{notebook_id}/folders", response_model=List[FolderResponse])
def get_folders_by_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return service.get_folders(notebook_id)


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
def update_notebook(
    notebook_id: UUID,
    notebook_in: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    notebook = service.notebook_repo.get_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return service.notebook_repo.update(notebook, notebook_in.model_dump(exclude_unset=True))


@router.delete("/notebooks/{notebook_id}")
def delete_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    service.notebook_repo.delete(notebook_id)
    return {"message": "Notebook deleted"}


@router.post("/folders", response_model=FolderResponse)
def create_folder(
    folder_in: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(folder_in.notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return service.create_folder(folder_in)


@router.put("/folders/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: UUID,
    folder_in: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_folder_ownership(folder_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    folder = service.folder_repo.get_by_id(folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return service.folder_repo.update(folder, folder_in.model_dump(exclude_unset=True))


@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_folder_ownership(folder_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    service.folder_repo.delete(folder_id)
    return {"message": "Folder deleted"}


@router.post("/", response_model=NoteResponse)
def create_note(
    note_in: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_folder_ownership(note_in.folder_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    # Create markdown file (sanitize title to prevent path traversal)
    file_name = f"{note_in.folder_id}/{sanitize_filename(note_in.title)}.md"
    file_path = str(NOTES_DIR / file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(note_in.content or "")

    return service.create_note(note_in, file_path)


@router.get("/folder/{folder_id}", response_model=List[NoteResponse])
def get_notes_by_folder(
    folder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    if not service.verify_folder_ownership(folder_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return service.get_notes(folder_id)


@router.get("/search", response_model=List[NoteResponse])
def search_notes(
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    return service.search_notes(current_user.id, query)


@router.get("/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    note = service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not service.verify_note_ownership(note, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Read file content
    content = ""
    if note.file_path and os.path.exists(note.file_path):
        with open(note.file_path, "r", encoding="utf-8") as f:
            content = f.read()

    # Create response with content
    note_dict = {
        "id": note.id,
        "folder_id": note.folder_id,
        "title": note.title,
        "summary": note.summary,
        "tags": note.tags,
        "is_pinned": note.is_pinned,
        "file_path": note.file_path,
        "content": content,
        "word_count": note.word_count,
        "created_at": note.created_at,
        "updated_at": note.updated_at
    }
    return note_dict


@router.put("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: UUID,
    note_in: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    note = service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not service.verify_note_ownership(note, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    file_path = note.file_path
    if note_in.content is not None and file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(note_in.content)

    return service.update_note(note, note_in, file_path)


@router.delete("/{note_id}")
def delete_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    note = service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not service.verify_note_ownership(note, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete file first; only proceed with DB deletion if file operation succeeds
    if note.file_path and os.path.exists(note.file_path):
        try:
            os.remove(note.file_path)
        except OSError:
            raise HTTPException(status_code=500, detail="Failed to delete note file")

    service.delete_note(note_id)
    return {"message": "Note deleted"}
