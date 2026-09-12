from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.coin_transaction import CoinTransaction
from app.models.daily_workbench import DailyFocusPlan, WorkbenchTaskRequest
from app.models.todo import Task
from app.models.user import User
from app.schemas.daily_workbench import DailyFocusUpdate, QuickTaskCreate
from app.services.auth import create_access_token
from app.services.daily_workbench import DailyWorkbenchService


@pytest.fixture
def clock(monkeypatch):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant[0].astimezone(tz) if tz else instant[0].replace(tzinfo=None)

    monkeypatch.setattr("app.timezone.datetime", FrozenDatetime)
    monkeypatch.setattr("app.services.todo.datetime", FrozenDatetime)
    return lambda value: instant.__setitem__(0, value)


def make_user(session):
    name = uuid4().hex
    user = User(username=name, email=f"{name}@example.com", password_hash="unused")
    session.add(user)
    session.commit()
    return user


def headers(user):
    return {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}


def make_task(session, user, **values):
    task = Task(user_id=user.id, title=values.pop("title", "任务"), **values)
    session.add(task)
    session.commit()
    return task


def focus_payload(tasks, revision=0, day="2026-09-12"):
    return {"date": day, "revision": revision, "task_ids": [str(task.id) for task in tasks]}


def test_workbench_groups_china_dates_and_isolates_users(client, db_session, clock):
    user, other = make_user(db_session), make_user(db_session)
    tasks = {
        "overdue": make_task(db_session, user, deadline=datetime(2026, 9, 11, 15, 59, 59)),
        "today": make_task(db_session, user, deadline=datetime(2026, 9, 11, 16)),
        "upcoming": make_task(db_session, user, deadline=datetime(2026, 9, 12, 16)),
        "unscheduled": make_task(db_session, user),
    }
    make_task(db_session, other, title="他人的任务")
    make_task(db_session, user, status="completed", completed_at=datetime(2026, 9, 11, 16))
    make_task(db_session, user, status="cancelled")
    response = client.get("/api/todos/workbench", headers=headers(user))
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-09-12"
    assert body["summary"]["completed_today"] == 1
    assert body["summary"]["open_tasks"] == 4
    for group, task in tasks.items():
        assert [row["id"] for row in body["task_groups"][group]] == [str(task.id)]
    assert body["revision"] == 0
    assert body["focus_tasks"] == []


def test_corrupt_focus_ids_are_filtered_without_failing_workbench(client, db_session, clock):
    user = make_user(db_session)
    valid = make_task(db_session, user, title="仍然有效")
    missing_id = str(uuid4())
    plan = DailyFocusPlan(
        user_id=user.id,
        plan_date=date(2026, 9, 12),
        task_ids=["not-a-uuid", str(valid.id), str(valid.id), missing_id],
        revision=4,
    )
    db_session.add(plan)
    db_session.commit()

    response = client.get("/api/todos/workbench", headers=headers(user))

    assert response.status_code == 200
    body = response.json()
    assert [task["id"] for task in body["focus_tasks"]] == [str(valid.id)]
    assert body["revision"] == 4
    db_session.refresh(plan)
    assert plan.task_ids == ["not-a-uuid", str(valid.id), str(valid.id), missing_id]


def test_focus_order_persists_without_changing_task_priority(client, db_session, clock):
    user = make_user(db_session)
    tasks = [make_task(db_session, user, title=str(index), priority="low") for index in range(3)]
    auth = headers(user)
    response = client.put("/api/todos/workbench/focus", headers=auth, json=focus_payload(tasks))
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    reversed_tasks = list(reversed(tasks))
    response = client.put("/api/todos/workbench/focus", headers=auth, json=focus_payload(reversed_tasks, 1))
    assert response.status_code == 200
    latest = client.get("/api/todos/workbench", headers=auth).json()
    assert [row["id"] for row in latest["focus_tasks"]] == [str(task.id) for task in reversed_tasks]
    assert all(row["priority"] == "low" for row in latest["focus_tasks"])
    assert latest["revision"] == 2


@pytest.mark.parametrize("invalid", ["four", "duplicate", "foreign", "missing", "cancelled"])
def test_focus_rejects_invalid_selections(client, db_session, clock, invalid):
    user = make_user(db_session)
    task = make_task(db_session, user)
    tasks = [task]
    expected = 404
    if invalid == "four":
        tasks += [make_task(db_session, user) for index in range(3)]
        expected = 422
    elif invalid == "duplicate":
        tasks += [task]
        expected = 422
    elif invalid == "foreign":
        tasks = [make_task(db_session, make_user(db_session))]
    elif invalid == "cancelled":
        tasks = [make_task(db_session, user, status="cancelled")]
    payload = focus_payload(tasks)
    if invalid == "missing":
        payload["task_ids"] = [str(uuid4())]
    response = client.put("/api/todos/workbench/focus", headers=headers(user), json=payload)
    assert response.status_code == expected
    assert db_session.query(DailyFocusPlan).count() == 0


def test_stale_focus_edit_cannot_overwrite_another_device(client, db_session, clock):
    user = make_user(db_session)
    first, second = make_task(db_session, user), make_task(db_session, user)
    auth = headers(user)
    client.put("/api/todos/workbench/focus", headers=auth, json=focus_payload([first]))
    rejected = client.put("/api/todos/workbench/focus", headers=auth, json=focus_payload([second]))
    assert rejected.status_code == 409
    latest = client.get("/api/todos/workbench", headers=auth).json()
    assert latest["focus_tasks"][0]["id"] == str(first.id)


def test_focus_resets_at_china_midnight_and_rejects_old_day(client, db_session, clock):
    user = make_user(db_session)
    task = make_task(db_session, user)
    auth = headers(user)
    client.put("/api/todos/workbench/focus", headers=auth, json=focus_payload([task]))
    clock(datetime(2026, 9, 12, 16, tzinfo=timezone.utc))
    today = client.get("/api/todos/workbench", headers=auth).json()
    assert today["date"] == "2026-09-13"
    assert today["focus_tasks"] == []
    assert today["revision"] == 0
    assert client.put("/api/todos/workbench/focus", headers=auth, json=focus_payload([task], 1)).status_code == 409
    assert client.put("/api/todos/workbench/focus", headers=auth,
                      json=focus_payload([task], day="2026-09-13")).status_code == 200
    assert db_session.query(DailyFocusPlan).count() == 2


def test_completed_focus_stays_visible_and_rewards_only_once(client, db_session, clock):
    user = make_user(db_session)
    task = make_task(db_session, user)
    auth = headers(user)
    client.put("/api/todos/workbench/focus", headers=auth, json=focus_payload([task]))
    for attempt in range(2):
        assert client.post(f"/api/todos/tasks/{task.id}/complete", headers=auth).status_code == 200
    board = client.get("/api/todos/workbench", headers=auth).json()
    assert board["focus_tasks"][0]["status"] == "completed"
    assert board["summary"]["focus_completed"] == 1
    assert board["summary"]["completed_today"] == 1
    assert board["summary"]["open_tasks"] == 0
    assert db_session.query(CoinTransaction).filter_by(user_id=user.id, source="task").count() == 1
    client.delete(f"/api/todos/tasks/{task.id}", headers=auth)
    assert client.get("/api/todos/workbench", headers=auth).json()["focus_tasks"] == []


@pytest.mark.parametrize("schedule,due_date,expected", [
    ("today", None, "2026-09-12T15:59:59.999999Z"),
    ("unscheduled", None, None),
    ("date", "2026-09-20", "2026-09-20T15:59:59.999999Z"),
])
def test_quick_create_uses_china_day_deadlines(client, db_session, clock, schedule, due_date, expected):
    user = make_user(db_session)
    payload = {"title": "  快速任务  ", "schedule": schedule, "due_date": due_date, "request_id": str(uuid4())}
    response = client.post("/api/todos/workbench/tasks", headers=headers(user), json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "快速任务"
    assert response.json()["deadline"] == expected


def test_quick_create_retry_does_not_duplicate_and_changed_payload_conflicts(client, db_session, clock):
    user = make_user(db_session)
    auth = headers(user)
    payload = {"title": "快速任务", "request_id": str(uuid4())}
    first = client.post("/api/todos/workbench/tasks", headers=auth, json=payload)
    retry = client.post("/api/todos/workbench/tasks", headers=auth, json=payload)
    assert first.json()["id"] == retry.json()["id"]
    assert db_session.query(Task).count() == 1
    assert client.post("/api/todos/workbench/tasks", headers=auth, json={**payload, "title": "不同内容"}).status_code == 409
    client.delete(f"/api/todos/tasks/{first.json()['id']}", headers=auth)
    assert client.post("/api/todos/workbench/tasks", headers=auth, json=payload).status_code == 409
    assert db_session.query(Task).count() == 0


def test_quick_create_persists_canonical_idempotency_payload(client, db_session, clock):
    user = make_user(db_session)
    request_id = uuid4()
    response = client.post("/api/todos/workbench/tasks", headers=headers(user), json={
        "title": "  规范任务  ", "schedule": "date", "due_date": "2026-09-20", "request_id": str(request_id),
    })

    assert response.status_code == 200
    request = db_session.query(WorkbenchTaskRequest).filter_by(user_id=user.id, request_id=request_id).one()
    assert request.payload == {"title": "规范任务", "schedule": "date", "due_date": "2026-09-20"}


@pytest.mark.parametrize("changes", [{"title": "   "}, {"title": "长" * 201}, {"schedule": "date"}, {"schedule": "unknown"}])
def test_quick_create_validates_input(client, db_session, clock, changes):
    payload = {"title": "任务", "request_id": str(uuid4()), **changes}
    response = client.post("/api/todos/workbench/tasks", headers=headers(make_user(db_session)), json=payload)
    assert response.status_code == 422
    assert db_session.query(Task).count() == 0


@pytest.fixture
def file_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'workbench.sqlite'}", connect_args={"timeout": 30})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as session:
        yield session, factory
    engine.dispose()


@pytest.mark.parametrize("operation", ["focus", "create"])
def test_parallel_workbench_writes_are_serialized(file_database, clock, operation):
    session, factory = file_database
    user = make_user(session)
    task = make_task(session, user)
    user_id, task_id, request_id = user.id, task.id, uuid4()
    barrier = Barrier(2)

    def write():
        with factory() as worker:
            barrier.wait(timeout=10)
            service = DailyWorkbenchService(worker)
            try:
                if operation == "focus":
                    service.update_focus(user_id, DailyFocusUpdate(date=date(2026, 9, 12), revision=0, task_ids=[task_id]))
                    return "saved"
                return str(service.create_quick_task(user_id, QuickTaskCreate(title="新任务", request_id=request_id)).id)
            except HTTPException as error:
                assert error.status_code == 409
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write) for attempt in range(2)]
        results = [future.result(timeout=40) for future in futures]
    if operation == "focus":
        assert sorted(results) == ["conflict", "saved"]
        assert session.query(DailyFocusPlan).count() == 1
    else:
        assert results[0] == results[1]
        assert session.query(WorkbenchTaskRequest).count() == 1
        assert session.query(Task).count() == 2


def test_quick_create_commit_failure_rolls_back_request_and_task(file_database, clock, monkeypatch):
    session, factory = file_database
    user = make_user(session)

    def fail():
        raise RuntimeError("commit failed")

    monkeypatch.setattr(session, "commit", fail)
    with pytest.raises(RuntimeError):
        DailyWorkbenchService(session).create_quick_task(user.id, QuickTaskCreate(title="任务", request_id=uuid4()))
    assert session.query(Task).count() == 0
    assert session.query(WorkbenchTaskRequest).count() == 0
