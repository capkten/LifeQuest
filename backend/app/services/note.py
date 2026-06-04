# backend/app/services/note.py
import os
import pathlib
import re
import shutil
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.note import Notebook, Attachment
from app.models.note_node import NoteNode, normalize_name
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


class NoteService:
    def __init__(self, db: Session):
        self.db = db
        self.notebook_repo = NotebookRepository(db)
        self.node_repo = NoteNodeRepository(db)
        self.attachment_repo = AttachmentRepository(db)
        self.achievement_service = AchievementService(db)

    # --- Ownership verification ---

    def verify_notebook_ownership(self, notebook_id: UUID, user_id: UUID) -> bool:
        notebook = self.notebook_repo.get_by_id(notebook_id)
        if not notebook:
            return False
        return notebook.user_id == user_id

    def verify_node_ownership(self, node_id: UUID, user_id: UUID) -> bool:
        node = self.node_repo.get_by_id(node_id)
        if not node:
            return False
        return self.verify_notebook_ownership(node.notebook_id, user_id)

    # --- Notebook operations ---

    def create_notebook(self, user_id: UUID, notebook_in: NotebookCreate) -> Notebook:
        data = notebook_in.model_dump()
        data["user_id"] = user_id
        return self.notebook_repo.create(data)

    def get_notebooks(self, user_id: UUID) -> List[Notebook]:
        return self.notebook_repo.get_by_user(user_id)

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
        content_path = _compute_content_path(user_id, notebook_id, path)

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
            tags=note_in.tags,
            word_count=len(note_in.content.split()) if note_in.content else 0,
        )
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)

        # Write markdown file
        os.makedirs(os.path.dirname(content_path), exist_ok=True)
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(note_in.content or "")

        # Check note_count achievements
        try:
            self.achievement_service.check_notes(user_id)
        except Exception:
            pass  # Don't fail note creation if achievement check fails

        return node

    def rename_node(self, node_id: UUID, new_name: str) -> NoteNode:
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
            if not new_parent or new_parent.type != "folder":
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

    def update_note(self, node_id: UUID, note_in: NoteUpdate) -> NoteNode:
        node = self.node_repo.get_by_id(node_id)
        if not node or node.type != "note":
            raise ValueError("Note not found")

        if note_in.title is not None:
            self.rename_node(node_id, note_in.title)

        if note_in.summary is not None:
            node.summary = note_in.summary
        if note_in.tags is not None:
            node.tags = note_in.tags
        if note_in.is_pinned is not None:
            node.is_pinned = note_in.is_pinned

        if note_in.content is not None:
            node.word_count = len(note_in.content.split())
            if node.content_path:
                os.makedirs(os.path.dirname(node.content_path), exist_ok=True)
                with open(node.content_path, "w", encoding="utf-8") as f:
                    f.write(note_in.content)

        self.db.commit()
        self.db.refresh(node)
        return node

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
        for desc in reversed(descendants):
            if desc.type == "note" and desc.content_path and os.path.exists(desc.content_path):
                os.remove(desc.content_path)
            self.db.delete(desc)

        # Delete the node itself
        if node.type == "note" and node.content_path and os.path.exists(node.content_path):
            os.remove(node.content_path)

        self.db.delete(node)
        self.db.commit()

    def search_notes(self, user_id: UUID, query: str) -> List[NoteNode]:
        return self.node_repo.search(user_id, query)

    # --- Migration from old tables ---

    @staticmethod
    def migrate_old_data(db: Session) -> None:
        """Migrate data from old folders/notes tables to note_nodes.

        Called once at startup. If old tables don't exist or are empty, no-op.
        """
        inspector = inspect(db.bind)
        existing_tables = inspector.get_table_names()

        if "folders" not in existing_tables or "notes" not in existing_tables:
            return

        # Check if there's data to migrate
        old_folders = db.execute(text("SELECT id, notebook_id, parent_id, name, path FROM folders")).fetchall()
        old_notes = db.execute(text(
            "SELECT id, folder_id, title, file_path, summary, tags, is_pinned, word_count, created_at, updated_at FROM notes"
        )).fetchall()

        if not old_folders and not old_notes:
            return

        # Check if note_nodes already has data (don't re-migrate)
        existing_nodes = db.execute(text("SELECT COUNT(*) FROM note_nodes")).scalar()
        if existing_nodes > 0:
            return

        # Build folder mapping: old_folder_id -> note_node
        folder_id_map = {}
        for f in old_folders:
            folder_id, notebook_id, parent_id, name, old_path = f
            norm = name.strip().lower()
            nn_parent = folder_id_map.get(parent_id) if parent_id else None
            parent_path = nn_parent.path if nn_parent else ""
            node_path = f"{parent_path}/{name}" if parent_path else f"/{name}"

            node = NoteNode(
                id=uuid4(),
                notebook_id=UUID(notebook_id) if isinstance(notebook_id, str) else notebook_id,
                parent_id=UUID(parent_id) if isinstance(parent_id, str) else parent_id,
                type="folder",
                name=name,
                normalized_name=norm,
                path=node_path,
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

            norm = title.strip().lower()
            node_path = f"{parent_node.path}/{title}.md"

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
                id=UUID(note_id) if isinstance(note_id, str) else note_id,  # preserve original ID
                notebook_id=UUID(parent_node.notebook_id) if isinstance(parent_node.notebook_id, str) else parent_node.notebook_id,
                parent_id=UUID(parent_node.id) if isinstance(parent_node.id, str) else parent_node.id,
                type="note",
                name=title,
                normalized_name=norm,
                path=node_path,
                content_path=new_content_path,
                summary=summary,
                tags=tags,
                is_pinned=bool(is_pinned),
                word_count=word_count or 0,
                created_at=created_at,
                updated_at=updated_at,
            )
            db.add(node)

            # Move file if path changed (wrapped in try/except for robustness)
            if old_file_path and os.path.exists(old_file_path) and old_file_path != new_content_path:
                try:
                    os.makedirs(os.path.dirname(new_content_path), exist_ok=True)
                    shutil.move(old_file_path, new_content_path)
                except OSError:
                    pass  # Skip file move if path is invalid (e.g. corrupted Unicode)

        db.commit()

        # Drop old tables
        db.execute(text("DROP TABLE IF EXISTS notes"))
        db.execute(text("DROP TABLE IF EXISTS folders"))
        db.commit()
