# backend/app/services/note.py
import os
import pathlib
import re
import shutil
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Sequence, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, inspect, text
from sqlalchemy.orm import Session

from app.models.note import Notebook, Attachment
from app.models.note_node import NoteNode, normalize_name
from app.models.note_sharing import NotebookMember, NoteUserActivity, NoteCollabDocument, NoteCollabEvent
from app.models.user import User
from app.repositories.note import NotebookRepository, NoteNodeRepository, AttachmentRepository
from app.schemas.note import (
    NotebookCreate,
    FolderCreate,
    NoteCreate,
    NoteUpdate,
    NodeUpdate,
)
from app.services.achievement import AchievementService

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
NOTES_DIR = BACKEND_DIR / "notes_data"
logger = logging.getLogger(__name__)


class NoteRevisionConflict(ValueError):
    def __init__(self, node: NoteNode, content: str):
        super().__init__("NOTE_CONFLICT")
        self.node = node
        self.content = content


def canonicalize_tags(tags: Optional[str]) -> Optional[str]:
    if tags is None:
        return None
    return ",".join(token.strip() for token in tags.split(",") if token.strip())


def sanitize_filename(name: str) -> str:
    """Remove path separators and other dangerous characters from a filename."""
    return re.sub(r'[/\\:*?"<>|]', '_', name)


def _compute_path(parent_path: Optional[str], name: str, is_note: bool) -> str:
    """Compute the materialized path for a node."""
    display_name = f"{name}.md" if is_note else name
    if parent_path:
        return f"{parent_path}/{display_name}"
    return f"/{display_name}"


def _compute_content_path(user_id: UUID, notebook_id: UUID, path: str) -> str:
    """Compute the filesystem content_path for a note."""
    return str(NOTES_DIR / str(user_id) / str(notebook_id) / path.lstrip("/"))


def _write_content_atomically(content_path: str, content: str) -> None:
    target = pathlib.Path(content_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, target)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def _attachment_file_path(file_path: Optional[str]) -> Optional[pathlib.Path]:
    if not file_path:
        return None
    path = pathlib.Path(file_path)
    return path if path.is_absolute() else BACKEND_DIR / path


class NoteService:
    def __init__(self, db: Session):
        self.db = db
        self.notebook_repo = NotebookRepository(db)
        self.node_repo = NoteNodeRepository(db)
        self.attachment_repo = AttachmentRepository(db)
        self.achievement_service = AchievementService(db)

    # --- Ownership verification ---

    def get_notebook_access(self, notebook_id: UUID, user_id: UUID) -> Optional[dict]:
        notebook = self.notebook_repo.get_by_id(notebook_id)
        if not notebook:
            return None
        if notebook.user_id == user_id:
            return {"notebook": notebook, "role": "owner", "is_owner": True}

        member = self.db.query(NotebookMember).filter(
            NotebookMember.notebook_id == notebook_id,
            NotebookMember.user_id == user_id,
            NotebookMember.status == "active",
        ).first()
        if not member:
            return None
        return {"notebook": notebook, "role": member.role, "is_owner": False, "member": member}

    def require_notebook_access(self, notebook_id: UUID, user_id: UUID, write: bool = False) -> dict:
        access = self.get_notebook_access(notebook_id, user_id)
        if not access or (write and access["role"] == "viewer"):
            raise PermissionError("Not authorized")
        return access

    def require_node_access(self, node_id: UUID, user_id: UUID, write: bool = False) -> dict:
        node = self.node_repo.get_by_id(node_id)
        if not node:
            raise ValueError("Note not found")
        access = self.require_notebook_access(node.notebook_id, user_id, write=write)
        access["node"] = node
        return access

    def verify_notebook_ownership(self, notebook_id: UUID, user_id: UUID) -> bool:
        """Backward-compatible access check used by the MCP adapter.

        The old note API only had owners, so the MCP helper kept this name.
        It now means that the user can access the notebook as a member too.
        Destructive owner-only operations must check ``is_owner`` explicitly.
        """
        return self.get_notebook_access(notebook_id, user_id) is not None

    def verify_notebook_owner(self, notebook_id: UUID, user_id: UUID) -> bool:
        access = self.get_notebook_access(notebook_id, user_id)
        return bool(access and access["is_owner"])

    def verify_node_ownership(self, node_id: UUID, user_id: UUID) -> bool:
        node = self.node_repo.get_by_id(node_id)
        if not node:
            return False
        return self.get_notebook_access(node.notebook_id, user_id) is not None

    # --- Notebook operations ---

    def create_notebook(self, user_id: UUID, notebook_in: NotebookCreate) -> Notebook:
        data = notebook_in.model_dump()
        data["user_id"] = user_id
        return self.notebook_repo.create(data)

    def get_notebooks(self, user_id: UUID) -> List[Notebook]:
        owned = self.notebook_repo.get_by_user(user_id)
        shared = (
            self.db.query(Notebook)
            .join(NotebookMember, NotebookMember.notebook_id == Notebook.id)
            .filter(
                NotebookMember.user_id == user_id,
                NotebookMember.status == "active",
            )
            .all()
        )
        seen = set()
        result = []
        for notebook in [*owned, *shared]:
            if notebook.id in seen:
                continue
            seen.add(notebook.id)
            access = self.get_notebook_access(notebook.id, user_id)
            notebook._access_role = access["role"] if access else "viewer"
            notebook._is_owner = bool(access and access["is_owner"])
            notebook._member_count = self.db.query(NotebookMember).filter(
                NotebookMember.notebook_id == notebook.id,
                NotebookMember.status == "active",
            ).count() + 1
            result.append(notebook)
        return result

    def get_notebook_members(self, notebook_id: UUID, user_id: UUID) -> List[dict]:
        access = self.require_notebook_access(notebook_id, user_id)
        owner = self.db.query(User).filter(User.id == access["notebook"].user_id).first()
        members = []
        if owner:
            members.append({
                "id": owner.id,
                "user_id": owner.id,
                "username": owner.username,
                "email": owner.email,
                "role": "owner",
                "status": "active",
                "created_at": access["notebook"].created_at,
            })
        rows = (
            self.db.query(NotebookMember, User)
            .join(User, User.id == NotebookMember.user_id)
            .filter(NotebookMember.notebook_id == notebook_id)
            .order_by(NotebookMember.created_at.asc())
            .all()
        )
        for member, target in rows:
            members.append({
                "id": member.id,
                "user_id": target.id,
                "username": target.username,
                "email": target.email,
                "role": member.role,
                "status": member.status,
                "created_at": member.created_at,
            })
        return members

    def add_notebook_member(self, notebook_id: UUID, actor_id: UUID, identifier: str, role: str) -> dict:
        access = self.require_notebook_access(notebook_id, actor_id)
        if not access["is_owner"]:
            raise PermissionError("Not authorized")
        normalized = identifier.strip()
        target = self.db.query(User).filter(
            or_(User.username == normalized, User.email == normalized)
        ).first()
        if not target:
            raise ValueError("USER_NOT_FOUND")
        if target.id == access["notebook"].user_id:
            raise ValueError("OWNER_ALREADY_MEMBER")
        existing = self.db.query(NotebookMember).filter(
            NotebookMember.notebook_id == notebook_id,
            NotebookMember.user_id == target.id,
        ).first()
        if existing:
            raise ValueError("MEMBER_ALREADY_EXISTS")
        member = NotebookMember(
            notebook_id=notebook_id,
            user_id=target.id,
            role=role,
            status="active",
            invited_by=actor_id,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return {
            "id": member.id,
            "user_id": target.id,
            "username": target.username,
            "email": target.email,
            "role": member.role,
            "status": member.status,
            "created_at": member.created_at,
        }

    def update_notebook_member(self, notebook_id: UUID, actor_id: UUID, target_id: UUID, role: str) -> dict:
        access = self.require_notebook_access(notebook_id, actor_id)
        if not access["is_owner"]:
            raise PermissionError("Not authorized")
        member = self.db.query(NotebookMember).filter(
            NotebookMember.notebook_id == notebook_id,
            NotebookMember.user_id == target_id,
        ).first()
        if not member:
            raise ValueError("MEMBER_NOT_FOUND")
        member.role = role
        self.db.commit()
        target = self.db.query(User).filter(User.id == target_id).first()
        self.db.refresh(member)
        return {
            "id": member.id,
            "user_id": target.id,
            "username": target.username,
            "email": target.email,
            "role": member.role,
            "status": member.status,
            "created_at": member.created_at,
        }

    def remove_notebook_member(self, notebook_id: UUID, actor_id: UUID, target_id: UUID) -> None:
        access = self.require_notebook_access(notebook_id, actor_id)
        if not access["is_owner"]:
            raise PermissionError("Not authorized")
        member = self.db.query(NotebookMember).filter(
            NotebookMember.notebook_id == notebook_id,
            NotebookMember.user_id == target_id,
        ).first()
        if not member:
            raise ValueError("MEMBER_NOT_FOUND")
        self.db.delete(member)
        self.db.commit()

    def delete_notebook(self, notebook_id: UUID) -> None:
        notebook = self.notebook_repo.get_by_id(notebook_id)
        if not notebook:
            raise ValueError("Notebook not found")

        root_nodes = [
            node for node in self.node_repo.get_by_notebook(notebook_id)
            if node.parent_id is None
        ]
        for node in root_nodes:
            self.delete_node(node.id)

        self.db.query(NotebookMember).filter(
            NotebookMember.notebook_id == notebook_id,
        ).delete(synchronize_session=False)
        self.db.delete(notebook)
        self.db.commit()

    # --- Node tree operations ---

    def get_tree(self, notebook_id: UUID) -> List[NoteNode]:
        return self.node_repo.get_tree(notebook_id)

    def get_children(self, notebook_id: UUID, parent_id: Optional[UUID]) -> List[NoteNode]:
        return self.node_repo.get_children(notebook_id, parent_id)

    def _get_parent_path(self, parent_id: Optional[UUID], notebook_id: UUID) -> tuple:
        """Return (parent_path, parent_node) for a given parent_id."""
        if parent_id is None:
            return "", None
        parent = self.node_repo.get_by_id(parent_id)
        if not parent or parent.notebook_id != notebook_id:
            raise ValueError("Parent node not found or does not belong to this notebook")
        if parent.type != "folder":
            raise ValueError("Cannot create children under a note")
        return parent.path, parent

    def create_folder(self, notebook_id: UUID, user_id: UUID, folder_in: FolderCreate) -> NoteNode:
        norm = normalize_name(folder_in.name)
        parent_path, _ = self._get_parent_path(folder_in.parent_id, notebook_id)

        if self.node_repo.check_name_conflict(notebook_id, folder_in.parent_id, norm):
            raise ValueError("同名冲突: 当前目录已存在同名条目")

        path = _compute_path(parent_path, folder_in.name.strip(), is_note=False)
        node = NoteNode(
            id=uuid4(),
            notebook_id=notebook_id,
            parent_id=folder_in.parent_id,
            type="folder",
            name=folder_in.name.strip(),
            normalized_name=norm,
            path=path,
            tags_normalized=True,
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        return node

    def create_note(self, notebook_id: UUID, user_id: UUID, note_in: NoteCreate) -> NoteNode:
        norm = normalize_name(note_in.title)
        parent_path, _ = self._get_parent_path(note_in.parent_id, notebook_id)

        if self.node_repo.check_name_conflict(notebook_id, note_in.parent_id, norm):
            raise ValueError("同名冲突: 当前目录已存在同名条目")

        path = _compute_path(parent_path, note_in.title.strip(), is_note=True)
        notebook = self.notebook_repo.get_by_id(notebook_id)
        if not notebook:
            raise ValueError("Notebook not found")
        # Shared notes use the notebook owner's existing storage root so a
        # collaborator never creates a second private copy of the document.
        content_path = _compute_content_path(notebook.user_id, notebook_id, path)

        node = NoteNode(
            id=uuid4(),
            notebook_id=notebook_id,
            parent_id=note_in.parent_id,
            type="note",
            name=note_in.title.strip(),
            normalized_name=norm,
            path=path,
            content_path=content_path,
            summary=note_in.summary,
            tags=canonicalize_tags(note_in.tags),
            tags_normalized=True,
            word_count=len(note_in.content.split()) if note_in.content else 0,
        )
        self.db.add(node)
        try:
            _write_content_atomically(content_path, note_in.content or "")
            self.db.commit()
            self.db.refresh(node)
        except Exception:
            self.db.rollback()
            if os.path.exists(content_path):
                os.remove(content_path)
            raise

        # Check note_count achievements
        try:
            self.achievement_service.check_notes(user_id)
        except Exception:
            logger.exception("Note achievement processing failed for user %s", user_id)

        return node

    def rename_node(self, node_id: UUID, new_name: str, commit: bool = True) -> NoteNode:
        node = self.node_repo.get_by_id(node_id)
        if not node:
            raise ValueError("Node not found")

        norm = normalize_name(new_name)
        if norm == node.normalized_name:
            return node  # no change

        if self.node_repo.check_name_conflict(node.notebook_id, node.parent_id, norm):
            raise ValueError("同名冲突: 当前目录已存在同名条目")

        old_path = node.path
        is_note = node.type == "note"
        display_name = new_name.strip()

        # Compute new parent path from current node's parent
        parent = self.node_repo.get_by_id(node.parent_id) if node.parent_id else None
        parent_path = parent.path if parent else ""
        new_path = _compute_path(parent_path, display_name, is_note)

        node.name = display_name
        node.normalized_name = norm
        node.path = new_path

        if is_note and node.content_path:
            parts = pathlib.Path(node.content_path).parts
            notes_data_idx = None
            for i, p in enumerate(parts):
                if p == "notes_data":
                    notes_data_idx = i
                    break
            if notes_data_idx is not None:
                user_id_str = parts[notes_data_idx + 1]
                new_content_path = str(
                    NOTES_DIR / user_id_str / str(node.notebook_id) / new_path.lstrip("/")
                )
            else:
                new_content_path = node.content_path

            if os.path.exists(node.content_path):
                os.makedirs(os.path.dirname(new_content_path), exist_ok=True)
                os.rename(node.content_path, new_content_path)
            node.content_path = new_content_path

        # Update descendants' paths
        descendants = self.node_repo.get_descendants(node_id)
        for desc in descendants:
            desc.path = desc.path.replace(old_path + "/", new_path + "/", 1)
            if desc.content_path:
                desc.content_path = desc.content_path.replace(
                    old_path.lstrip("/") + "/", new_path.lstrip("/") + "/", 1
                )

        if commit:
            self.db.commit()
            self.db.refresh(node)
        return node

    def move_node(self, node_id: UUID, new_parent_id: Optional[UUID]) -> NoteNode:
        node = self.node_repo.get_by_id(node_id)
        if not node:
            raise ValueError("Node not found")

        # Prevent moving to self or own descendant
        if new_parent_id == node_id:
            raise ValueError("Cannot move a node into itself")
        if new_parent_id:
            descendants = self.node_repo.get_descendants(node_id)
            if any(d.id == new_parent_id for d in descendants):
                raise ValueError("Cannot move a node into its own descendant")

        norm = node.normalized_name
        if self.node_repo.check_name_conflict(node.notebook_id, new_parent_id, norm):
            raise ValueError("同名冲突: 目标目录已存在同名条目")

        old_path = node.path
        is_note = node.type == "note"

        if new_parent_id:
            new_parent = self.node_repo.get_by_id(new_parent_id)
            if (
                not new_parent
                or new_parent.notebook_id != node.notebook_id
                or new_parent.type != "folder"
            ):
                raise ValueError("Target must be a folder")
            new_parent_path = new_parent.path
        else:
            new_parent_path = ""

        new_path = _compute_path(new_parent_path, node.name, is_note)
        node.parent_id = new_parent_id
        node.path = new_path

        if is_note and node.content_path:
            parts = pathlib.Path(node.content_path).parts
            notes_data_idx = None
            for i, p in enumerate(parts):
                if p == "notes_data":
                    notes_data_idx = i
                    break
            if notes_data_idx is not None:
                user_id_str = parts[notes_data_idx + 1]
                new_content_path = str(
                    NOTES_DIR / user_id_str / str(node.notebook_id) / new_path.lstrip("/")
                )
                if os.path.exists(node.content_path):
                    os.makedirs(os.path.dirname(new_content_path), exist_ok=True)
                    shutil.move(node.content_path, new_content_path)
                node.content_path = new_content_path

        # Update descendants
        descendants = self.node_repo.get_descendants(node_id)
        for desc in descendants:
            desc.path = desc.path.replace(old_path + "/", new_path + "/", 1)
            if desc.content_path:
                desc.content_path = desc.content_path.replace(
                    old_path.lstrip("/") + "/", new_path.lstrip("/") + "/", 1
                )

        self.db.commit()
        self.db.refresh(node)
        return node

    def update_note(self, node_id: UUID, note_in: NoteUpdate, user_id: Optional[UUID] = None) -> NoteNode:
        node = self.node_repo.get_by_id(node_id)
        if not node or node.type != "note":
            raise ValueError("Note not found")

        if user_id is not None:
            self.require_notebook_access(node.notebook_id, user_id, write=True)

        if note_in.base_revision is not None and note_in.base_revision != (node.content_revision or 1):
            raise NoteRevisionConflict(node, self.get_note_content(node_id))

        if note_in.title is not None:
            self.rename_node(node_id, note_in.title, commit=False)

        if note_in.summary is not None:
            node.summary = note_in.summary
        if note_in.tags is not None:
            node.tags = canonicalize_tags(note_in.tags)
        else:
            node.tags = canonicalize_tags(node.tags)
        node.tags_normalized = True
        if note_in.is_pinned is not None:
            node.is_pinned = note_in.is_pinned

        previous_content = None
        content_path = node.content_path
        if note_in.content is not None and content_path and os.path.exists(content_path):
            with open(content_path, "r", encoding="utf-8") as content_file:
                previous_content = content_file.read()

        if note_in.content is not None:
            node.word_count = len(note_in.content.split())
            if content_path:
                _write_content_atomically(content_path, note_in.content)

        changed = any(
            value is not None
            for value in (note_in.title, note_in.summary, note_in.tags, note_in.is_pinned, note_in.content)
        )
        if changed:
            node.content_revision = (node.content_revision or 1) + 1
            if user_id is not None:
                node.updated_by = user_id

        try:
            self.db.commit()
            self.db.refresh(node)
        except Exception:
            self.db.rollback()
            if note_in.content is not None and content_path and previous_content is not None:
                _write_content_atomically(content_path, previous_content)
            raise
        return node

    def persist_collaboration_content(self, node_id: UUID, user_id: UUID, content: str) -> NoteNode:
        node = self.node_repo.get_by_id(node_id)
        if not node or node.type != "note":
            raise ValueError("Note not found")
        self.require_notebook_access(node.notebook_id, user_id, write=True)
        previous_content = self.get_note_content(node_id)
        try:
            if node.content_path:
                _write_content_atomically(node.content_path, content)
            node.word_count = len(content.split())
            node.content_revision = (node.content_revision or 1) + 1
            node.updated_by = user_id
            self.db.commit()
            self.db.refresh(node)
            return node
        except Exception:
            self.db.rollback()
            if node.content_path:
                _write_content_atomically(node.content_path, previous_content)
            raise

    def get_note_content(self, node_id: UUID) -> str:
        node = self.node_repo.get_by_id(node_id)
        if not node or node.type != "note":
            raise ValueError("Note not found")
        if node.content_path and os.path.exists(node.content_path):
            with open(node.content_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def delete_node(self, node_id: UUID) -> None:
        node = self.node_repo.get_by_id(node_id)
        if not node:
            raise ValueError("Node not found")

        # Delete descendants first
        descendants = self.node_repo.get_descendants(node_id)
        for desc in sorted(descendants, key=lambda item: item.path.count("/"), reverse=True):
            self._delete_note_related_data(desc)
            if desc.type == "note" and desc.content_path and os.path.exists(desc.content_path):
                os.remove(desc.content_path)
            self.db.delete(desc)

        # Delete the node itself
        self._delete_note_related_data(node)
        if node.type == "note" and node.content_path and os.path.exists(node.content_path):
            os.remove(node.content_path)

        self.db.delete(node)
        self.db.commit()

    def _delete_note_related_data(self, node: NoteNode) -> None:
        if node.type != "note":
            return
        for attachment in self.attachment_repo.get_by_note(node.id):
            attachment_path = _attachment_file_path(attachment.file_path)
            if attachment_path and attachment_path.exists():
                attachment_path.unlink()
            self.db.delete(attachment)
        self.db.query(NoteUserActivity).filter(
            NoteUserActivity.note_id == node.id,
        ).delete(synchronize_session=False)
        self.db.query(NoteCollabEvent).filter(
            NoteCollabEvent.note_id == node.id,
        ).delete(synchronize_session=False)
        self.db.query(NoteCollabDocument).filter(
            NoteCollabDocument.note_id == node.id,
        ).delete(synchronize_session=False)

    def create_attachment(
        self,
        note_id: UUID,
        user_id: UUID,
        filename: str,
        file_path: str,
        file_type: str,
        file_size: int,
    ) -> Attachment:
        self.require_node_access(note_id, user_id, write=True)
        attachment = Attachment(
            note_id=note_id,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size=file_size,
        )
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

    def get_attachment(self, note_id: UUID, attachment_id: UUID, user_id: UUID) -> Attachment:
        self.require_node_access(note_id, user_id)
        attachment = self.db.query(Attachment).filter(
            Attachment.id == attachment_id,
            Attachment.note_id == note_id,
        ).first()
        if not attachment:
            raise ValueError("Attachment not found")
        return attachment

    def search_notes(self, user_id: UUID, query: str) -> List[NoteNode]:
        return self.node_repo.search(user_id, query)

    def mark_note_opened(self, note_id: UUID, user_id: UUID) -> NoteNode:
        node = self.node_repo.get_by_id(note_id)
        if not node or node.type != "note":
            raise ValueError("Note not found")
        self.require_notebook_access(node.notebook_id, user_id)

        opened_at = datetime.now(timezone.utc)
        node.last_opened_at = opened_at
        activity = self.db.query(NoteUserActivity).filter(
            NoteUserActivity.note_id == note_id,
            NoteUserActivity.user_id == user_id,
        ).first()
        if not activity:
            activity = NoteUserActivity(note_id=note_id, user_id=user_id)
            self.db.add(activity)
        activity.last_opened_at = opened_at
        self.db.commit()
        self.db.refresh(node)
        return node

    def get_recent_notes(self, user_id: UUID, limit: int) -> List[NoteNode]:
        return self.node_repo.get_recent_by_user(user_id, limit)

    def discover_notes(
        self,
        user_id: UUID,
        sort: str,
        notebook_id: Optional[UUID] = None,
        tag: Optional[str] = None,
        pinned: Optional[bool] = None,
        updated_after: Optional[datetime] = None,
        updated_before: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[NoteNode]:
        return self.node_repo.discover(
            user_id=user_id,
            sort=sort,
            notebook_id=notebook_id,
            tag=tag,
            pinned=pinned,
            updated_after=updated_after,
            updated_before=updated_before,
            limit=limit,
        )

    @staticmethod
    def canonicalize_existing_tags(db) -> None:
        """Normalize each unmarked row once and mark it complete."""
        rows = db.execute(text(
            "SELECT id, tags FROM note_nodes WHERE tags_normalized IS NULL"
        )).fetchall()
        if not rows:
            return

        updates = [
            {"id": row.id, "tags": canonicalize_tags(row.tags), "tags_normalized": True}
            for row in rows
        ]
        db.execute(text(
            "UPDATE note_nodes "
            "SET tags = :tags, tags_normalized = :tags_normalized "
            "WHERE id = :id AND tags_normalized IS NULL"
        ), updates)

    # --- Migration from old tables ---

    @staticmethod
    def _parse_legacy_datetime(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time.min)
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            try:
                return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def restore_moved_files(moved_files: Sequence[Tuple[str, str]]) -> None:
        """Restore legacy files moved by a migration that did not commit."""
        for old_path, new_path in reversed(moved_files):
            if os.path.exists(new_path):
                os.makedirs(os.path.dirname(old_path), exist_ok=True)
                shutil.move(new_path, old_path)

    @staticmethod
    def migrate_old_data(db: Session) -> List[Tuple[str, str]]:
        """Migrate data from old folders/notes tables to note_nodes.

        Called once at startup. If old tables don't exist or are empty, no-op.
        The returned file moves remain the caller's responsibility until the
        caller commits the surrounding transaction.
        """
        inspector = inspect(db.bind)
        existing_tables = inspector.get_table_names()

        if "folders" not in existing_tables or "notes" not in existing_tables:
            return []

        # Check if there's data to migrate
        old_folders = db.execute(text("SELECT id, notebook_id, parent_id, name, path FROM folders")).fetchall()
        old_notes = db.execute(text(
            "SELECT id, folder_id, title, file_path, summary, tags, is_pinned, word_count, created_at, updated_at FROM notes"
        )).fetchall()

        if not old_folders and not old_notes:
            return []

        # Check if note_nodes already has data (don't re-migrate)
        existing_nodes = db.execute(text("SELECT COUNT(*) FROM note_nodes")).scalar()
        if existing_nodes > 0:
            return []

        moved_files = []

        try:
            # Build folder mapping: old_folder_id -> note_node
            folder_id_map = {}
            for f in old_folders:
                folder_id, notebook_id, parent_id, name, old_path = f
                safe_name = sanitize_filename(name).strip() or "Untitled"
                norm = safe_name.lower()
                nn_parent = folder_id_map.get(parent_id) if parent_id else None
                parent_path = nn_parent.path if nn_parent else ""
                node_path = f"{parent_path}/{safe_name}" if parent_path else f"/{safe_name}"

                node = NoteNode(
                    id=uuid4(),
                    notebook_id=UUID(notebook_id) if isinstance(notebook_id, str) else notebook_id,
                    parent_id=nn_parent.id if nn_parent else None,
                    type="folder",
                    name=safe_name,
                    normalized_name=norm,
                    path=node_path,
                    tags_normalized=True,
                )
                db.add(node)
                db.flush()
                folder_id_map[folder_id] = node

            # Migrate notes
            for n in old_notes:
                (note_id, old_folder_id, title, old_file_path,
                 summary, tags, is_pinned, word_count, created_at, updated_at) = n

                parent_node = folder_id_map.get(old_folder_id)
                if not parent_node:
                    continue

                safe_title = sanitize_filename(title).strip() or "Untitled"
                norm = safe_title.lower()
                node_path = f"{parent_node.path}/{safe_title}.md"

                # Compute new content path
                parts = pathlib.Path(old_file_path).parts if old_file_path else ()
                user_id_str = None
                for i, p in enumerate(parts):
                    if p == "notes_data" and i + 1 < len(parts):
                        user_id_str = parts[i + 1]
                        break

                if user_id_str:
                    new_content_path = str(
                        NOTES_DIR / user_id_str / str(parent_node.notebook_id) / node_path.lstrip("/")
                    )
                else:
                    new_content_path = old_file_path

                node = NoteNode(
                    id=UUID(note_id) if isinstance(note_id, str) else note_id,
                    notebook_id=UUID(parent_node.notebook_id) if isinstance(parent_node.notebook_id, str) else parent_node.notebook_id,
                    parent_id=parent_node.id,
                    type="note",
                    name=safe_title,
                    normalized_name=norm,
                    path=node_path,
                    content_path=new_content_path,
                    summary=summary,
                    tags=canonicalize_tags(tags),
                    tags_normalized=True,
                    is_pinned=bool(is_pinned),
                    word_count=word_count or 0,
                    created_at=NoteService._parse_legacy_datetime(created_at) or datetime.now(timezone.utc),
                    updated_at=NoteService._parse_legacy_datetime(updated_at) or datetime.now(timezone.utc),
                )
                db.add(node)

                # Move file if path changed
                if old_file_path and os.path.exists(old_file_path) and old_file_path != new_content_path:
                    os.makedirs(os.path.dirname(new_content_path), exist_ok=True)
                    shutil.move(old_file_path, new_content_path)
                    moved_files.append((old_file_path, new_content_path))

            db.flush()
            db.execute(text("DROP TABLE IF EXISTS notes"))
            db.execute(text("DROP TABLE IF EXISTS folders"))
            return moved_files
        except Exception:
            db.rollback()
            NoteService.restore_moved_files(moved_files)
            raise
