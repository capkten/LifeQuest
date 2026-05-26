import os
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.note import (
    NotebookCreate,
    NotebookResponse,
    FolderCreate,
    FolderResponse,
    NoteCreate,
    NoteUpdate,
    NoteResponse,
)
from app.services.note import NoteService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/notes", tags=["notes"])

# Create notes directory if it doesn't exist
NOTES_DIR = "notes_data"
os.makedirs(NOTES_DIR, exist_ok=True)


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


@router.post("/folders", response_model=FolderResponse)
def create_folder(
    folder_in: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    return service.create_folder(folder_in)


@router.post("/", response_model=NoteResponse)
def create_note(
    note_in: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    # Create markdown file
    file_name = f"{note_in.folder_id}/{note_in.title}.md"
    file_path = os.path.join(NOTES_DIR, file_name)
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
    return service.get_notes(folder_id)


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
    return note


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

    # Delete file
    if note.file_path and os.path.exists(note.file_path):
        os.remove(note.file_path)

    service.delete_note(note_id)
    return {"message": "Note deleted"}


@router.get("/search/{query}", response_model=List[NoteResponse])
def search_notes(
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = NoteService(db)
    return service.search_notes(current_user.id, query)
