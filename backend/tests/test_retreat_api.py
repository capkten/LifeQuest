import uuid
import pytest
from app.models.todo import Task, Difficulty, TaskStatus

def test_retreat_api_full_flow(client, auth_headers, user, db_session):
    # 1. Start a 25 minute retreat
    res = client.post(
        "/api/cultivation/retreat/start",
        json={"target_duration": 25},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_duration"] == 25
    assert data["status"] == "active"
    retreat_id = data["id"]

    # 2. Get active retreat
    active_res = client.get("/api/cultivation/retreat/active", headers=auth_headers)
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data is not None
    assert active_data["id"] == retreat_id

    # 3. Abort retreat
    abort_res = client.post(f"/api/cultivation/retreat/{retreat_id}/abort", headers=auth_headers)
    assert abort_res.status_code == 200
    assert abort_res.json()["status"] == "aborted"

    # 4. Catalog endpoint
    cat_res = client.get("/api/cultivation/retreat/encounters/catalog", headers=auth_headers)
    assert cat_res.status_code == 200
    catalog = cat_res.json()
    assert len(catalog) >= 8

def test_retreat_api_rejects_foreign_todo(client, auth_headers, user, db_session):
    # Create a task belonging to a different user
    foreign_user_id = uuid.uuid4()
    foreign_task = Task(
        title="Other User Secret Task",
        user_id=foreign_user_id,
        difficulty=Difficulty.MEDIUM,
        status=TaskStatus.PENDING,
    )
    db_session.add(foreign_task)
    db_session.commit()

    res = client.post(
        "/api/cultivation/retreat/start",
        json={"target_duration": 25, "todo_id": str(foreign_task.id)},
        headers=auth_headers,
    )
    assert res.status_code in (403, 404)


def test_retreat_api_complete_with_todo(client, auth_headers, user, db_session):
    from datetime import datetime, timezone, timedelta
    from app.models.cultivation_retreat import CultivationRetreat

    # Create task belonging to user
    task = Task(
        title="My Focus Task",
        user_id=user.id,
        difficulty=Difficulty.EASY,
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()

    # Start retreat bound to this task
    start_res = client.post(
        "/api/cultivation/retreat/start",
        json={"target_duration": 25, "todo_id": str(task.id)},
        headers=auth_headers,
    )
    assert start_res.status_code == 200
    retreat_id = start_res.json()["id"]

    # Backdate started_at by 26 minutes to simulate full focus duration
    retreat_obj = db_session.query(CultivationRetreat).filter(CultivationRetreat.id == uuid.UUID(retreat_id)).first()
    retreat_obj.started_at = datetime.now(timezone.utc) - timedelta(minutes=26)
    db_session.commit()

    # Complete retreat with mark_todo_complete = True
    comp_res = client.post(
        f"/api/cultivation/retreat/{retreat_id}/complete",
        json={"mark_todo_complete": True},
        headers=auth_headers,
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "completed"
    assert comp_data["exp_gained"] >= 250
    assert comp_data["coins_gained"] >= 125

    # Verify task status is completed
    db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED

    # Query history
    hist_res = client.get("/api/cultivation/retreat/history", headers=auth_headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert any(h["id"] == retreat_id for h in history)

