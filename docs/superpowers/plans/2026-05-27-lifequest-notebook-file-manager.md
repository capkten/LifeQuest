# LifeQuest 笔记本文件管理器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 3-level Notebook→Folder→Note model with a unified NoteNode tree that supports root-level notes, nested folders, rename/move, and same-name conflict detection.

**Architecture:** A single `note_nodes` table stores both folders and notes as tree nodes. Parent=null means root-level. `normalized_name` + unique constraint enforces same-directory uniqueness. Markdown files live at `notes_data/<user_id>/<notebook_id>/<path>`. Old `folders`/`notes` tables are migrated then removed.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy (SQLite), Pydantic v2, Vue 3 Composition API, Vue Router, Axios, `@kangc/v-md-editor`

---

## File Structure

### Backend files to CREATE:
- `backend/app/models/note_node.py` — NoteNode SQLAlchemy model

### Backend files to REWRITE:
- `backend/app/models/note.py` — Keep only Notebook + Attachment (drop Folder, Note)
- `backend/app/models/__init__.py` — Replace Folder/Note with NoteNode
- `backend/app/schemas/note.py` — New node schemas
- `backend/app/repositories/note.py` — NoteNodeRepository
- `backend/app/services/note.py` — New service with node operations + migration
- `backend/app/api/notes.py` — New API routes per spec

### Backend files to MODIFY:
- `backend/app/main.py` — Add migration call at startup

### Frontend files to CREATE:
- `frontend/src/views/NotebookFileManage.vue` — File manager layout (tree + content + editor)

### Frontend files to REWRITE:
- `frontend/src/services/note.js` — New API methods for node endpoints
- `frontend/src/router/index.js` — New routes for file manager
- `frontend/src/components/layout/AppLayout.vue` — Add route titles for new routes

### Frontend files to DELETE (after migration verified):
- `frontend/src/views/NotebookDetail.vue`
- `frontend/src/views/FolderDetail.vue`

### Test files to REWRITE:
- `backend/tests/test_notes.py` — Complete test coverage per spec

---

## Task 1: NoteNode Model

**Files:**
- Create: `backend/app/models/note_node.py`

- [ ] **Step 1: Create the NoteNode model file**

```python
# backend/app/models/note_node.py
import uuid
import re
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base

INVALID_NAME_CHARS = re.compile(r'[/\\:*?"<>|\x00-\x1f]')
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def normalize_name(name: str) -> str:
    """Normalize a node name for uniqueness comparison.

    Rules:
    - Strip leading/trailing whitespace
    - Reject empty names
    - Reject names containing path separators, control chars, or Windows reserved names
    - Case-insensitive comparison (stored lowercased)
    """
    stripped = name.strip()
    if not stripped:
        raise ValueError("Name cannot be empty")
    if INVALID_NAME_CHARS.search(stripped):
        raise ValueError("Name contains invalid characters")
    upper = stripped.upper().replace(".MD", "")
    if upper in WINDOWS_RESERVED:
        raise ValueError("Name is a reserved system name")
    return stripped.lower()


class NoteNode(Base):
    __tablename__ = "note_nodes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    notebook_id = Column(Uuid, ForeignKey("notebooks.id"), nullable=False)
    parent_id = Column(Uuid, ForeignKey("note_nodes.id"), nullable=True)
    type = Column(String(10), nullable=False)  # "folder" or "note"
    name = Column(String(200), nullable=False)
    normalized_name = Column(String(200), nullable=False)
    path = Column(String(1000), nullable=False)
    content_path = Column(String(1000), nullable=True)  # note only
    summary = Column(Text, nullable=True)  # note only
    tags = Column(String(500), nullable=True)  # note only, JSON string
    is_pinned = Column(Boolean, default=False)  # note only
    word_count = Column(Integer, default=0)  # note only
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("notebook_id", "parent_id", "normalized_name", name="uq_node_sibling_name"),
    )

    notebook = relationship("Notebook", backref="note_nodes")
    parent = relationship("NoteNode", remote_side=[id], backref="children")
```

- [ ] **Step 2: Verify the model can be imported**

Run: `cd backend && python -c "from app.models.note_node import NoteNode, normalize_name; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/note_node.py
git commit -m "feat(notes): add NoteNode model with normalized name validation"
```

---

## Task 2: Register NoteNode & Rewrite note.py Model

**Files:**
- Modify: `backend/app/models/note.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Rewrite note.py to keep only Notebook + Attachment**

The old `Folder` and `Note` models are no longer needed by new code. Keep `Notebook` (unchanged) and `Attachment` (re-point its FK to note_nodes later, or keep as-is for now). Remove `Folder` and `Note` classes.

```python
# backend/app/models/note.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, Text, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class Notebook(Base):
    __tablename__ = "notebooks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    note_id = Column(Uuid, nullable=False)  # references note_nodes.id
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_type = Column(String(50))
    file_size = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Update models/__init__.py**

```python
from app.models.user import User
from app.models.note import Notebook, Attachment
from app.models.note_node import NoteNode
from app.models.todo import Habit, Task, Goal, Subtask
from app.models.shop import ShopItem, ExchangeHistory, ExchangeStatus
from app.models.backpack import (
    BackpackItem, ItemType, ItemStatus,
    UsageHistory, UsageAction,
)
from app.models.achievement import Achievement, UserAchievement

__all__ = [
    "User",
    "Notebook", "Attachment", "NoteNode",
    "Habit", "Task", "Goal", "Subtask",
    "ShopItem", "ExchangeHistory", "ExchangeStatus",
    "BackpackItem", "ItemType", "ItemStatus",
    "UsageHistory", "UsageAction",
    "Achievement", "UserAchievement",
]
```

- [ ] **Step 3: Verify imports still work**

Run: `cd backend && python -c "from app.models import NoteNode, Notebook, Attachment; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/note.py backend/app/models/__init__.py
git commit -m "refactor(notes): remove Folder/Note models, register NoteNode"
```

---

## Task 3: NoteNode Schemas

**Files:**
- Rewrite: `backend/app/schemas/note.py`

- [ ] **Step 1: Rewrite schemas/note.py with new node schemas**

```python
# backend/app/schemas/note.py
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# --- Notebook schemas (unchanged) ---

class NotebookBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None


class NotebookCreate(NotebookBase):
    pass


class NotebookUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class NotebookResponse(NotebookBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime


# --- NoteNode schemas ---

class FolderCreate(BaseModel):
    parent_id: Optional[UUID] = None
    name: str


class NoteCreate(BaseModel):
    parent_id: Optional[UUID] = None
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[UUID] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: Optional[bool] = None


class NodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notebook_id: UUID
    parent_id: Optional[UUID] = None
    type: str
    name: str
    path: str
    content_path: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[str] = None
    is_pinned: bool = False
    word_count: int = 0
    created_at: datetime
    updated_at: datetime


class NoteDetailResponse(NodeResponse):
    content: Optional[str] = None


class TreeResponse(BaseModel):
    id: UUID
    name: str
    type: str
    parent_id: Optional[UUID] = None
    children: List["TreeResponse"] = []


TreeResponse.model_rebuild()
```

- [ ] **Step 2: Verify schema imports**

Run: `cd backend && python -c "from app.schemas.note import NodeResponse, TreeResponse, FolderCreate, NoteCreate; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/note.py
git commit -m "feat(notes): add NoteNode schemas (NodeResponse, TreeResponse, etc.)"
```

---

## Task 4: NoteNode Repository

**Files:**
- Rewrite: `backend/app/repositories/note.py`

- [ ] **Step 1: Rewrite repositories/note.py**

```python
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
```

- [ ] **Step 2: Verify repository imports**

Run: `cd backend && python -c "from app.repositories.note import NoteNodeRepository, NotebookRepository; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/repositories/note.py
git commit -m "feat(notes): add NoteNodeRepository with tree/conflict/descendant queries"
```

---

## Task 5: NoteNode Service with Migration

**Files:**
- Rewrite: `backend/app/services/note.py`

- [ ] **Step 1: Rewrite services/note.py**

```python
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
            new_content_path = _compute_content_path(
                node.notebook_id, node.notebook_id, new_path
            )
            # Actually we need user_id — recalculate from the path structure
            # content_path = notes_data/<user_id>/<notebook_id>/<path.lstrip("/")>
            # Extract user_id from old content_path
            parts = pathlib.Path(node.content_path).parts
            # ... notes_data, user_id, notebook_id, ...
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
                notebook_id=notebook_id,
                parent_id=parent_id,
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
                id=note_id,  # preserve original ID
                notebook_id=parent_node.notebook_id,
                parent_id=parent_node.id,
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

            # Move file if path changed
            if old_file_path and os.path.exists(old_file_path) and old_file_path != new_content_path:
                os.makedirs(os.path.dirname(new_content_path), exist_ok=True)
                shutil.move(old_file_path, new_content_path)

        db.commit()

        # Drop old tables
        db.execute(text("DROP TABLE IF EXISTS notes"))
        db.execute(text("DROP TABLE IF EXISTS folders"))
        db.commit()
```

- [ ] **Step 2: Verify service imports**

Run: `cd backend && python -c "from app.services.note import NoteService; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/note.py
git commit -m "feat(notes): rewrite NoteService with NoteNode operations and migration"
```

---

## Task 6: API Routes

**Files:**
- Rewrite: `backend/app/api/notes.py`

- [ ] **Step 1: Rewrite api/notes.py**

```python
# backend/app/api/notes.py
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
    node_map = {n.id: n for n in nodes}
    children_map: dict = {}
    for n in nodes:
        key = n.parent_id  # None for root
        if key not in children_map:
            children_map[key] = []
        children_map[key].append(n)

    def build(parent_id):
        result = []
        for n in children_map.get(parent_id, []):
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
    if not service.verify_node_ownership(note_id, current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    node = service.node_repo.get_by_id(note_id)
    if not node or node.type != "note":
        raise HTTPException(status_code=404, detail="Note not found")
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
```

- [ ] **Step 2: Verify API imports**

Run: `cd backend && python -c "from app.api.notes import router; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/notes.py
git commit -m "feat(notes): rewrite API routes for NoteNode tree operations"
```

---

## Task 7: Migration Hook in main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add migration call to startup event**

In `backend/app/main.py`, add the migration call inside the `startup_event` function, before the achievement seeding. Add this import at the top:

```python
from app.services.note import NoteService
```

And add this line inside `startup_event()`, after `_migrate_columns()`:

```python
    NoteService.migrate_old_data(SessionLocal())
```

The full startup_event becomes:

```python
@app.on_event("startup")
def startup_event():
    """Seed default achievements on application startup."""
    _migrate_columns()
    # Migrate old notes/folders tables to note_nodes
    db = SessionLocal()
    try:
        NoteService.migrate_old_data(db)
    finally:
        db.close()
    db = SessionLocal()
    try:
        from app.services.achievement import AchievementService
        service = AchievementService(db)
        service.seed_achievements()
    finally:
        db.close()
```

- [ ] **Step 2: Verify app starts without errors**

Run: `cd backend && python -c "from app.main import app; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(notes): add old-data migration to startup"
```

---

## Task 8: Backend Tests

**Files:**
- Rewrite: `backend/tests/test_notes.py`

- [ ] **Step 1: Rewrite test_notes.py with full coverage**

```python
# backend/tests/test_notes.py
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")


def _register_and_login(client):
    """Helper: register a user and return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_notebook(client, headers, name="My Notebook"):
    response = client.post(
        "/api/notes/notebooks",
        json={"name": name},
        headers=headers,
    )
    return response.json()


def test_create_notebook(client):
    headers = _register_and_login(client)
    response = client.post(
        "/api/notes/notebooks",
        json={"name": "My Notebook", "description": "Test notebook"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Notebook"


def test_create_folder_at_root(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    response = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Project A"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Project A"
    assert data["type"] == "folder"
    assert data["parent_id"] is None


def test_create_note_at_root(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    response = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Inbox", "content": "# Hello"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Inbox"
    assert data["type"] == "note"


def test_create_nested_folders(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create root folder
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Project A"},
        headers=headers,
    )
    folder_id = r1.json()["id"]

    # Create subfolder
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Requirements", "parent_id": folder_id},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["parent_id"] == folder_id
    assert "/Project A/Requirements" in r2.json()["path"]


def test_create_note_in_subfolder(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create folder
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Docs"},
        headers=headers,
    )
    folder_id = r1.json()["id"]

    # Create note in folder
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Meeting Notes", "content": "## Notes", "parent_id": folder_id},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["type"] == "note"
    assert "/Docs/Meeting Notes.md" in r2.json()["path"]


def test_same_name_conflict_note_and_folder(client):
    """A note and folder with the same normalized name in the same dir should conflict."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create folder "test"
    client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "test"},
        headers=headers,
    )

    # Try to create note "test" at same level
    r = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "test", "content": ""},
        headers=headers,
    )
    assert r.status_code == 409
    assert "同名冲突" in r.json()["detail"]


def test_same_name_conflict_two_notes(client):
    """Two notes with the same name in the same directory should conflict."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Weekly", "content": "week 1"},
        headers=headers,
    )
    r = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Weekly", "content": "week 2"},
        headers=headers,
    )
    assert r.status_code == 409


def test_same_name_allowed_in_different_dirs(client):
    """Same name in different directories should succeed."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create two folders
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir A"},
        headers=headers,
    )
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir B"},
        headers=headers,
    )
    dir_a = r1.json()["id"]
    dir_b = r2.json()["id"]

    # Create note "report" in both
    n1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "A", "parent_id": dir_a},
        headers=headers,
    )
    n2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "B", "parent_id": dir_b},
        headers=headers,
    )
    assert n1.status_code == 200
    assert n2.status_code == 200


def test_rename_to_existing_name_returns_409(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Alpha", "content": ""},
        headers=headers,
    )
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Beta", "content": ""},
        headers=headers,
    )
    beta_id = r2.json()["id"]

    # Rename Beta -> Alpha should fail
    r = client.patch(
        f"/api/notes/nodes/{beta_id}",
        json={"name": "Alpha"},
        headers=headers,
    )
    assert r.status_code == 409


def test_move_to_dir_with_same_name_returns_409(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create two folders
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir A"},
        headers=headers,
    )
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir B"},
        headers=headers,
    )
    dir_a = r1.json()["id"]
    dir_b = r2.json()["id"]

    # Create "report" in Dir A
    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "", "parent_id": dir_a},
        headers=headers,
    )
    # Create "report" in Dir B
    r_note = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "", "parent_id": dir_b},
        headers=headers,
    )
    report_b_id = r_note.json()["id"]

    # Try to move report from Dir B to root (where there's no conflict) — should succeed
    r = client.patch(
        f"/api/notes/nodes/{report_b_id}",
        json={"parent_id": None},
        headers=headers,
    )
    assert r.status_code == 200

    # But try to move it back to Dir A where "report" already exists
    r = client.patch(
        f"/api/notes/nodes/{report_b_id}",
        json={"parent_id": dir_a},
        headers=headers,
    )
    assert r.status_code == 409


def test_delete_folder_recursive(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create folder with a note inside
    r_folder = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Temp"},
        headers=headers,
    )
    folder_id = r_folder.json()["id"]

    r_note = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Doc", "content": "content here", "parent_id": folder_id},
        headers=headers,
    )
    note_id = r_note.json()["id"]

    # Delete the folder
    r = client.delete(f"/api/notes/nodes/{folder_id}", headers=headers)
    assert r.status_code == 200

    # Verify note is also gone
    r = client.get(f"/api/notes/{note_id}", headers=headers)
    assert r.status_code == 404


def test_get_tree(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Folder1"},
        headers=headers,
    )
    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Root Note", "content": ""},
        headers=headers,
    )

    r = client.get(f"/api/notes/notebooks/{nb['id']}/tree", headers=headers)
    assert r.status_code == 200
    tree = r.json()
    assert len(tree) == 2
    names = {n["name"] for n in tree}
    assert "Folder1" in names
    assert "Root Note" in names


def test_get_children(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    r_folder = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Folder1"},
        headers=headers,
    )
    folder_id = r_folder.json()["id"]

    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Note In Folder", "content": "", "parent_id": folder_id},
        headers=headers,
    )
    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Root Note", "content": ""},
        headers=headers,
    )

    # Root children should have Folder1 and Root Note
    r = client.get(f"/api/notes/notebooks/{nb['id']}/children", headers=headers)
    assert r.status_code == 200
    children = r.json()
    assert len(children) == 2

    # Folder1 children should have Note In Folder
    r = client.get(
        f"/api/notes/notebooks/{nb['id']}/children?parent_id={folder_id}",
        headers=headers,
    )
    children = r.json()
    assert len(children) == 1
    assert children[0]["name"] == "Note In Folder"


def test_cannot_access_other_users_notebook(client):
    # User 1
    headers1 = _register_and_login(client)
    nb = _create_notebook(client, headers1)

    # User 2
    client.post(
        "/api/auth/register",
        json={"username": "user2", "email": "u2@e.com", "password": "pass123456"},
    )
    login2 = client.post(
        "/api/auth/login",
        data={"username": "user2", "password": "pass123456"},
    )
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    # User 2 cannot see User 1's tree
    r = client.get(f"/api/notes/notebooks/{nb['id']}/tree", headers=headers2)
    assert r.status_code == 403


def test_file_path_stays_within_notes_data(client):
    """Names with path separators should be sanitized."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    r = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "../escape", "content": ""},
        headers=headers,
    )
    # The name should be rejected by normalize_name due to invalid chars
    assert r.status_code == 400
```

- [ ] **Step 2: Run all backend tests**

Run: `cd backend && python -m pytest tests/test_notes.py -v`

Expected: All tests pass.

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_notes.py
git commit -m "test(notes): comprehensive tests for NoteNode file manager"
```

---

## Task 9: Frontend API Service

**Files:**
- Rewrite: `frontend/src/services/note.js`

- [ ] **Step 1: Rewrite the note service**

```javascript
// frontend/src/services/note.js
import api from './api'

export const noteService = {
  // --- Notebooks ---
  async getNotebooks() {
    const response = await api.get('/notes/notebooks')
    return response.data
  },

  async getNotebook(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}`)
    return response.data
  },

  async createNotebook(data) {
    const response = await api.post('/notes/notebooks', data)
    return response.data
  },

  async updateNotebook(notebookId, data) {
    const response = await api.put(`/notes/notebooks/${notebookId}`, data)
    return response.data
  },

  async deleteNotebook(notebookId) {
    await api.delete(`/notes/notebooks/${notebookId}`)
  },

  // --- Node tree ---
  async getTree(notebookId) {
    const response = await api.get(`/notes/notebooks/${notebookId}/tree`)
    return response.data
  },

  async getChildren(notebookId, parentId = null) {
    const params = parentId ? { parent_id: parentId } : {}
    const response = await api.get(`/notes/notebooks/${notebookId}/children`, { params })
    return response.data
  },

  // --- Folders ---
  async createFolder(notebookId, data) {
    const response = await api.post(`/notes/notebooks/${notebookId}/folders`, data)
    return response.data
  },

  // --- Notes ---
  async createNote(notebookId, data) {
    const response = await api.post(`/notes/notebooks/${notebookId}/notes`, data)
    return response.data
  },

  async getNote(noteId) {
    const response = await api.get(`/notes/${noteId}`)
    return response.data
  },

  async updateNote(noteId, data) {
    const response = await api.put(`/notes/${noteId}`, data)
    return response.data
  },

  // --- Node operations ---
  async renameNode(nodeId, name) {
    const response = await api.patch(`/notes/nodes/${nodeId}`, { name })
    return response.data
  },

  async moveNode(nodeId, parentId) {
    const response = await api.patch(`/notes/nodes/${nodeId}`, { parent_id: parentId })
    return response.data
  },

  async deleteNode(nodeId) {
    await api.delete(`/notes/nodes/${nodeId}`)
  },

  // --- Search ---
  async searchNotes(query) {
    const response = await api.get('/notes/search', { params: { query } })
    return response.data
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/note.js
git commit -m "feat(notes): rewrite frontend service for NoteNode API"
```

---

## Task 10: Frontend NotebookFileManage View

**Files:**
- Create: `frontend/src/views/NotebookFileManage.vue`

- [ ] **Step 1: Create the file manager view**

This component replaces NotebookDetail + FolderDetail. It shows:
- Left panel: tree navigation of the notebook
- Right panel: current directory content list (folders + notes mixed)
- Clicking a note navigates to the editor

```vue
<!-- frontend/src/views/NotebookFileManage.vue -->
<template>
  <div class="file-manager">
    <!-- Breadcrumb -->
    <div class="fm-toolbar">
      <div class="fm-breadcrumb">
        <button class="breadcrumb-item" @click="navigateTo(null)">
          {{ notebook?.name || '笔记本' }}
        </button>
        <template v-for="crumb in breadcrumbs" :key="crumb.id">
          <span class="breadcrumb-sep">/</span>
          <button class="breadcrumb-item" @click="navigateTo(crumb.id)">
            {{ crumb.name }}
          </button>
        </template>
      </div>
      <div class="fm-actions">
        <button class="action-btn" @click="showCreateFolder = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <line x1="12" y1="11" x2="12" y2="17" />
            <line x1="9" y1="14" x2="15" y2="14" />
          </svg>
          新建文件夹
        </button>
        <button class="action-btn action-btn--primary" @click="showCreateNote = true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          新建笔记
        </button>
      </div>
    </div>

    <!-- Main content area: tree sidebar + content list -->
    <div class="fm-body">
      <!-- Tree sidebar -->
      <aside class="fm-tree" :class="{ 'fm-tree--open': treeOpen }">
        <div class="tree-header">
          <span class="tree-title">目录</span>
          <button class="tree-close" @click="treeOpen = false" aria-label="关闭目录">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div v-if="treeLoading" class="tree-loading">
          <span class="loading-spinner loading-spinner--sm"></span>
        </div>
        <ul v-else class="tree-list">
          <li v-for="node in tree" :key="node.id">
            <TreeItem :node="node" :current-id="currentFolderId" @navigate="navigateTo" />
          </li>
        </ul>
      </aside>

      <!-- Content list -->
      <div class="fm-content">
        <button class="tree-toggle" @click="treeOpen = !treeOpen" aria-label="切换目录">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
        </button>

        <div v-if="loading" class="loading-state">
          <span class="loading-spinner"></span>
        </div>

        <div v-else-if="error" class="error-state">
          <p>{{ error }}</p>
          <button class="retry-btn" @click="fetchChildren">重试</button>
        </div>

        <div v-else-if="children.length === 0" class="empty-state">
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <h3>暂无内容</h3>
          <p>点击上方按钮创建文件夹或笔记</p>
        </div>

        <div v-else class="node-list">
          <div
            v-for="node in children"
            :key="node.id"
            class="node-card"
            tabindex="0"
            role="button"
            @click="openNode(node)"
            @keydown.enter="openNode(node)"
          >
            <div class="node-icon" :class="{ 'node-icon--folder': node.type === 'folder' }">
              <svg v-if="node.type === 'folder'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            </div>
            <div class="node-info">
              <h3 class="node-name">{{ node.name }}</h3>
              <p class="node-meta" v-if="node.type === 'note' && node.updated_at">
                {{ formatDate(node.updated_at) }}
                <span v-if="node.word_count"> · {{ node.word_count }} 字</span>
              </p>
              <p class="node-meta" v-else-if="node.type === 'folder'">文件夹</p>
            </div>
            <div class="node-actions">
              <button class="node-action-btn" @click.stop="startRename(node)" title="重命名">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button class="node-action-btn node-action-btn--danger" @click.stop="confirmDelete(node)" title="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Folder Dialog -->
    <Teleport to="body">
      <div v-if="showCreateFolder" class="dialog-overlay" @click.self="showCreateFolder = false">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">新建文件夹</h3>
            <button class="dialog-close" @click="showCreateFolder = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="createFolder">
            <div class="form-group">
              <label class="form-label" for="folder-name-input">文件夹名称</label>
              <input id="folder-name-input" ref="folderNameRef" v-model="folderForm.name" type="text" class="form-input" placeholder="我的文件夹" required maxlength="100" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showCreateFolder = false">取消</button>
              <button type="submit" class="btn-primary" :disabled="!folderForm.name.trim()">创建</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Create Note Dialog -->
    <Teleport to="body">
      <div v-if="showCreateNote" class="dialog-overlay" @click.self="showCreateNote = false">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">新建笔记</h3>
            <button class="dialog-close" @click="showCreateNote = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="createNote">
            <div class="form-group">
              <label class="form-label" for="note-title-input">笔记标题</label>
              <input id="note-title-input" ref="noteTitleRef" v-model="noteForm.title" type="text" class="form-input" placeholder="我的笔记" required maxlength="200" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showCreateNote = false">取消</button>
              <button type="submit" class="btn-primary" :disabled="!noteForm.title.trim()">创建</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Rename Dialog -->
    <Teleport to="body">
      <div v-if="showRename" class="dialog-overlay" @click.self="showRename = false">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <h3 class="dialog-title">重命名</h3>
            <button class="dialog-close" @click="showRename = false" aria-label="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <form class="dialog-body" @submit.prevent="doRename">
            <div class="form-group">
              <label class="form-label" for="rename-input">新名称</label>
              <input id="rename-input" ref="renameRef" v-model="renameForm.name" type="text" class="form-input" required maxlength="200" />
            </div>
            <div v-if="dialogError" class="dialog-error" role="alert">{{ dialogError }}</div>
            <div class="dialog-actions">
              <button type="button" class="btn-secondary" @click="showRename = false">取消</button>
              <button type="submit" class="btn-primary" :disabled="!renameForm.name.trim()">确认</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Toast -->
    <Teleport to="body">
      <Transition name="toast">
        <div v-if="toast.show" class="toast" :class="toast.type">{{ toast.message }}</div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { noteService } from '../services/note'

const route = useRoute()
const router = useRouter()
const notebookId = computed(() => route.params.notebookId)

const notebook = ref(null)
const tree = ref([])
const children = ref([])
const currentFolderId = ref(null)
const loading = ref(true)
const treeLoading = ref(true)
const error = ref(null)
const treeOpen = ref(false)

// Dialogs
const showCreateFolder = ref(false)
const showCreateNote = ref(false)
const showRename = ref(false)
const dialogError = ref(null)
const folderForm = ref({ name: '' })
const noteForm = ref({ title: '' })
const renameForm = ref({ name: '', nodeId: null })
const folderNameRef = ref(null)
const noteTitleRef = ref(null)
const renameRef = ref(null)

// Toast
const toast = ref({ show: false, message: '', type: 'success' })
let toastTimer = null

function showToast(message, type = 'success') {
  if (toastTimer) clearTimeout(toastTimer)
  toast.value = { show: true, message, type }
  toastTimer = setTimeout(() => { toast.value.show = false }, 3000)
}

// Build breadcrumbs from tree data
const breadcrumbs = computed(() => {
  if (!currentFolderId.value) return []
  const crumbs = []
  const findPath = (nodes, targetId, path) => {
    for (const n of nodes) {
      if (n.id === targetId) return [...path, { id: n.id, name: n.name }]
      if (n.children?.length) {
        const found = findPath(n.children, targetId, [...path, { id: n.id, name: n.name }])
        if (found) return found
      }
    }
    return null
  }
  return findPath(tree.value, currentFolderId.value, []) || []
})

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}

async function fetchTree() {
  treeLoading.value = true
  try {
    tree.value = await noteService.getTree(notebookId.value)
  } catch (e) {
    console.error('Failed to load tree:', e)
  } finally {
    treeLoading.value = false
  }
}

async function fetchChildren() {
  loading.value = true
  error.value = null
  try {
    children.value = await noteService.getChildren(notebookId.value, currentFolderId.value)
  } catch (e) {
    error.value = '加载失败，请重试'
  } finally {
    loading.value = false
  }
}

async function fetchAll() {
  await Promise.all([fetchTree(), fetchChildren()])
}

function navigateTo(folderId) {
  currentFolderId.value = folderId
  fetchChildren()
}

function openNode(node) {
  if (node.type === 'folder') {
    navigateTo(node.id)
  } else {
    router.push({ name: 'NoteEditor', params: { id: node.id } })
  }
}

async function createFolder() {
  if (!folderForm.value.name.trim()) return
  dialogError.value = null
  try {
    await noteService.createFolder(notebookId.value, {
      name: folderForm.value.name.trim(),
      parent_id: currentFolderId.value,
    })
    showCreateFolder.value = false
    folderForm.value = { name: '' }
    await fetchAll()
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建失败，请重试。'
  }
}

async function createNote() {
  if (!noteForm.value.title.trim()) return
  dialogError.value = null
  try {
    const node = await noteService.createNote(notebookId.value, {
      title: noteForm.value.title.trim(),
      parent_id: currentFolderId.value,
    })
    showCreateNote.value = false
    noteForm.value = { title: '' }
    router.push({ name: 'NoteEditor', params: { id: node.id } })
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '创建失败，请重试。'
  }
}

function startRename(node) {
  renameForm.value = { name: node.name, nodeId: node.id }
  dialogError.value = null
  showRename.value = true
}

async function doRename() {
  if (!renameForm.value.name.trim()) return
  dialogError.value = null
  try {
    await noteService.renameNode(renameForm.value.nodeId, renameForm.value.name.trim())
    showRename.value = false
    await fetchAll()
    showToast('重命名成功')
  } catch (e) {
    dialogError.value = e.response?.data?.detail || '重命名失败。'
  }
}

async function confirmDelete(node) {
  const label = node.type === 'folder' ? '文件夹' : '笔记'
  if (!confirm(`确定要删除${label}「${node.name}」吗？${node.type === 'folder' ? '文件夹内的所有内容将被删除。' : ''}`)) return
  try {
    await noteService.deleteNode(node.id)
    await fetchAll()
    showToast('删除成功')
  } catch (e) {
    showToast('删除失败', 'error')
  }
}

// Auto-focus dialog inputs
watch(showCreateFolder, (open) => {
  if (open) { nextTick(() => folderNameRef.value?.focus()) }
  else { dialogError.value = null }
})
watch(showCreateNote, (open) => {
  if (open) { nextTick(() => noteTitleRef.value?.focus()) }
  else { dialogError.value = null }
})
watch(showRename, (open) => {
  if (open) { nextTick(() => renameRef.value?.select()) }
  else { dialogError.value = null }
})

onMounted(async () => {
  notebook.value = await noteService.getNotebook(notebookId.value)
  await fetchAll()
})
</script>

<!-- Inline TreeItem component -->
<script>
// We'll define TreeItem as a separate component below
</script>

<style scoped>
.file-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

/* Toolbar */
.fm-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-xl);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.fm-breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-sm);
  min-width: 0;
  overflow-x: auto;
}

.breadcrumb-item {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  white-space: nowrap;
  transition: color 0.15s;
}

.breadcrumb-item:hover {
  color: var(--color-primary);
}

.breadcrumb-sep {
  color: var(--color-text-tertiary);
}

.fm-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
  transition: all 0.15s;
  white-space: nowrap;
}

.action-btn:hover {
  background: var(--color-bg-tertiary);
}

.action-btn--primary {
  color: #fff;
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.action-btn--primary:hover {
  background: var(--color-primary-dark);
}

.action-btn svg {
  width: 16px;
  height: 16px;
}

/* Body */
.fm-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* Tree sidebar */
.fm-tree {
  width: 240px;
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
  flex-shrink: 0;
  padding: var(--spacing-md);
}

.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}

.tree-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.tree-close {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: var(--color-text-tertiary);
}

.tree-close svg {
  width: 16px;
  height: 16px;
}

.tree-loading {
  display: flex;
  justify-content: center;
  padding: var(--spacing-lg);
}

.tree-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

/* Content */
.fm-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg) var(--spacing-xl);
  min-width: 0;
}

.tree-toggle {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  color: var(--color-text);
  border-radius: var(--radius-md);
}

.tree-toggle:hover {
  background: var(--color-bg-tertiary);
}

.tree-toggle svg {
  width: 20px;
  height: 20px;
}

/* Node list */
.node-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.node-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.node-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.node-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-icon--folder {
  background: rgba(108, 99, 255, 0.12);
}

.node-icon svg {
  width: 22px;
  height: 22px;
  color: var(--color-primary);
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-name {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-meta {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin: var(--spacing-xs) 0 0;
}

.node-actions {
  display: flex;
  gap: var(--spacing-xs);
  opacity: 0;
  transition: opacity 0.15s;
}

.node-card:hover .node-actions {
  opacity: 1;
}

.node-action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: background 0.15s, color 0.15s;
}

.node-action-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.node-action-btn--danger:hover {
  color: var(--color-error);
}

.node-action-btn svg {
  width: 16px;
  height: 16px;
}

/* Loading, error, empty states */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loading-spinner--sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@keyframes spin { to { transform: rotate(360deg); } }

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  gap: var(--spacing-md);
  color: var(--color-error);
  font-size: var(--font-size-sm);
}

.retry-btn {
  padding: var(--spacing-xs) var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  background: transparent;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  text-align: center;
  color: var(--color-text-tertiary);
}

.empty-icon {
  width: 56px;
  height: 56px;
  margin-bottom: var(--spacing-md);
}

.empty-state h3 {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--spacing-xs);
}

.empty-state p {
  font-size: var(--font-size-sm);
  margin: 0;
}

/* Dialog (reused pattern) */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: var(--spacing-lg);
}

.dialog {
  width: 100%;
  max-width: 440px;
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--color-border);
}

.dialog-title {
  font-size: var(--font-size-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.dialog-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: background 0.15s;
}

.dialog-close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.dialog-close svg {
  width: 18px;
  height: 18px;
}

.dialog-body {
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-text);
}

.form-input {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  color: var(--color-text);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--color-primary);
}

.dialog-error {
  font-size: var(--font-size-sm);
  color: var(--color-error);
  padding: var(--spacing-xs) 0;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-sm);
}

.btn-secondary {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
}

.btn-secondary:hover {
  background: var(--color-bg-tertiary);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: #fff;
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: var(--font-family);
}

.btn-primary:hover {
  background: var(--color-primary-dark);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Toast */
.toast {
  position: fixed;
  bottom: var(--spacing-xl);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--spacing-md) var(--spacing-xl);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  z-index: 200;
  box-shadow: var(--shadow-lg);
  pointer-events: none;
}

.toast.success { background: #10b981; color: white; }
.toast.error { background: #ef4444; color: white; }

.toast-enter-active, .toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(-50%) translateY(20px); }

/* Responsive */
@media (max-width: 767px) {
  .fm-toolbar {
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .fm-actions {
    width: 100%;
  }

  .action-btn {
    flex: 1;
    justify-content: center;
  }

  .fm-tree {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    background: var(--color-card);
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .fm-tree--open {
    transform: translateX(0);
  }

  .tree-close {
    display: flex;
  }

  .tree-toggle {
    display: flex;
  }

  .fm-content {
    padding: var(--spacing-md);
  }
}
</style>
```

- [ ] **Step 2: Create TreeItem component**

Create `frontend/src/components/TreeItem.vue` — a recursive tree node component:

```vue
<!-- frontend/src/components/TreeItem.vue -->
<template>
  <div class="tree-node" :class="{ 'tree-node--active': node.id === currentId }">
    <button class="tree-node-btn" @click="$emit('navigate', node.id)">
      <svg v-if="node.type === 'folder'" class="tree-node-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
      <svg v-else class="tree-node-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
      <span class="tree-node-name">{{ node.name }}</span>
    </button>
    <ul v-if="node.children?.length" class="tree-children">
      <li v-for="child in node.children" :key="child.id">
        <TreeItem :node="child" :current-id="currentId" @navigate="$emit('navigate', $event)" />
      </li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  node: { type: Object, required: true },
  currentId: { type: String, default: null },
})
defineEmits(['navigate'])
</script>

<style scoped>
.tree-node {
  margin-bottom: 2px;
}

.tree-node-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  width: 100%;
  padding: 6px 8px;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text);
  font-size: var(--font-size-sm);
  font-family: var(--font-family);
  text-align: left;
  transition: background 0.15s;
}

.tree-node-btn:hover {
  background: var(--color-bg-tertiary);
}

.tree-node--active > .tree-node-btn {
  background: rgba(108, 99, 255, 0.1);
  color: var(--color-primary);
  font-weight: 600;
}

.tree-node-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.tree-node-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tree-children {
  list-style: none;
  padding-left: 16px;
  margin: 0;
}
</style>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/NotebookFileManage.vue frontend/src/components/TreeItem.vue
git commit -m "feat(notes): add NotebookFileManage view with tree and content list"
```

---

## Task 11: Router and AppLayout Updates

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/components/layout/AppLayout.vue`

- [ ] **Step 1: Update router**

Replace the old notebook/folder routes with new file manager routes. Keep the Notes list page and NoteEditor unchanged:

```javascript
// In router/index.js, replace the notes-related children entries with:
      {
        path: 'notes',
        name: 'Notes',
        component: () => import('../views/Notes.vue')
      },
      {
        path: 'notes/:notebookId',
        name: 'NotebookFileManage',
        component: () => import('../views/NotebookFileManage.vue')
      },
      {
        path: 'notes/edit/:id',
        name: 'NoteEditor',
        component: () => import('../views/NoteEditor.vue')
      },
```

Remove the old routes for `NotebookDetail`, `FolderDetail`, and `NewNote`.

- [ ] **Step 2: Update AppLayout.vue page title mapping**

In `frontend/src/components/layout/AppLayout.vue`, update the `titles` object:

```javascript
    const titles = {
      Home: '首页',
      Todos: '待办',
      Tasks: '任务',
      Goals: '目标',
      Notes: '笔记',
      NotebookFileManage: '笔记本',
      Shop: '商城',
      Backpack: '背包',
      Profile: '个人'
    }
```

- [ ] **Step 3: Update NoteEditor.vue back navigation**

The NoteEditor currently navigates back to `/notes/folder/${folderId}` which no longer exists. Update the `goBack` function:

```javascript
function goBack() {
  router.push('/notes')
}
```

- [ ] **Step 4: Update Notes.vue to navigate to new route**

In `frontend/src/views/Notes.vue`, the `openNotebook` function should navigate to the new route:

```javascript
function openNotebook(notebook) {
  router.push(`/notes/${notebook.id}`)
}
```

This already uses the path `/notes/${notebook.id}` which will match the new `NotebookFileManage` route.

- [ ] **Step 5: Verify frontend builds**

Run: `cd frontend && npm run build`

Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/router/index.js frontend/src/components/layout/AppLayout.vue frontend/src/views/NoteEditor.vue frontend/src/views/Notes.vue
git commit -m "refactor(notes): update router for file manager, remove old routes"
```

---

## Task 12: Delete Old Views

**Files:**
- Delete: `frontend/src/views/NotebookDetail.vue`
- Delete: `frontend/src/views/FolderDetail.vue`

- [ ] **Step 1: Remove old view files**

These are no longer referenced by any route or component.

- [ ] **Step 2: Verify frontend builds**

Run: `cd frontend && npm run build`

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git rm frontend/src/views/NotebookDetail.vue frontend/src/views/FolderDetail.vue
git commit -m "chore(notes): remove old NotebookDetail and FolderDetail views"
```

---

## Task 13: Final Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`

Expected: All tests pass (including existing todo/shop/user/achievement tests).

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`

Expected: Build succeeds.

- [ ] **Step 3: Manual smoke test**

1. Start backend: `cd backend && python -m uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Create a notebook
4. Open the notebook — see empty file manager
5. Create a folder at root
6. Create a note at root
7. Navigate into the folder
8. Create a subfolder and a note inside
9. Rename a node
10. Delete a node
11. Verify same-name conflict shows error
12. Open a note in the editor and save content
13. Verify the tree updates after operations

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix(notes): address verification issues"
```
