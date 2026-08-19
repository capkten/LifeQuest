from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.models.cultivation import CultivationLog, CultivationProfile
from app.models.user import User
from app.services.content_catalog import QUALITY_FACTORS
from app.services.cultivation import CultivationService
from app.services.todo import TodoService


def _register_and_login(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "task6-rework-user",
            "email": "task6-rework@example.com",
            "password": "password123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "task6-rework-user", "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def task6_user(db_session):
    from app.database import Base
    from tests.conftest import engine as test_engine

    Base.metadata.create_all(bind=test_engine)
    user = User(
        username="task6-rework-service-user",
        email="task6-rework-service@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_checkin_preserves_the_legacy_experience_delta(client):
    headers = _register_and_login(client)
    before = client.get("/api/users/me", headers=headers).json()

    response = client.post("/api/checkin", headers=headers)

    assert response.status_code == 200
    after = client.get("/api/users/me", headers=headers).json()
    assert after["experience"] - before["experience"] == response.json()["reward_exp"]


def test_checkin_restores_legacy_snapshot_before_old_reward(monkeypatch, client):
    monkeypatch.setattr(
        CultivationService,
        "_calculate_efficiency",
        lambda self, profile, user_id: 40.0,
    )
    headers = _register_and_login(client)

    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == "task6-rework-user").one()
        user.level = 1
        user.experience = 98
        db.commit()
    finally:
        db.close()

    response = client.post("/api/checkin", headers=headers)

    assert response.status_code == 200
    assert response.json()["cultivation_reward"]["cultivation"] == 200
    after = client.get("/api/users/me", headers=headers).json()
    assert (after["level"], after["experience"]) == (2, 3)


def test_subtask_completion_settles_once_and_replays_the_original_result(
    client, db_session
):
    headers = _register_and_login(client)
    task = client.post(
        "/api/todos/tasks", json={"title": "Parent"}, headers=headers
    ).json()
    subtask = client.post(
        "/api/todos/subtasks",
        json={"task_id": task["id"], "title": "Child"},
        headers=headers,
    ).json()

    first = client.post(
        f"/api/todos/subtasks/{subtask['id']}/complete", headers=headers
    )
    second = client.post(
        f"/api/todos/subtasks/{subtask['id']}/complete", headers=headers
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["cultivation_reward"] == second.json()["cultivation_reward"]
    user_id = UUID(client.get("/api/users/me", headers=headers).json()["id"])
    assert db_session.query(CultivationLog).filter(
        CultivationLog.user_id == user_id,
        CultivationLog.source_key == f"todo:subtask:{subtask['id']}",
    ).count() == 1


def test_replayed_source_key_returns_the_original_efficiency_and_readiness(
    db_session, task6_user
):
    service = TodoService(db_session)
    first = service.cultivation_service.settle_todo_reward(
        task6_user.id,
        "task",
        15,
        "medium",
        source_key="task6:stable-settlement",
    )
    profile = db_session.query(CultivationProfile).filter_by(user_id=task6_user.id).one()
    profile.cultivation_efficiency = 9.9
    profile.minor_stage = 9
    profile.cultivation = 10_000
    db_session.flush()

    replay = service.cultivation_service.settle_todo_reward(
        task6_user.id,
        "task",
        999,
        "very_hard",
        quality=0.75,
        source_key="task6:stable-settlement",
    )

    assert replay.model_dump() == first.model_dump()


def test_todo_completion_quality_reads_the_catalog(monkeypatch):
    deadline = datetime.now(timezone.utc) + timedelta(minutes=1)
    monkeypatch.setitem(QUALITY_FACTORS, "early", 1.23)

    assert TodoService._completion_quality(deadline, datetime.now(timezone.utc)) == 1.23
