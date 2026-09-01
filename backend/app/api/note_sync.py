import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.note import Notebook
from app.models.note_node import NoteNode
from app.models.note_sync import NoteSyncChange, NoteSyncConflict, NoteSyncOperation
from app.models.user import User
from app.schemas.note import FolderCreate, NoteCreate, NoteUpdate
from app.schemas.note_sync import (
    SyncApplyRequest,
    SyncApplyResponse,
    SyncApplyResult,
    SyncChangeResponse,
    SyncChangesResponse,
    SyncConflictListResponse,
    SyncConflictResolveRequest,
    SyncContentRequest,
    SyncContentResponse,
    SyncManifestItem,
    SyncManifestResponse,
)
from app.services.note import NoteRevisionConflict, NoteService, _compute_path

router = APIRouter(prefix="/api/notes", tags=["note-sync"])


def _require_owner(service: NoteService, notebook_id: UUID, user_id: UUID) -> Notebook:
    access = service.get_notebook_access(notebook_id, user_id)
    if not access:
        if service.notebook_repo.get_by_id(notebook_id):
            raise HTTPException(status_code=403, detail="Only the notebook owner can sync")
        raise HTTPException(status_code=404, detail="Notebook not found")
    if not access["is_owner"]:
        raise HTTPException(status_code=403, detail="Only the notebook owner can sync")
    return access["notebook"]


def _validate_sync_path(path: str | None) -> None:
    if path is None:
        return
    if not path.startswith("/") or "\\" in path or "//" in path:
        raise ValueError("INVALID_SYNC_PATH")
    parts = path.split("/")[1:]
    if not parts or any(not part or part in {".", ".."} for part in parts):
        raise ValueError("INVALID_SYNC_PATH")
    if any(part.startswith(".") for part in parts):
        raise ValueError("INVALID_SYNC_PATH")


def _validate_local_path(path: str | None) -> None:
    if path is None:
        return
    if path.startswith("/") or "\\" in path or "//" in path:
        raise ValueError("INVALID_SYNC_PATH")
    parts = path.split("/")
    if not parts or any(not part or part in {".", ".."} for part in parts):
        raise ValueError("INVALID_SYNC_PATH")
    if any(part.startswith(".") for part in parts):
        raise ValueError("INVALID_SYNC_PATH")


def _manifest_item(service: NoteService, node: NoteNode) -> SyncManifestItem:
    return SyncManifestItem(
        node_id=node.id,
        parent_id=node.parent_id,
        node_type=node.type,
        name=node.name,
        path=node.path,
        content_revision=(node.content_revision if node.type == "note" else None),
        content_hash=service.node_content_hash(node),
        updated_at=node.updated_at or datetime.now(timezone.utc),
    )


def _change_response(change: NoteSyncChange) -> SyncChangeResponse:
    return SyncChangeResponse.model_validate(change)


def _result_json(result: SyncApplyResult) -> str:
    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False)


def _stored_result(operation: NoteSyncOperation) -> SyncApplyResult:
    payload = json.loads(operation.result_json)
    payload["status"] = "already_applied"
    return SyncApplyResult.model_validate(payload)


def _error_result(operation_id: str, code: str, message: str) -> SyncApplyResult:
    return SyncApplyResult(
        client_operation_id=operation_id,
        status="rejected",
        error_code=code,
        message=message,
    )


def _store_result(service: NoteService, notebook_id: UUID, operation, result: SyncApplyResult) -> SyncApplyResult:
    service.db.add(NoteSyncOperation(
        notebook_id=notebook_id,
        client_operation_id=operation.client_operation_id,
        operation=operation.kind,
        result_json=_result_json(result),
    ))
    service.db.commit()
    return result


def _expected_path(service: NoteService, node: NoteNode, parent_id: UUID | None) -> str:
    parent_path, _ = service._get_parent_path(parent_id, node.notebook_id)
    return _compute_path(parent_path, node.name, node.type == "note")


def _conflict_for(
    db: Session,
    notebook_id: UUID,
    node: NoteNode | None,
    operation,
    remote_revision: int | None,
) -> NoteSyncConflict:
    conflict = NoteSyncConflict(
        notebook_id=notebook_id,
        node_id=node.id if node else operation.node_id,
        local_path=operation.local_path or operation.path or (node.path if node else "/"),
        base_hash=operation.base_hash,
        remote_revision=remote_revision,
        status="open",
    )
    db.add(conflict)
    db.flush()
    return conflict


def _check_base_hash(service: NoteService, node: NoteNode, operation) -> bool:
    if operation.base_hash is None:
        return True
    return service.node_content_hash(node) == operation.base_hash


@router.get(
    "/notebooks/{notebook_id}/sync/manifest",
    response_model=SyncManifestResponse,
)
def get_manifest(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    notebook = _require_owner(service, notebook_id, current_user.id)
    nodes = sorted(service.get_tree(notebook_id), key=lambda node: node.path)
    return SyncManifestResponse(
        notebook_id=notebook_id,
        revision=notebook.sync_revision or 0,
        items=[_manifest_item(service, node) for node in nodes],
    )


@router.get(
    "/notebooks/{notebook_id}/sync/changes",
    response_model=SyncChangesResponse,
)
def get_changes(
    notebook_id: UUID,
    after: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = NoteService(db)
    notebook = _require_owner(service, notebook_id, current_user.id)
    rows = (
        db.query(NoteSyncChange)
        .filter(
            NoteSyncChange.notebook_id == notebook_id,
            NoteSyncChange.sequence > after,
        )
        .order_by(NoteSyncChange.sequence.asc())
        .limit(limit + 1)
        .all()
    )
    has_more = len(rows) > limit
    rows = rows[:limit]
    cursor = rows[-1].sequence if rows else after
    return SyncChangesResponse(
        notebook_id=notebook_id,
        cursor=cursor,
        changes=[_change_response(row) for row in rows],
        has_more=has_more,
    )


@router.post(
    "/notebooks/{notebook_id}/sync/content",
    response_model=SyncContentResponse,
)
def get_content(
    notebook_id: UUID,
    body: SyncContentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(NoteService(db), notebook_id, current_user.id)
    if len(set(body.node_ids)) != len(body.node_ids):
        raise HTTPException(status_code=400, detail="DUPLICATE_NODE_ID")
    nodes = (
        db.query(NoteNode)
        .filter(NoteNode.notebook_id == notebook_id, NoteNode.id.in_(body.node_ids))
        .all()
    )
    node_map = {node.id: node for node in nodes}
    if len(node_map) != len(body.node_ids) or any(node.type != "note" for node in nodes):
        raise HTTPException(status_code=404, detail="Note not found")
    service = NoteService(db)
    return SyncContentResponse(
        notebook_id=notebook_id,
        contents={str(node_id): service.get_note_content(node_id) for node_id in body.node_ids},
    )


def _apply_one(service: NoteService, notebook_id: UUID, operation) -> SyncApplyResult:
    operation_id = operation.client_operation_id
    existing = service.db.query(NoteSyncOperation).filter(
        NoteSyncOperation.notebook_id == notebook_id,
        NoteSyncOperation.client_operation_id == operation_id,
    ).first()
    if existing:
        return _stored_result(existing)

    try:
        _validate_sync_path(operation.path)
        _validate_local_path(operation.local_path)
    except ValueError as exc:
        return _store_result(service, notebook_id, operation, _error_result(operation_id, str(exc), "The sync path is invalid"))

    node = service.node_repo.get_by_id(operation.node_id) if operation.node_id else None
    if node and node.notebook_id != notebook_id:
        node = None

    try:
        if operation.kind == "create_folder":
            if not operation.name:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "NAME_REQUIRED", "Folder name is required"))
            if operation.name.startswith("."):
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "INVALID_NAME", "Hidden names are reserved"))
            notebook = service.notebook_repo.get_by_id(notebook_id)
            expected_path = _compute_path(
                service._get_parent_path(operation.parent_id, notebook_id)[0],
                operation.name,
                False,
            )
            if operation.path and operation.path != expected_path:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "PATH_MISMATCH", "Path does not match the folder"))
            node = service.create_folder(
                notebook_id,
                notebook.user_id,
                FolderCreate(parent_id=operation.parent_id, name=operation.name),
                commit=False,
            )
        elif operation.kind == "create_note":
            if not operation.name:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "NAME_REQUIRED", "Note name is required"))
            note_name = operation.name.removesuffix(".md")
            if note_name.startswith("."):
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "INVALID_NAME", "Hidden names are reserved"))
            notebook = service.notebook_repo.get_by_id(notebook_id)
            expected_path = _compute_path(
                service._get_parent_path(operation.parent_id, notebook_id)[0],
                note_name,
                True,
            )
            if operation.path and operation.path != expected_path:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "PATH_MISMATCH", "Path does not match the note"))
            node = service.create_note(
                notebook_id,
                notebook.user_id,
                NoteCreate(
                    parent_id=operation.parent_id,
                    title=note_name,
                    content=operation.content or "",
                    summary=operation.summary,
                    tags=operation.tags,
                ),
                commit=False,
            )
        elif operation.kind == "update_note":
            if not node:
                if operation.base_revision is not None:
                    conflict = _conflict_for(
                        service.db,
                        notebook_id,
                        None,
                        operation,
                        operation.base_revision,
                    )
                    result = SyncApplyResult(
                        client_operation_id=operation_id,
                        status="conflict",
                        error_code="REMOTE_DELETED",
                        message="The remote note was deleted before this upload",
                        conflict_id=conflict.id,
                    )
                    service.db.add(NoteSyncOperation(
                        notebook_id=notebook_id,
                        client_operation_id=operation_id,
                        operation=operation.kind,
                        result_json=_result_json(result),
                    ))
                    service.db.commit()
                    return result
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "NOT_FOUND", "Note not found"))
            if node.type != "note":
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "NOT_FOUND", "Note not found"))
            if operation.base_revision is None:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "BASE_REVISION_REQUIRED", "Base revision is required"))
            if operation.path and operation.path != node.path:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "PATH_MISMATCH", "Path does not match the note"))
            if not _check_base_hash(service, node, operation):
                conflict = _conflict_for(service.db, notebook_id, node, operation, node.content_revision)
                result = SyncApplyResult(
                    client_operation_id=operation_id,
                    status="conflict",
                    node=_manifest_item(service, node),
                    error_code="BASE_HASH_MISMATCH",
                    message="The remote note changed before this upload",
                    conflict_id=conflict.id,
                )
                service.db.add(NoteSyncOperation(
                    notebook_id=notebook_id,
                    client_operation_id=operation_id,
                    operation=operation.kind,
                    result_json=_result_json(result),
                ))
                service.db.commit()
                return result
            node = service.update_note(
                node.id,
                NoteUpdate(
                    content=operation.content,
                    summary=operation.summary,
                    tags=operation.tags,
                    base_revision=operation.base_revision,
                ),
                service.notebook_repo.get_by_id(notebook_id).user_id,
                commit=False,
            )
        elif operation.kind == "move_node":
            if not node:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "NOT_FOUND", "Node not found"))
            if operation.path and operation.path != _expected_path(service, node, operation.parent_id):
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "PATH_MISMATCH", "Path does not match the moved node"))
            node = service.move_node(node.id, operation.parent_id, commit=False)
        elif operation.kind == "delete_node":
            if not node:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "NOT_FOUND", "Node not found"))
            if operation.path and operation.path != node.path:
                return _store_result(service, notebook_id, operation, _error_result(operation_id, "PATH_MISMATCH", "Path does not match the deleted node"))
            service.delete_node(node.id, commit=False)
            node = None

        result = SyncApplyResult(
            client_operation_id=operation_id,
            status="applied",
            node=_manifest_item(service, node) if node else None,
        )
        service.db.add(NoteSyncOperation(
            notebook_id=notebook_id,
            client_operation_id=operation_id,
            operation=operation.kind,
            result_json=_result_json(result),
        ))
        service.db.commit()
        return result
    except NoteRevisionConflict:
        current = service.node_repo.get_by_id(operation.node_id) if operation.node_id else None
        conflict = _conflict_for(
            service.db,
            notebook_id,
            current,
            operation,
            current.content_revision if current else None,
        )
        result = SyncApplyResult(
            client_operation_id=operation_id,
            status="conflict",
            node=_manifest_item(service, current) if current else None,
            error_code="STALE_REVISION",
            message="The remote note changed before this upload",
            conflict_id=conflict.id,
        )
        service.db.add(NoteSyncOperation(
            notebook_id=notebook_id,
            client_operation_id=operation_id,
            operation=operation.kind,
            result_json=_result_json(result),
        ))
        service.db.commit()
        return result
    except (ValueError, TypeError) as exc:
        service.db.rollback()
        detail = str(exc)
        if "同名冲突" in detail:
            code = "NAME_CONFLICT"
        elif "reserved" in detail.lower() or "invalid" in detail.lower():
            code = "INVALID_NAME"
        elif "not found" in detail.lower():
            code = "NOT_FOUND"
        else:
            code = detail or "INVALID_OPERATION"
        result = _error_result(operation_id, code, detail or "The sync operation was rejected")
        service.db.add(NoteSyncOperation(
            notebook_id=notebook_id,
            client_operation_id=operation_id,
            operation=operation.kind,
            result_json=_result_json(result),
        ))
        service.db.commit()
        return result


@router.post(
    "/notebooks/{notebook_id}/sync/apply",
    response_model=SyncApplyResponse,
)
def apply_operations(
    notebook_id: UUID,
    body: SyncApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notebook = _require_owner(NoteService(db), notebook_id, current_user.id)
    service = NoteService(db)
    results = [_apply_one(service, notebook_id, operation) for operation in body.operations]
    db.refresh(notebook)
    return SyncApplyResponse(
        notebook_id=notebook_id,
        revision=notebook.sync_revision or 0,
        results=results,
    )


@router.get(
    "/notebooks/{notebook_id}/sync/conflicts",
    response_model=SyncConflictListResponse,
)
def list_conflicts(
    notebook_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_owner(NoteService(db), notebook_id, current_user.id)
    conflicts = (
        db.query(NoteSyncConflict)
        .filter(NoteSyncConflict.notebook_id == notebook_id)
        .order_by(NoteSyncConflict.created_at.desc())
        .all()
    )
    return SyncConflictListResponse(notebook_id=notebook_id, conflicts=conflicts)


@router.post(
    "/notebooks/{notebook_id}/sync/conflicts/{conflict_id}/resolve",
    response_model=SyncApplyResponse,
)
def resolve_conflict(
    notebook_id: UUID,
    conflict_id: UUID,
    body: SyncConflictResolveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notebook = _require_owner(NoteService(db), notebook_id, current_user.id)
    conflict = db.query(NoteSyncConflict).filter(
        NoteSyncConflict.id == conflict_id,
        NoteSyncConflict.notebook_id == notebook_id,
    ).first()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict not found")
    if conflict.status != "open":
        raise HTTPException(status_code=409, detail="Conflict is already resolved")

    service = NoteService(db)
    node = service.node_repo.get_by_id(conflict.node_id) if conflict.node_id else None
    if node and node.notebook_id != notebook_id:
        node = None
    if body.resolution in {"keep_local", "merged_content"}:
        if body.content is None:
            raise HTTPException(status_code=400, detail="Resolution content is required")
        if node:
            if node.type != "note":
                raise HTTPException(status_code=400, detail="Resolution target is not a note")
            try:
                node = service.update_note(
                    node.id,
                    NoteUpdate(content=body.content, base_revision=body.base_revision or node.content_revision),
                    current_user.id,
                )
            except NoteRevisionConflict as exc:
                raise HTTPException(status_code=409, detail={"code": "STALE_REVISION", "message": str(exc)})
        else:
            relative_path = conflict.local_path.lstrip("/")
            try:
                _validate_local_path(relative_path)
            except ValueError:
                raise HTTPException(status_code=400, detail="Conflict path is invalid")
            if not relative_path.lower().endswith(".md"):
                raise HTTPException(status_code=400, detail="Conflict path is not a note")
            parts = relative_path.split("/")
            title = parts[-1][:-3]
            parent_path = "/" + "/".join(parts[:-1]) if len(parts) > 1 else None
            parent = None
            if parent_path:
                parent = next(
                    (
                        candidate
                        for candidate in service.get_tree(notebook_id)
                        if candidate.type == "folder" and candidate.path == parent_path
                    ),
                    None,
                )
                if not parent:
                    raise HTTPException(status_code=400, detail="Conflict parent folder not found")
            try:
                node = service.create_note(
                    notebook_id,
                    notebook.user_id,
                    NoteCreate(parent_id=parent.id if parent else None, title=title, content=body.content),
                    commit=False,
                )
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc))
    conflict.status = "resolved"
    conflict.resolution = body.resolution
    conflict.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notebook)
    result = SyncApplyResult(
        client_operation_id=f"conflict:{conflict_id}:{uuid4()}",
        status="applied",
        node=_manifest_item(service, node) if node else None,
    )
    return SyncApplyResponse(notebook_id=notebook_id, revision=notebook.sync_revision or 0, results=[result])
