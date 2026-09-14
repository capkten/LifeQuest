from uuid import uuid4

import pytest
from fastapi import HTTPException

import mcp_server
from app.database import Base
from app.models.user import User


@pytest.fixture
def mcp_crud_db(db_session, monkeypatch):
    Base.metadata.create_all(bind=db_session.bind)
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(mcp_server, "_db_initialized", True)
    user = User(
        username=f"mcp-crud-{uuid4().hex[:8]}",
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


def test_mcp_todo_tools_cover_lifecycle(mcp_crud_db):
    goal = mcp_server.create_goal("年度目标", difficulty="hard")
    assert mcp_server.complete_goal(goal["id"])["status"] == "completed"

    task = mcp_server.create_task("主任务", priority="high")
    subtask = mcp_server.create_subtask(task["id"], "子任务")
    assert mcp_server.complete_subtask(subtask["id"])["is_completed"] is True
    assert mcp_server.delete_subtask(subtask["id"])["status"] == "ok"

    habit = mcp_server.create_habit(
        "指定日期习惯", frequency="weekdays", weekdays=[0, 2, 4]
    )
    assert mcp_server.pause_habit(habit["id"])["is_active"] is False
    assert mcp_server.resume_habit(habit["id"])["is_active"] is True

    workbench = mcp_server.get_workbench()
    quick = mcp_server.create_quick_task(
        "快速任务", schedule="unscheduled", request_id=str(uuid4())
    )
    assert quick["title"] == "快速任务"
    assert mcp_server.update_daily_focus(
        workbench["date"], workbench["revision"], [task["id"]]
    )["focus_tasks"]


def test_mcp_adapters_preserve_extended_fields(mcp_crud_db):
    task = mcp_server.create_task(
        "计划任务",
        start_date="2026-09-14T08:00:00+08:00",
        priority="urgent",
    )
    assert task["priority"] == "urgent"
    assert task["start_date"].startswith("2026-09-14T00:00:00")

    habit = mcp_server.create_habit(
        "工作日习惯", frequency="weekdays", weekdays=[4, 0, 2]
    )
    assert habit["weekdays"] == [0, 2, 4]

    updated = mcp_server.update_habit(habit["id"], weekdays=[1, 3, 5])
    assert updated["weekdays"] == [1, 3, 5]

    daily_habit = mcp_server.create_habit("带备注习惯")
    mcp_server.complete_habit(daily_habit["id"], note="完成记录")
    history = mcp_server.get_habit_history(daily_habit["id"])
    assert any(day["note"] == "完成记录" for day in history["days"])


def test_mcp_adapters_reject_other_users_for_read_complete_and_delete(mcp_crud_db):
    db, owner = mcp_crud_db
    owner_id = owner.id
    task = mcp_server.create_task("私有任务")
    goal = mcp_server.create_goal("私有目标")
    habit = mcp_server.create_habit("私有习惯")
    other_user = User(
        username=f"mcp-other-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
    )
    db.add(other_user)
    db.commit()
    mcp_server._auth_user_id.set(other_user.id)

    with pytest.raises(HTTPException):
        mcp_server.list_subtasks(task["id"])
    with pytest.raises(HTTPException):
        mcp_server.complete_goal(goal["id"])
    with pytest.raises(HTTPException):
        mcp_server.delete_habit(habit["id"])

    mcp_server._auth_user_id.set(owner_id)
    assert mcp_server.list_tasks()[0]["id"] == task["id"]


def test_mcp_workbench_revision_and_quick_task_idempotency(mcp_crud_db):
    task = mcp_server.create_task("重点任务")
    workbench = mcp_server.get_workbench()
    updated = mcp_server.update_daily_focus(
        workbench["date"], workbench["revision"], [task["id"]]
    )
    assert updated["revision"] == workbench["revision"] + 1
    with pytest.raises(HTTPException, match="其他页面更新"):
        mcp_server.update_daily_focus(workbench["date"], workbench["revision"], [])

    request_id = str(uuid4())
    first = mcp_server.create_quick_task(
        "幂等任务", schedule="unscheduled", request_id=request_id
    )
    retry = mcp_server.create_quick_task(
        "幂等任务", schedule="unscheduled", request_id=request_id
    )
    assert retry["id"] == first["id"]
    with pytest.raises(HTTPException, match="其他内容"):
        mcp_server.create_quick_task(
            "不同任务", schedule="unscheduled", request_id=request_id
        )
