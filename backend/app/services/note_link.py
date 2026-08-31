from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.note_link import GoalNoteLink, ProjectNoteLink, TaskNoteLink
from app.models.note_node import NoteNode
from app.models.project import Project
from app.models.todo import Goal, Task
from app.schemas.note_link import LinkKind
from app.services.note import NoteService


class NoteLinkService:
    """Manage explicit links without weakening either side's ownership rules."""

    _LINK_MODELS = {
        "task": (TaskNoteLink, Task, "task_id"),
        "goal": (GoalNoteLink, Goal, "goal_id"),
        "project": (ProjectNoteLink, Project, "project_id"),
    }

    def __init__(self, db: Session):
        self.db = db
        self.note_service = NoteService(db)

    def _require_note(self, note_id: UUID, user_id: UUID, write: bool = False) -> tuple[NoteNode, dict]:
        access = self.note_service.require_node_access(note_id, user_id, write=write)
        note = access["node"]
        if note.type != "note":
            raise ValueError("NOTE_REQUIRED")
        return note, access

    def _require_target(self, kind: LinkKind, target_id: UUID, user_id: UUID):
        model_info = self._LINK_MODELS.get(kind)
        if model_info is None:
            raise ValueError("LINK_KIND_INVALID")
        target = self.db.get(model_info[1], target_id)
        if target is None:
            raise ValueError("TARGET_NOT_FOUND")
        if target.user_id != user_id:
            raise PermissionError("Not authorized")
        return target, model_info

    @staticmethod
    def _target_url(kind: str, target_id: UUID) -> str:
        if kind == "task":
            return f"/todos?task_id={target_id}"
        if kind == "goal":
            return f"/todos?tab=goals&goal_id={target_id}"
        return f"/projects/{target_id}"

    @staticmethod
    def _note_url(note: NoteNode) -> str:
        return f"/notes/{note.notebook_id}/view/{note.id}"

    def _target_summary(self, kind: str, target) -> dict:
        return {
            "kind": kind,
            "id": target.id,
            "title": target.name if kind == "project" else target.title,
            "url": self._target_url(kind, target.id),
        }

    def _note_summary(self, note: NoteNode) -> dict:
        return {
            "kind": "note",
            "id": note.id,
            "title": note.name,
            "url": self._note_url(note),
        }

    def list_for_note(self, note_id: UUID, user_id: UUID) -> list[dict]:
        self._require_note(note_id, user_id)
        summaries = []
        for kind, (link_model, target_model, target_field) in self._LINK_MODELS.items():
            rows = (
                self.db.query(link_model, target_model)
                .join(target_model, getattr(link_model, target_field) == target_model.id)
                .filter(link_model.note_id == note_id, target_model.user_id == user_id)
                .order_by(link_model.created_at.asc())
                .all()
            )
            summaries.extend(self._target_summary(kind, target) for _link, target in rows)
        return summaries

    def list_for_target(self, kind: LinkKind, target_id: UUID, user_id: UUID) -> list[dict]:
        _target, (link_model, _target_model, target_field) = self._require_target(kind, target_id, user_id)
        rows = (
            self.db.query(NoteNode)
            .join(link_model, link_model.note_id == NoteNode.id)
            .filter(getattr(link_model, target_field) == target_id, NoteNode.type == "note")
            .order_by(link_model.created_at.asc())
            .all()
        )
        summaries = []
        for note in rows:
            if self.note_service.get_notebook_access(note.notebook_id, user_id):
                summaries.append(self._note_summary(note))
        return summaries

    def link(self, note_id: UUID, kind: LinkKind, target_id: UUID, user_id: UUID) -> dict:
        note, _access = self._require_note(note_id, user_id, write=True)
        target, (link_model, _target_model, target_field) = self._require_target(kind, target_id, user_id)
        existing = self.db.query(link_model).filter(
            link_model.note_id == note.id,
            getattr(link_model, target_field) == target.id,
        ).first()
        if existing:
            raise ValueError("LINK_ALREADY_EXISTS")
        self.db.add(link_model(note_id=note.id, **{target_field: target.id}))
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("LINK_ALREADY_EXISTS") from exc
        return self._target_summary(kind, target)

    def unlink(self, note_id: UUID, kind: LinkKind, target_id: UUID, user_id: UUID) -> None:
        self._require_note(note_id, user_id, write=True)
        self._require_target(kind, target_id, user_id)
        link_model, _target_model, target_field = self._LINK_MODELS[kind]
        link = self.db.query(link_model).filter(
            link_model.note_id == note_id,
            getattr(link_model, target_field) == target_id,
        ).first()
        if link is None:
            raise ValueError("LINK_NOT_FOUND")
        self.db.delete(link)
        self.db.commit()

    def link_target(self, kind: LinkKind, target_id: UUID, note_id: UUID, user_id: UUID) -> dict:
        return self.link(note_id, kind, target_id, user_id)

    def unlink_target(self, kind: LinkKind, target_id: UUID, note_id: UUID, user_id: UUID) -> None:
        self.unlink(note_id, kind, target_id, user_id)

    def remove_for_note(self, note_id: UUID) -> None:
        for link_model, _target_model, _target_field in self._LINK_MODELS.values():
            self.db.query(link_model).filter(link_model.note_id == note_id).delete(synchronize_session=False)

    def remove_for_target(self, kind: LinkKind, target_id: UUID) -> None:
        link_model, _target_model, target_field = self._LINK_MODELS[kind]
        self.db.query(link_model).filter(getattr(link_model, target_field) == target_id).delete(
            synchronize_session=False
        )
