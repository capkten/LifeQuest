from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

import mcp_server
from app.database import Base
from app.models.user import User
from app.models.cultivation_retreat import CultivationRetreat


@pytest.fixture
def retreat_tools(db_session, monkeypatch):
    from app.mcp.retreat import register
    Base.metadata.create_all(db_session.bind)
    users = [User(username=uuid4().hex, email=f"{uuid4().hex}@example.com", password_hash="hashed") for _ in range(2)]
    db_session.add_all(users)
    db_session.commit()
    owner_id, other_id = [user.id for user in users]
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(mcp_server, "_db_initialized", True)
    auth = mcp_server._auth_user_id.set(owner_id)
    tools = {}
    class Registry:
        def tool(self):
            def decorate(fn):
                tools[fn.__name__] = fn
                return fn
            return decorate
    register(Registry(), mcp_server._resolve_user_id, mcp_server._serialize, lambda: db_session)
    try:
        yield tools, db_session, owner_id, other_id
    finally:
        mcp_server._auth_user_id.reset(auth)
        db_session.rollback()
        Base.metadata.drop_all(db_session.bind)


def test_retreat_history_and_catalog_are_user_scoped(retreat_tools):
    tools, db, owner_id, other_id = retreat_tools
    own = CultivationRetreat(user_id=owner_id, target_duration=25, status="aborted", started_at=datetime.now(timezone.utc))
    db.add_all([own, CultivationRetreat(user_id=other_id, target_duration=25, status="aborted", started_at=datetime.now(timezone.utc))])
    db.commit()
    own_id = str(own.id)
    assert [item["id"] for item in tools["get_focus_session_history"]()] == [own_id]
    assert tools["get_focus_session_history"](offset=1) == []
    catalog = tools["get_encounter_catalog"]()
    assert catalog and all(not event["unlocked"] for event in catalog)
    for kwargs in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        with pytest.raises(ValueError):
            tools["get_focus_session_history"](**kwargs)


def test_focus_settlement_server_clock_replay_and_ownership(retreat_tools, monkeypatch):
    tools, db, owner_id, other_id = retreat_tools
    from app.models.coin_transaction import CoinTransaction
    from app.services.encounter_engine import EncounterEngine
    monkeypatch.setattr(EncounterEngine, "roll_encounter", lambda **kwargs: None)
    session = mcp_server.start_focus_session(25)
    aborted = mcp_server.complete_focus_session(session["id"])
    assert aborted["status"] == "aborted" and aborted["coins_gained"] == 0
    experience = db.get(User, owner_id).experience
    with pytest.raises(HTTPException):
        mcp_server.complete_focus_session(session["id"])
    assert db.get(User, owner_id).experience == experience
    session = mcp_server.start_focus_session(25)
    db.get(CultivationRetreat, UUID(session["id"])).started_at = datetime.now(timezone.utc) - timedelta(minutes=25)
    db.commit()
    finished = mcp_server.complete_focus_session(session["id"])
    assert finished["status"] == "completed" and finished["coins_gained"] == 125
    assert db.query(CoinTransaction).filter_by(user_id=owner_id, source_id=session["id"]).count() == 1
    with pytest.raises(HTTPException):
        mcp_server.complete_focus_session(session["id"])
    assert db.query(CoinTransaction).filter_by(user_id=owner_id, source_id=session["id"]).count() == 1
    assert len(tools["get_focus_session_history"]()) == 2
    mcp_server._auth_user_id.set(other_id)
    assert tools["get_focus_session_history"]() == []
    with pytest.raises(HTTPException):
        mcp_server.complete_focus_session(session["id"])


@pytest.mark.parametrize("duration", [-5, 0, 241])
def test_focus_service_rejects_out_of_range_duration(retreat_tools, duration):
    with pytest.raises(ValueError):
        mcp_server.start_focus_session(duration)


def test_one_minute_focus_cannot_instantly_claim_rewards(retreat_tools):
    _, db, owner_id, _ = retreat_tools
    before = db.get(User, owner_id).experience
    started = mcp_server.start_focus_session(1)
    result = mcp_server.complete_focus_session(started["id"])
    assert result["status"] == "aborted"
    assert result["coins_gained"] == result["exp_gained"] == 0
    assert db.get(User, owner_id).experience == before


def test_linked_task_uses_normal_rewards_and_failure_rolls_back_focus(retreat_tools, monkeypatch):
    _, db, owner_id, _ = retreat_tools
    from app.models.todo import Task, TaskStatus
    from app.models.coin_transaction import CoinTransaction
    from app.services.encounter_engine import EncounterEngine
    from app.services.todo import TodoService
    monkeypatch.setattr(EncounterEngine, "roll_encounter", lambda **kwargs: None)
    task = mcp_server.create_task("linked focus")
    started = mcp_server.start_focus_session(25, task["id"])
    db.get(CultivationRetreat, UUID(started["id"])).started_at = datetime.now(timezone.utc) - timedelta(minutes=25)
    db.commit()
    before_coins = db.get(User, owner_id).coins
    before_earned = db.get(User, owner_id).total_coins_earned
    original = TodoService.complete_task
    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("task completion failed")
    monkeypatch.setattr(TodoService, "complete_task", fail)
    with pytest.raises(RuntimeError, match="task completion failed"):
        mcp_server.complete_focus_session(started["id"], True)
    assert db.get(CultivationRetreat, UUID(started["id"])).status == "active"
    assert db.get(User, owner_id).coins == before_coins
    monkeypatch.setattr(TodoService, "complete_task", original)
    mcp_server.complete_focus_session(started["id"], True)
    assert db.get(Task, UUID(task["id"])).status == TaskStatus.COMPLETED
    assert db.get(User, owner_id).coins == before_coins + 125 + task["coins_reward"]
    assert db.get(User, owner_id).total_coins_earned == before_earned + 125 + task["coins_reward"]
    assert db.query(CoinTransaction).filter_by(user_id=owner_id, source="task").count() == 1


def test_concurrent_focus_settlement_rewards_once(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.coin_transaction import CoinTransaction
    from app.services.cultivation_retreat import CultivationRetreatService
    from app.services.encounter_engine import EncounterEngine
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(EncounterEngine, "roll_encounter", lambda **kwargs: None)
    with sessions() as db:
        user = User(username=uuid4().hex, email=f"{uuid4().hex}@example.com", password_hash="hashed")
        db.add(user)
        db.commit()
        user_id = user.id
        retreat = CultivationRetreatService.start_retreat(db, user_id, 25)
        retreat.started_at = datetime.now(timezone.utc) - timedelta(minutes=25)
        db.commit()
        retreat_id = retreat.id
    barrier = Barrier(2)
    def settle():
        with sessions() as db:
            barrier.wait(timeout=10)
            try:
                return CultivationRetreatService.complete_retreat(db, user_id, retreat_id).status
            except HTTPException as exc:
                return exc.status_code
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: settle(), range(2)))
        assert sorted(str(result) for result in results) == ["404", "completed"]
        with sessions() as db:
            assert db.get(User, user_id).coins == 125
            assert db.get(User, user_id).total_coins_earned == 125
            assert db.query(CoinTransaction).filter_by(user_id=user_id).count() == 1
    finally:
        engine.dispose()
