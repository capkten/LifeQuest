from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta
import pytest
from app.database import Base
from app.models.user import User
from app.models.cultivation_retreat import CultivationRetreat
import mcp_server


@pytest.fixture
def mcp_db(db_session, monkeypatch):
    Base.metadata.create_all(bind=db_session.bind)
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(mcp_server, "_db_initialized", True)
    user = User(
        username=f"mcp-retreat-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    auth_token = mcp_server._auth_user_id.set(user.id)
    try:
        yield db_session, user
    finally:
        mcp_server._auth_user_id.reset(auth_token)
        db_session.rollback()
        Base.metadata.drop_all(bind=db_session.bind)


def test_mcp_focus_session_flow(mcp_db):
    db, user = mcp_db

    # 1. Start a focus session
    session = mcp_server.start_focus_session(target_duration=25)
    assert session is not None
    assert session["target_duration"] == 25
    assert session["status"] == "active"
    session_id = session["id"]

    # 2. Get active focus session
    active = mcp_server.get_active_focus_session()
    assert active is not None
    assert active["id"] == session_id

    # 3. Simulate elapsed duration
    retreat_obj = db.query(CultivationRetreat).filter(CultivationRetreat.id == UUID(session_id)).first()
    retreat_obj.started_at = datetime.now(timezone.utc) - timedelta(minutes=26)
    db.commit()

    # 4. Complete focus session
    completed = mcp_server.complete_focus_session(session_id=session_id)
    assert completed is not None
    assert completed["status"] == "completed"
    assert completed["exp_gained"] >= 250

    # 5. Verify active session is now None
    assert mcp_server.get_active_focus_session() is None


def test_mcp_abort_and_todo_linkage(mcp_db):
    db, user = mcp_db

    # Test abort
    session1 = mcp_server.start_focus_session(target_duration=30)
    aborted = mcp_server.abort_focus_session(session1["id"])
    assert aborted["status"] == "aborted"
    assert mcp_server.get_active_focus_session() is None

    # Test todo linkage
    task = mcp_server.create_task("MCP 专注关联任务", priority="high")
    session2 = mcp_server.start_focus_session(target_duration=15, todo_id=task["id"])
    assert session2["todo_id"] == task["id"]

    # Backdate started_at
    retreat_obj = db.query(CultivationRetreat).filter(CultivationRetreat.id == UUID(session2["id"])).first()
    retreat_obj.started_at = datetime.now(timezone.utc) - timedelta(minutes=16)
    db.commit()

    completed2 = mcp_server.complete_focus_session(session_id=session2["id"], mark_todo_complete=True)
    assert completed2["status"] == "completed"

    # Verify task completed
    tasks = mcp_server.list_tasks()
    matching = [t for t in tasks if t["id"] == task["id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "completed"

