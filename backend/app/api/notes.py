# backend/app/api/notes.py
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.note import (
    NotebookCreate,
    NotebookUpdate,
    NotebookResponse,
    FolderCreate,
    NoteCreate,
    NoteUpdate,
    NodeUpdate,
    NodeResponse,
    NoteDetailResponse,
    TreeResponse,
)
from app.services.note import NoteService
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/notes", tags=["notes"])


# --- Notebook endpoints ---

@router.post("/notebooks", response_model=NotebookResponse)
def create_notebook(
    notebook_in: NotebookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    return service.create_notebook(current_user.id, notebook_in)


@router.get("/notebooks", response_model=List[NotebookResponse])
def get_notebooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    return service.get_notebooks(current_user.id)


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
def get_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    notebook = service.notebook_repo.get_by_id(notebook_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
def update_notebook(
    notebook_id: UUID,
    notebook_in: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    service.notebook_repo.delete(notebook_id)
    return {"message": "Notebook deleted"}


# --- Node tree endpoints ---

@router.get("/notebooks/{notebook_id}/tree", response_model=List[TreeResponse])
def get_tree(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    nodes = service.get_tree(notebook_id)
    return _build_tree(nodes, parent_id=None)


def _build_tree(nodes: list, parent_id) -> list:
    """Build a nested tree structure from a flat list of nodes."""
    children_map: dict = {}
    for n in nodes:
        key = n.parent_id  # None for root
        if key not in children_map:
            children_map[key] = []
        children_map[key].append(n)

    def build(pid):
        result = []
        for n in children_map.get(pid, []):
            result.append(TreeResponse(
                id=n.id,
                name=n.name,
                type=n.type,
                parent_id=n.parent_id,
                children=build(n.id),
            ))
        return result

    return build(parent_id)


@router.get("/notebooks/{notebook_id}/children", response_model=List[NodeResponse])
def get_children(
    notebook_id: UUID,
    parent_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return service.get_children(notebook_id, parent_id)


@router.post("/notebooks/{notebook_id}/folders", response_model=NodeResponse)
def create_folder(
    notebook_id: UUID,
    folder_in: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        return service.create_folder(notebook_id, current_user.id, folder_in)
    except ValueError as e:
        detail = str(e)
        if "同名冲突" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


@router.post("/notebooks/{notebook_id}/notes", response_model=NodeResponse)
def create_note(
    notebook_id: UUID,
    note_in: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_notebook_ownership(notebook_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        return service.create_note(notebook_id, current_user.id, note_in)
    except ValueError as e:
        detail = str(e)
        if "同名冲突" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


# --- Node operations ---

@router.patch("/nodes/{node_id}", response_model=NodeResponse)
def update_node(
    node_id: UUID,
    node_in: NodeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_node_ownership(node_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        if node_in.name is not None:
            service.rename_node(node_id, node_in.name)
        if node_in.parent_id is not None:
            service.move_node(node_id, node_in.parent_id)
        return service.node_repo.get_by_id(node_id)
    except ValueError as e:
        detail = str(e)
        if "同名冲突" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


@router.delete("/nodes/{node_id}")
def delete_node(
    node_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_node_ownership(node_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        service.delete_node(node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "Node deleted"}


# --- Note content ---

@router.get("/search", response_model=List[NodeResponse])
def search_notes(
    query: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    return service.search_notes(current_user.id, query)


@router.get("/{note_id}", response_model=NoteDetailResponse)
def get_note(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    node = service.node_repo.get_by_id(note_id)
    if not node or node.type != "note":
        raise HTTPException(status_code=404, detail="Note not found")
    if not service.verify_node_ownership(note_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    content = service.get_note_content(note_id)
    return NoteDetailResponse(
        id=node.id,
        notebook_id=node.notebook_id,
        parent_id=node.parent_id,
        type=node.type,
        name=node.name,
        path=node.path,
        content_path=node.content_path,
        summary=node.summary,
        tags=node.tags,
        is_pinned=node.is_pinned,
        word_count=node.word_count,
        created_at=node.created_at,
        updated_at=node.updated_at,
        content=content,
    )


@router.put("/{note_id}", response_model=NodeResponse)
def update_note(
    note_id: UUID,
    note_in: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    if not service.verify_node_ownership(note_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    try:
        return service.update_note(note_id, note_in)
    except ValueError as e:
        detail = str(e)
        if "同名冲突" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


UPLOAD_DIR = Path("uploads/notes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = UPLOAD_DIR / filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"url": f"/uploads/notes/{filename}"}
