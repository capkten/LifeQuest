# backend/app/api/notes.py
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from app.database import SessionLocal, get_db
from app.models.user import User
from app.models.note_sharing import NotebookMember
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
    NotebookMemberCreate,
    NotebookMemberResponse,
    NotebookMemberUpdate,
    CollaborationTicketResponse,
    node_to_response,
)
from app.services.note import NoteService
from app.services.note import NoteRevisionConflict
from app.api.auth import get_current_user
from app.services.auth import create_access_token, decode_access_token

router = APIRouter(prefix="/api/notes", tags=["notes"])


def _notebook_response(notebook, user_id: UUID, service: NoteService) -> NotebookResponse:
    access = service.get_notebook_access(notebook.id, user_id)
    role = access["role"] if access else "viewer"
    is_owner = bool(access and access["is_owner"])
    member_count = service.db.query(NotebookMember).filter(
        NotebookMember.notebook_id == notebook.id,
        NotebookMember.status == "active",
    ).count() + 1
    return NotebookResponse(
        id=notebook.id,
        user_id=notebook.user_id,
        name=notebook.name,
        description=notebook.description,
        icon=notebook.icon,
        created_at=notebook.created_at,
        role=role,
        is_owner=is_owner,
        member_count=member_count,
    )


def _require_notebook(service: NoteService, notebook_id: UUID, user_id: UUID, write: bool = False) -> dict:
    try:
        return service.require_notebook_access(notebook_id, user_id, write=write)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


def _require_owner(service: NoteService, notebook_id: UUID, user_id: UUID) -> dict:
    access = _require_notebook(service, notebook_id, user_id)
    if not access["is_owner"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    return access


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
    return [_notebook_response(notebook, current_user.id, service) for notebook in service.get_notebooks(current_user.id)]


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
def get_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    access = _require_notebook(service, notebook_id, current_user.id)
    return _notebook_response(access["notebook"], current_user.id, service)


@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
def update_notebook(
    notebook_id: UUID,
    notebook_in: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    access = _require_owner(service, notebook_id, current_user.id)
    notebook = access["notebook"]
    return service.notebook_repo.update(notebook, notebook_in.model_dump(exclude_unset=True))


@router.delete("/notebooks/{notebook_id}")
def delete_notebook(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    _require_owner(service, notebook_id, current_user.id)
    try:
        service.delete_notebook(notebook_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"message": "Notebook deleted"}


@router.get("/notebooks/{notebook_id}/members", response_model=List[NotebookMemberResponse])
def get_notebook_members(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    _require_notebook(service, notebook_id, current_user.id)
    return service.get_notebook_members(notebook_id, current_user.id)


@router.post("/notebooks/{notebook_id}/members", response_model=NotebookMemberResponse)
def add_notebook_member(
    notebook_id: UUID,
    member_in: NotebookMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    try:
        return service.add_notebook_member(
            notebook_id, current_user.id, member_in.username_or_email, member_in.role
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        status_code = 404 if str(exc) == "USER_NOT_FOUND" else 409
        raise HTTPException(status_code=status_code, detail=str(exc))


@router.patch("/notebooks/{notebook_id}/members/{member_id}", response_model=NotebookMemberResponse)
def update_notebook_member(
    notebook_id: UUID,
    member_id: UUID,
    member_in: NotebookMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    try:
        return service.update_notebook_member(
            notebook_id, current_user.id, member_id, member_in.role
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/notebooks/{notebook_id}/members/{member_id}")
def remove_notebook_member(
    notebook_id: UUID,
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    try:
        service.remove_notebook_member(notebook_id, current_user.id, member_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"message": "Member removed"}


# --- Node tree endpoints ---

@router.get("/notebooks/{notebook_id}/tree", response_model=List[TreeResponse])
def get_tree(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    access = _require_notebook(service, notebook_id, current_user.id)
    nodes = service.get_tree(notebook_id)
    tree = _build_tree(nodes, parent_id=None)
    return tree


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
    access = _require_notebook(service, notebook_id, current_user.id)
    return [node_to_response(node, access["role"]) for node in service.get_children(notebook_id, parent_id)]


@router.post("/notebooks/{notebook_id}/folders", response_model=NodeResponse)
def create_folder(
    notebook_id: UUID,
    folder_in: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    _require_notebook(service, notebook_id, current_user.id, write=True)
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
    _require_notebook(service, notebook_id, current_user.id, write=True)
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
    node = service.node_repo.get_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    access = _require_notebook(service, node.notebook_id, current_user.id, write=True)
    try:
        if node_in.name is not None:
            service.rename_node(node_id, node_in.name)
        if "parent_id" in node_in.model_fields_set:
            service.move_node(node_id, node_in.parent_id)
        return node_to_response(service.node_repo.get_by_id(node_id), access["role"])
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
    node = service.node_repo.get_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    _require_notebook(service, node.notebook_id, current_user.id, write=True)
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
    return [
        node_to_response(
            node,
            service.get_notebook_access(node.notebook_id, current_user.id)["role"],
        )
        for node in service.search_notes(current_user.id, query)
    ]


@router.get("/recent", response_model=List[NodeResponse])
def get_recent_notes(
    limit: int = Query(8, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    return [
        node_to_response(
            node,
            service.get_notebook_access(node.notebook_id, current_user.id)["role"],
        )
        for node in service.get_recent_notes(current_user.id, limit)
    ]


@router.get("/discover", response_model=List[NodeResponse])
def discover_notes(
    sort: Literal["last_opened", "updated", "created", "title"] = Query("last_opened"),
    notebook_id: Optional[UUID] = Query(None),
    tag: Optional[str] = Query(None, min_length=1),
    pinned: Optional[bool] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    updated_before: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    nodes = service.discover_notes(
        user_id=current_user.id,
        sort=sort,
        notebook_id=notebook_id,
        tag=tag,
        pinned=pinned,
        updated_after=updated_after,
        updated_before=updated_before,
        limit=limit,
    )
    return [
        node_to_response(
            node,
            service.get_notebook_access(node.notebook_id, current_user.id)["role"],
        )
        for node in nodes
    ]


@router.post("/{note_id}/open", response_model=NodeResponse)
def mark_note_opened(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    try:
        node = service.mark_note_opened(note_id, current_user.id)
        access = service.get_notebook_access(node.notebook_id, current_user.id)
        return node_to_response(node, access["role"])
    except ValueError:
        raise HTTPException(status_code=404, detail="Note not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")


@router.post("/{note_id}/collaboration-ticket", response_model=CollaborationTicketResponse)
def create_collaboration_ticket(
    note_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    try:
        access = service.require_node_access(note_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Note not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")
    ticket = create_access_token(
        {
            "sub": str(current_user.id),
            "scope": "note_collab",
            "note_id": str(note_id),
        },
        expires_delta=timedelta(minutes=2),
    )
    return {"ticket": ticket, "expires_in": 120, "can_edit": access["role"] in {"owner", "editor"}}


@router.websocket("/{note_id}/collab")
async def collaborate_on_note(
    websocket: WebSocket,
    note_id: UUID,
    db: Session = Depends(get_db),
):
    """Join a note collaboration room using a short-lived REST ticket."""
    ticket = websocket.query_params.get("ticket")
    payload = decode_access_token(ticket) if ticket else None
    if not payload or payload.get("scope") != "note_collab" or payload.get("note_id") != str(note_id):
        await websocket.close(code=4401)
        return

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        await websocket.close(code=4401)
        return

    try:
        service = NoteService(db)
        access = service.require_node_access(note_id, user_id)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=4401)
            return
        from app.collaboration import collaboration_manager
        await collaboration_manager.serve(
            websocket,
            note_id,
            user_id,
            user.username,
            access["role"],
            sessionmaker(bind=db.get_bind(), autoflush=False, autocommit=False),
        )
    except (ValueError, PermissionError):
        await websocket.close(code=4403)
    except WebSocketDisconnect:
        pass
    finally:
        db.close()


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
    access = _require_notebook(service, node.notebook_id, current_user.id)
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
        last_opened_at=getattr(node, "_viewer_last_opened_at", node.last_opened_at),
        content_revision=getattr(node, "content_revision", 1) or 1,
        updated_by=getattr(node, "updated_by", None),
        permission_role=access["role"],
        can_edit=access["role"] in {"owner", "editor"},
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
    node = service.node_repo.get_by_id(note_id)
    if not node:
        raise HTTPException(status_code=404, detail="Note not found")
    access = _require_notebook(service, node.notebook_id, current_user.id, write=True)
    try:
        return node_to_response(service.update_note(note_id, note_in, current_user.id), access["role"])
    except NoteRevisionConflict as conflict:
        return JSONResponse(
            status_code=409,
            content={
                "detail": {"code": "NOTE_CONFLICT", "message": "Note changed by another collaborator"},
                "current_revision": conflict.node.content_revision or 1,
                "current_content": conflict.content,
            },
        )
    except ValueError as e:
        detail = str(e)
        if "同名冲突" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)


UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "notes"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    note_id: UUID = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NoteService(db)
    try:
        service.require_node_access(note_id, current_user.id, write=True)
    except ValueError:
        raise HTTPException(status_code=404, detail="Note not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")

    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
    MAX_SIZE = 10 * 1024 * 1024  # 10MB

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_ext = Path(file.filename or "upload.png").suffix.removeprefix(".").lower() or "png"
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size must be under 10MB")

    filename = f"{uuid.uuid4()}.{file_ext}"
    file_path = UPLOAD_DIR / str(note_id) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        attachment = service.create_attachment(
            note_id=note_id,
            user_id=current_user.id,
            filename=Path(file.filename or filename).name,
            file_path=str(file_path),
            file_type=file.content_type,
            file_size=len(content),
        )
    except PermissionError:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=403, detail="Not authorized")
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    return {
        "id": str(attachment.id),
        "url": f"/api/notes/{note_id}/attachments/{attachment.id}",
    }


@router.get("/{note_id}/attachments/{attachment_id}")
def get_note_attachment(
    note_id: UUID,
    attachment_id: UUID,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Serve note images only after validating the requesting user's access.

    Markdown images are loaded by the browser and cannot attach the app's
    localStorage bearer header, so the frontend supplies the same short-lived
    access token as a query parameter at render time. The token is never
    stored in the note content.
    """
    payload = decode_access_token(token) if token else None
    try:
        user_id = UUID(payload["sub"]) if payload else None
    except (KeyError, TypeError, ValueError):
        user_id = None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    service = NoteService(db)
    try:
        attachment = service.get_attachment(note_id, attachment_id, user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Attachment not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Not authorized")

    file_path = Path(attachment.file_path or "")
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parents[2] / file_path
    try:
        file_path = file_path.resolve()
        upload_root = UPLOAD_DIR.resolve()
        file_path.relative_to(upload_root)
    except (OSError, ValueError):
        raise HTTPException(status_code=404, detail="Attachment not found")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(file_path, media_type=attachment.file_type or "application/octet-stream", filename=attachment.filename)
