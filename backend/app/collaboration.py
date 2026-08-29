import asyncio
import base64
import binascii
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from app.database import SessionLocal
from app.models.note_node import NoteNode
from app.models.note_sharing import NoteCollabDocument, NoteCollabEvent
from app.services.note import NoteService, _write_content_atomically

logger = logging.getLogger(__name__)

MAX_UPDATE_BYTES = 2 * 1024 * 1024
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
INITIALIZATION_LEASE = timedelta(seconds=15)


@dataclass
class Peer:
    websocket: WebSocket
    note_id: UUID
    user_id: UUID
    username: str
    role: str
    cursor: int = 0
    waiting_for_initialization: bool = False

    @property
    def can_edit(self) -> bool:
        return self.role in {"owner", "editor"}


def _encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode(value: str) -> bytes:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, TypeError, ValueError) as exc:
        raise ValueError("COLLAB_INVALID_UPDATE") from exc
    if len(decoded) > MAX_UPDATE_BYTES:
        raise ValueError("COLLAB_UPDATE_TOO_LARGE")
    return decoded


def _load_state(note_id: UUID, session_factory=SessionLocal) -> dict:
    db = session_factory()
    try:
        node = db.get(NoteNode, note_id)
        if not node or node.type != "note":
            raise ValueError("Note not found")
        document = db.query(NoteCollabDocument).filter(NoteCollabDocument.note_id == note_id).first()
        if not document:
            document = NoteCollabDocument(note_id=note_id)
            db.add(document)
            try:
                db.commit()
            except Exception:
                db.rollback()
                document = db.query(NoteCollabDocument).filter(NoteCollabDocument.note_id == note_id).first()

        if not document or not document.initialized or not document.snapshot:
            now = datetime.now(timezone.utc)
            can_claim = (
                not document.init_claimed_at
                or now - document.init_claimed_at.replace(tzinfo=timezone.utc) > INITIALIZATION_LEASE
            )
            return {
                "mode": "init" if can_claim else "wait",
                "content": NoteService(db).get_note_content(note_id),
                "revision": node.content_revision or 1,
                "snapshot_cursor": 0,
            }

        events = (
            db.query(NoteCollabEvent)
            .filter(
                NoteCollabEvent.note_id == note_id,
                NoteCollabEvent.id > (document.snapshot_cursor or 0),
            )
            .order_by(NoteCollabEvent.id.asc())
            .all()
        )
        return {
            "mode": "sync",
            "snapshot": document.snapshot,
            "snapshot_cursor": document.snapshot_cursor or 0,
            "updates": [(event.id, event.update_payload) for event in events],
            "content": document.content if document.content is not None else NoteService(db).get_note_content(note_id),
            "revision": node.content_revision or 1,
        }
    finally:
        db.close()


def _claim_initialization(note_id: UUID, user_id: UUID, session_factory=SessionLocal) -> dict:
    db = session_factory()
    try:
        node = db.get(NoteNode, note_id)
        if not node or node.type != "note":
            raise ValueError("Note not found")
        document = db.query(NoteCollabDocument).filter(NoteCollabDocument.note_id == note_id).first()
        if not document:
            document = NoteCollabDocument(note_id=note_id)
            db.add(document)
            db.flush()
        now = datetime.now(timezone.utc)
        claimed_at = document.init_claimed_at
        if not document.initialized and (
            not claimed_at
            or now - claimed_at.replace(tzinfo=timezone.utc) > INITIALIZATION_LEASE
        ):
            document.init_claimed_at = now
            document.init_claimed_by = user_id
            db.commit()
            return {"mode": "init", "content": NoteService(db).get_note_content(note_id), "revision": node.content_revision or 1}
        db.commit()
        return {"mode": "wait"}
    finally:
        db.close()


def _persist_update(
    note_id: UUID,
    user_id: UUID,
    payload: bytes,
    content: Optional[str],
    session_factory=SessionLocal,
) -> tuple[int, int]:
    db = session_factory()
    previous_content = None
    content_path = None
    try:
        service = NoteService(db)
        access = service.require_node_access(note_id, user_id, write=True)
        node = access["node"]
        if content is not None and len(content) > MAX_CONTENT_LENGTH:
            raise ValueError("COLLAB_CONTENT_TOO_LARGE")
        if content is not None:
            previous_content = service.get_note_content(note_id)
            content_path = node.content_path
            if content_path:
                _write_content_atomically(content_path, content)
            node.word_count = len(content.split())
            node.content_revision = (node.content_revision or 1) + 1
            node.updated_by = user_id
        event = NoteCollabEvent(
            note_id=note_id,
            user_id=user_id,
            update_payload=payload,
            content=content,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event.id, node.content_revision or 1
    except Exception:
        db.rollback()
        if content_path and previous_content is not None:
            try:
                _write_content_atomically(content_path, previous_content)
            except Exception:
                logger.exception("Failed to restore note content after collaboration write failure")
        raise
    finally:
        db.close()


def _persist_snapshot(
    note_id: UUID,
    user_id: UUID,
    snapshot: bytes,
    content: str,
    cursor: int,
    session_factory=SessionLocal,
) -> int:
    if len(snapshot) > MAX_UPDATE_BYTES:
        raise ValueError("COLLAB_SNAPSHOT_TOO_LARGE")
    if len(content) > MAX_CONTENT_LENGTH:
        raise ValueError("COLLAB_CONTENT_TOO_LARGE")
    db = session_factory()
    previous_content = None
    content_path = None
    try:
        service = NoteService(db)
        access = service.require_node_access(note_id, user_id, write=True)
        node = access["node"]
        document = db.query(NoteCollabDocument).filter(NoteCollabDocument.note_id == note_id).first()
        if not document:
            document = NoteCollabDocument(note_id=note_id)
            db.add(document)
            db.flush()

        current_content = service.get_note_content(note_id)
        if content != current_content:
            previous_content = current_content
            content_path = node.content_path
            if content_path:
                _write_content_atomically(content_path, content)
            node.word_count = len(content.split())
            node.content_revision = (node.content_revision or 1) + 1
            node.updated_by = user_id

        max_cursor = db.query(func.max(NoteCollabEvent.id)).filter(NoteCollabEvent.note_id == note_id).scalar() or 0
        document.snapshot = snapshot
        document.snapshot_cursor = min(max(cursor, 0), max_cursor)
        document.content = content
        document.initialized = True
        document.init_claimed_at = None
        document.init_claimed_by = None
        db.commit()
        return node.content_revision or 1
    except Exception:
        db.rollback()
        if content_path and previous_content is not None:
            try:
                _write_content_atomically(content_path, previous_content)
            except Exception:
                logger.exception("Failed to restore note content after snapshot failure")
        raise
    finally:
        db.close()


class CollaborationManager:
    def __init__(self):
        self.rooms: dict[UUID, dict[int, Peer]] = {}
        self.last_event_id = 0
        self._started = False
        self._start_lock = asyncio.Lock()
        self._poll_task = None
        self._locally_emitted: set[int] = set()
        self._session_factory = SessionLocal

    async def _ensure_started(self, session_factory):
        async with self._start_lock:
            if self._started:
                return
            self._session_factory = session_factory
            db = self._session_factory()
            try:
                self.last_event_id = db.query(func.max(NoteCollabEvent.id)).scalar() or 0
            finally:
                db.close()
            self._poll_task = asyncio.create_task(self._poll_events())
            self._started = True

    async def serve(
        self,
        websocket: WebSocket,
        note_id: UUID,
        user_id: UUID,
        username: str,
        role: str,
        session_factory=SessionLocal,
    ):
        await self._ensure_started(session_factory)
        await websocket.accept()
        peer = Peer(websocket, note_id, user_id, username, role)
        room = self.rooms.setdefault(note_id, {})
        room[id(websocket)] = peer
        try:
            await self._send_initial_state(peer)
            await self._broadcast_presence(note_id)
            while True:
                message = await websocket.receive_text()
                await self._handle_message(peer, message)
        except WebSocketDisconnect:
            pass
        finally:
            room = self.rooms.get(note_id)
            if room:
                room.pop(id(websocket), None)
                if not room:
                    self.rooms.pop(note_id, None)
                else:
                    await self._broadcast_presence(note_id)

    async def _send_initial_state(self, peer: Peer):
        state = await asyncio.to_thread(_load_state, peer.note_id, self._session_factory)
        if state["mode"] == "sync":
            await self._send_sync(peer, state)
            return
        claim = await asyncio.to_thread(
            _claim_initialization,
            peer.note_id,
            peer.user_id,
            self._session_factory,
        )
        if claim["mode"] == "init":
            peer.waiting_for_initialization = False
            await peer.websocket.send_json({
                "type": "init",
                "content": claim.get("content", ""),
                "revision": claim.get("revision", 1),
            })
        else:
            peer.waiting_for_initialization = True
            await peer.websocket.send_json({"type": "waiting", "message": "正在等待协作文档初始化"})

    async def _send_sync(self, peer: Peer, state: dict):
        updates = state.get("updates", [])
        peer.cursor = max([state.get("snapshot_cursor", 0), *(event_id for event_id, _ in updates)])
        peer.waiting_for_initialization = False
        await peer.websocket.send_json({
            "type": "sync",
            "snapshot": _encode(state["snapshot"]),
            "snapshot_cursor": state.get("snapshot_cursor", 0),
            "updates": [{"cursor": event_id, "update": _encode(update)} for event_id, update in updates],
            "content": state.get("content", ""),
            "revision": state.get("revision", 1),
        })

    async def _handle_message(self, peer: Peer, raw_message: str):
        try:
            message = json.loads(raw_message)
            message_type = message.get("type")
            if message_type == "update":
                if not peer.can_edit:
                    await peer.websocket.send_json({"type": "error", "code": "READ_ONLY"})
                    return
                payload = _decode(message.get("update", ""))
                content = message.get("content")
                if not isinstance(content, str):
                    raise ValueError("COLLAB_CONTENT_REQUIRED")
                cursor, revision = await asyncio.to_thread(
                    _persist_update,
                    peer.note_id,
                    peer.user_id,
                    payload,
                    content,
                    self._session_factory,
                )
                peer.cursor = cursor
                self.last_event_id = max(self.last_event_id, cursor)
                self._locally_emitted.add(cursor)
                await self._broadcast_update(peer.note_id, {
                    "type": "update",
                    "cursor": cursor,
                    "update": _encode(payload),
                    "user_id": str(peer.user_id),
                    "revision": revision,
                })
                await peer.websocket.send_json({"type": "ack", "cursor": cursor, "revision": revision})
                return
            if message_type == "snapshot":
                if not peer.can_edit:
                    return
                snapshot = _decode(message.get("snapshot", ""))
                content = message.get("content")
                if not isinstance(content, str):
                    raise ValueError("COLLAB_CONTENT_REQUIRED")
                revision = await asyncio.to_thread(
                    _persist_snapshot,
                    peer.note_id,
                    peer.user_id,
                    snapshot,
                    content,
                    int(message.get("cursor", peer.cursor) or 0),
                    self._session_factory,
                )
                await peer.websocket.send_json({"type": "snapshot-ack", "revision": revision})
                await self._notify_waiting_peers(peer.note_id)
                return
            if message_type == "sync-request":
                await self._send_initial_state(peer)
                return
            if message_type == "ping":
                await peer.websocket.send_json({"type": "pong"})
                return
            raise ValueError("COLLAB_UNKNOWN_MESSAGE")
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            await peer.websocket.send_json({"type": "error", "code": str(exc)})

    async def _broadcast_update(self, note_id: UUID, message: dict):
        peers = list(self.rooms.get(note_id, {}).values())
        if not peers:
            return
        results = await asyncio.gather(
            *(peer.websocket.send_json(message) for peer in peers),
            return_exceptions=True,
        )
        for peer, result in zip(peers, results):
            if isinstance(result, Exception):
                self.rooms.get(note_id, {}).pop(id(peer.websocket), None)

    async def _broadcast_presence(self, note_id: UUID):
        users = [
            {"user_id": str(peer.user_id), "username": peer.username, "role": peer.role}
            for peer in self.rooms.get(note_id, {}).values()
        ]
        await self._broadcast_update(note_id, {"type": "presence", "users": users})

    async def _notify_waiting_peers(self, note_id: UUID):
        state = await asyncio.to_thread(_load_state, note_id, self._session_factory)
        peers = [peer for peer in self.rooms.get(note_id, {}).values() if peer.waiting_for_initialization]
        if state.get("mode") == "init":
            for peer in peers:
                claim = await asyncio.to_thread(
                    _claim_initialization,
                    note_id,
                    peer.user_id,
                    self._session_factory,
                )
                if claim.get("mode") == "init":
                    peer.waiting_for_initialization = False
                    await peer.websocket.send_json({
                        "type": "init",
                        "content": claim.get("content", ""),
                        "revision": claim.get("revision", 1),
                    })
                    break
            return
        if state.get("mode") != "sync":
            return
        for peer in peers:
            try:
                await self._send_sync(peer, state)
            except Exception:
                self.rooms.get(note_id, {}).pop(id(peer.websocket), None)

    async def _poll_events(self):
        while True:
            try:
                db = self._session_factory()
                try:
                    events = (
                        db.query(NoteCollabEvent)
                        .filter(NoteCollabEvent.id > self.last_event_id)
                        .order_by(NoteCollabEvent.id.asc())
                        .limit(250)
                        .all()
                    )
                finally:
                    db.close()
                revisions = {}
                if events:
                    db = self._session_factory()
                    try:
                        revisions = {
                            node.id: node.content_revision or 1
                            for node in db.query(NoteNode).filter(
                                NoteNode.id.in_({event.note_id for event in events})
                            ).all()
                        }
                    finally:
                        db.close()
                for event in events:
                    self.last_event_id = max(self.last_event_id, event.id)
                    if event.id in self._locally_emitted:
                        self._locally_emitted.discard(event.id)
                        continue
                    if event.note_id in self.rooms:
                        await self._broadcast_update(event.note_id, {
                            "type": "update",
                            "cursor": event.id,
                            "update": _encode(event.update_payload),
                            "user_id": str(event.user_id),
                            "revision": revisions.get(event.note_id, 1),
                        })
                for note_id in list(self.rooms):
                    await self._notify_waiting_peers(note_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Collaboration event polling failed")
            await asyncio.sleep(0.35)


collaboration_manager = CollaborationManager()
