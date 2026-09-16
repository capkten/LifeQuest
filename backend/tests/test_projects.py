import pytest
from fastapi import HTTPException
from uuid import UUID, uuid4

from app.models.achievement import Achievement, UserAchievement
from app.models.coin_transaction import CoinTransaction
from app.models.project import Project, ProjectPhase
from app.models.todo import Task
from app.models.user import User
from app.schemas.project import PhaseCreate, ProjectUpdate
from app.services.project import ProjectService


def _register_and_login(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "projectuser",
            "email": "project@example.com",
            "password": "testpassword123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": "projectuser", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_move_task_persists_status(client):
    headers = _register_and_login(client)

    project_response = client.post(
        "/api/projects",
        json={
            "name": "项目A",
            "description": "测试项目",
            "color": "#0EA5E9",
            "icon": "folder",
        },
        headers=headers,
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    task_response = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "title": "任务A",
            "difficulty": "medium",
            "coins_reward": 10,
            "exp_reward": 5,
        },
        headers=headers,
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["id"]

    move_response = client.put(
        f"/api/projects/tasks/{task_id}/move",
        json={"status": "completed"},
        headers=headers,
    )

    assert move_response.status_code == 200
    assert move_response.json()["status"] == "completed"


def test_project_start_is_idempotent(client, auth_headers, project):
    first = client.post(f"/api/projects/{project.id}/start", headers=auth_headers)
    second = client.post(f"/api/projects/{project.id}/start", headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "active"


def test_project_rejects_unknown_status(client, auth_headers, project):
    response = client.put(
        f"/api/projects/{project.id}",
        headers=auth_headers,
        json={"status": "unknown"},
    )
    assert response.status_code == 422


def test_project_status_lifecycle_rejects_skipped_transitions(client, auth_headers, project):
    skipped = client.put(
        f"/api/projects/{project.id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert skipped.status_code == 409

    started = client.post(f"/api/projects/{project.id}/start", headers=auth_headers)
    assert started.status_code == 200
    completed = client.put(
        f"/api/projects/{project.id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    archived = client.put(
        f"/api/projects/{project.id}",
        headers=auth_headers,
        json={"status": "archived"},
    )
    assert archived.status_code == 200


def test_reaching_milestone_is_idempotent(client, auth_headers, project):
    milestone = client.post(
        f"/api/projects/{project.id}/milestones",
        headers=auth_headers,
        json={"name": "完成首个版本"},
    ).json()
    first = client.post(
        f"/api/projects/milestones/{milestone['id']}/reach",
        headers=auth_headers,
    )
    second = client.post(
        f"/api/projects/milestones/{milestone['id']}/reach",
        headers=auth_headers,
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["status"] == second.json()["status"] == "reached"
    assert first.json()["reached_at"] == second.json()["reached_at"]


def test_project_put_completion_settles_achievement_once_and_keeps_fields(
    client, auth_headers, project, db_session,
):
    achievement = Achievement(
        name=f"PUT completion {uuid4().hex}",
        description="Completion through project update",
        icon="test",
        condition_type="project_completed",
        condition_value=1,
        coin_reward=7,
        exp_reward=11,
    )
    db_session.add(achievement)
    db_session.commit()
    user = db_session.query(User).filter_by(id=project.user_id).one()
    initial_coins = user.coins
    initial_experience = user.experience

    started = client.post(f"/api/projects/{project.id}/start", headers=auth_headers)
    completed = client.put(
        f"/api/projects/{project.id}",
        headers=auth_headers,
        json={
            "status": "completed",
            "name": "Settled by PUT",
            "description": "Fields stay editable with completion",
        },
    )
    repeated = client.put(
        f"/api/projects/{project.id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    explicit = client.post(
        f"/api/projects/{project.id}/complete",
        headers=auth_headers,
    )

    assert started.status_code == 200
    assert completed.status_code == repeated.status_code == explicit.status_code == 200
    assert completed.json()["name"] == "Settled by PUT"
    assert completed.json()["description"] == "Fields stay editable with completion"
    db_session.expire_all()
    persisted = db_session.query(Project).filter_by(id=project.id).one()
    persisted_user = db_session.query(User).filter_by(id=project.user_id).one()
    assert persisted.status == "completed"
    assert persisted.name == "Settled by PUT"
    assert persisted.description == "Fields stay editable with completion"
    assert db_session.query(UserAchievement).filter_by(
        user_id=project.user_id,
        achievement_id=achievement.id,
    ).count() == 1
    reward_rows = db_session.query(CoinTransaction).filter_by(
        user_id=project.user_id,
        source_id=f"a:{achievement.id.hex}",
    ).all()
    assert len(reward_rows) == 1
    assert reward_rows[0].amount == 7
    assert persisted_user.coins == initial_coins + 7
    assert persisted_user.experience == initial_experience + 11


def test_project_completion_rolls_back_status_and_rewards_when_reward_write_fails(
    client, auth_headers, project, db_session, monkeypatch,
):
    project.status = "active"
    achievement = Achievement(
        name="项目奖励回滚测试",
        description="测试项目完成奖励的一致性",
        icon="test",
        condition_type="project_completed",
        condition_value=1,
        coin_reward=7,
        exp_reward=11,
    )
    db_session.add(achievement)
    db_session.commit()
    initial_coins = project.user.coins
    initial_experience = project.user.experience
    service = ProjectService(db_session)
    db_project = db_session.query(Project).filter(Project.id == project.id).one()
    original_create_reward = service.achievement_service.coin_repo._create_no_commit

    def fail_reward_write(data):
        original_create_reward(data)
        raise RuntimeError("reward write failed")

    monkeypatch.setattr(
        service.achievement_service.coin_repo,
        "_create_no_commit",
        fail_reward_write,
    )

    with pytest.raises(RuntimeError, match="reward write failed"):
        service.complete_project(db_project)

    db_session.rollback()
    persisted_project = db_session.query(Project).filter(Project.id == project.id).one()
    persisted_user = persisted_project.user
    assert persisted_project.status == "active"
    assert persisted_user.coins == initial_coins
    assert persisted_user.experience == initial_experience
    assert db_session.query(UserAchievement).filter_by(
        user_id=project.user_id,
        achievement_id=achievement.id,
    ).count() == 0
    assert db_session.query(CoinTransaction).filter_by(
        user_id=project.user_id,
        source="achievement",
    ).count() == 0


def test_phase_status_create_update_boundaries_normalize_legacy_reads_and_reject_unknown_writes(
    client, auth_headers, project, db_session,
):
    unknown_create = client.post(
        f"/api/projects/{project.id}/phases",
        headers=auth_headers,
        json={"name": "未知状态阶段", "status": "unknown"},
    )
    assert unknown_create.status_code == 422

    created = client.post(
        f"/api/projects/{project.id}/phases",
        headers=auth_headers,
        json={"name": "阶段边界", "status": "active"},
    )
    assert created.status_code == 200
    assert created.json()["status"] == "active"
    phase_id = UUID(created.json()["id"])

    phase = db_session.query(ProjectPhase).filter(ProjectPhase.id == phase_id).one()
    for stored_status, response_status in (
        ("pending", "planning"),
        ("in_progress", "active"),
        ("completed", "completed"),
        ("old_phase_state", "unknown"),
    ):
        phase.status = stored_status
        db_session.commit()
        detail = client.get(f"/api/projects/{project.id}", headers=auth_headers)
        assert detail.status_code == 200
        phase_response = next(
            item for item in detail.json()["phases"] if item["id"] == str(phase_id)
        )
        assert phase_response["status"] == response_status

    updated = client.put(
        f"/api/projects/phases/{phase_id}",
        headers=auth_headers,
        json={"status": "active"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "active"

    unknown_update = client.put(
        f"/api/projects/phases/{phase_id}",
        headers=auth_headers,
        json={"status": "unknown"},
    )
    assert unknown_update.status_code == 422


def test_project_task_rejects_cross_project_references(client):
    headers_a = _register_and_login(client)
    client.post(
        "/api/auth/register",
        json={
            "username": "projectuserb",
            "email": "project-b@example.com",
            "password": "testpassword123",
        },
    )
    login_b = client.post(
        "/api/auth/login",
        data={"username": "projectuserb", "password": "testpassword123"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    project_a = client.post(
        "/api/projects", json={"name": "A"}, headers=headers_a
    ).json()
    project_b = client.post(
        "/api/projects", json={"name": "B"}, headers=headers_b
    ).json()
    phase_b = client.post(
        f"/api/projects/{project_b['id']}/phases",
        json={"name": "B phase"},
        headers=headers_b,
    ).json()
    milestone_b = client.post(
        f"/api/projects/{project_b['id']}/milestones",
        json={"name": "B milestone"},
        headers=headers_b,
    ).json()

    task_response = client.post(
        f"/api/projects/{project_a['id']}/tasks",
        json={
            "title": "A task",
            "phase_id": phase_b["id"],
            "milestone_id": milestone_b["id"],
        },
        headers=headers_a,
    )
    assert task_response.status_code == 403


def test_delete_project_phase_with_tasks_requires_explicit_policy(client):
    headers = _register_and_login(client)
    project = client.post(
        "/api/projects", json={"name": "Phase ownership"}, headers=headers
    ).json()
    phase = client.post(
        f"/api/projects/{project['id']}/phases",
        json={"name": "Owned tasks"},
        headers=headers,
    ).json()
    task = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"title": "Keep me", "phase_id": phase["id"]},
        headers=headers,
    ).json()

    response = client.delete(
        f"/api/projects/phases/{phase['id']}", headers=headers
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "PROJECT_PHASE_HAS_TASKS"
    assert detail["task_count"] == 1

    project_tasks = client.get(
        f"/api/projects/{project['id']}/tasks", headers=headers
    ).json()
    assert project_tasks[0]["id"] == task["id"]
    assert project_tasks[0]["phase_id"] == phase["id"]


def test_phase_deletion_requires_authorized_project_owner(client):
    owner_headers = _register_and_login(client)
    project = client.post(
        "/api/projects", json={"name": "Private phase"}, headers=owner_headers
    ).json()
    phase = client.post(
        f"/api/projects/{project['id']}/phases",
        json={"name": "Owner only"},
        headers=owner_headers,
    ).json()

    assert client.delete(f"/api/projects/phases/{phase['id']}").status_code == 401

    client.post(
        "/api/auth/register",
        json={
            "username": "projectuserb",
            "email": "project-b@example.com",
            "password": "testpassword123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": "projectuserb", "password": "testpassword123"},
    )
    other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.delete(
        f"/api/projects/phases/{phase['id']}", headers=other_headers
    )

    assert response.status_code == 403
    detail = client.get(f"/api/projects/{project['id']}", headers=owner_headers).json()
    assert any(item["id"] == phase["id"] for item in detail["phases"])


def test_repeated_phase_deletion_with_tasks_returns_stable_conflict(client):
    headers = _register_and_login(client)
    project = client.post(
        "/api/projects", json={"name": "Stable phase error"}, headers=headers
    ).json()
    phase = client.post(
        f"/api/projects/{project['id']}/phases",
        json={"name": "Still has work"},
        headers=headers,
    ).json()
    client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"title": "Blocking task", "phase_id": phase["id"]},
        headers=headers,
    )

    responses = [
        client.delete(f"/api/projects/phases/{phase['id']}", headers=headers)
        for _ in range(2)
    ]

    assert [response.status_code for response in responses] == [409, 409]
    assert [response.json()["detail"] for response in responses] == [
        {
            "code": "PROJECT_PHASE_HAS_TASKS",
            "message": "阶段仍有 1 个任务，请先移动任务后再删除。",
            "task_count": 1,
        },
        {
            "code": "PROJECT_PHASE_HAS_TASKS",
            "message": "阶段仍有 1 个任务，请先移动任务后再删除。",
            "task_count": 1,
        },
    ]


def test_phase_deletion_rechecks_tasks_added_during_transaction(
    client, db_session, monkeypatch
):
    headers = _register_and_login(client)
    project = client.post(
        "/api/projects", json={"name": "Atomic phase delete"}, headers=headers
    ).json()
    phase = client.post(
        f"/api/projects/{project['id']}/phases",
        json={"name": "Race window"},
        headers=headers,
    ).json()
    service = ProjectService(db_session)
    phase_id = UUID(phase["id"])
    db_phase = db_session.query(ProjectPhase).filter(ProjectPhase.id == phase_id).one()
    original_count_tasks = service.phase_repo.count_tasks

    def count_then_insert_task(candidate_phase_id):
        count = original_count_tasks(candidate_phase_id)
        if count == 0:
            db_session.add(
                Task(
                    user_id=db_phase.project.user_id,
                    project_id=db_phase.project_id,
                    phase_id=candidate_phase_id,
                    title="Inserted while deleting",
                )
            )
            db_session.flush()
        return count

    monkeypatch.setattr(service.phase_repo, "count_tasks", count_then_insert_task)

    with pytest.raises(HTTPException) as error:
        service.delete_phase(db_phase)

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "PROJECT_PHASE_HAS_TASKS"
    assert db_session.query(ProjectPhase).filter(ProjectPhase.id == phase_id).one()
    assert db_session.query(Task).filter(Task.phase_id == phase_id).count() == 0


def test_project_update_can_clear_existing_dates(client):
    headers = _register_and_login(client)
    project = client.post(
        "/api/projects",
        json={"name": "Date clearing", "start_date": "2026-08-01", "end_date": "2026-08-31"},
        headers=headers,
    ).json()

    response = client.put(
        f"/api/projects/{project['id']}",
        json={"start_date": None, "end_date": None},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["start_date"] is None
    assert response.json()["end_date"] is None


def test_project_update_rolls_back_when_persistence_fails(client, db_session, monkeypatch):
    headers = _register_and_login(client)
    project = client.post(
        "/api/projects", json={"name": "Keep original"}, headers=headers
    ).json()
    service = ProjectService(db_session)
    project_id = UUID(project["id"])
    db_project = db_session.query(Project).filter(Project.id == project_id).one()

    def fail_update(project_obj, update_data):
        project_obj.name = update_data["name"]
        raise RuntimeError("write failed")

    monkeypatch.setattr(service.project_repo, "update", fail_update)

    with pytest.raises(RuntimeError, match="write failed"):
        service.update_project(db_project, ProjectUpdate(name="Must not persist"))

    assert db_session.query(Project).filter(Project.id == project_id).one().name == "Keep original"


def test_phase_creation_rolls_back_when_persistence_fails(client, db_session, monkeypatch):
    headers = _register_and_login(client)
    project = client.post(
        "/api/projects", json={"name": "Phase rollback"}, headers=headers
    ).json()
    service = ProjectService(db_session)

    def fail_create(data):
        db_session.add(ProjectPhase(**data))
        raise RuntimeError("phase write failed")

    monkeypatch.setattr(service.phase_repo, "create", fail_create)

    with pytest.raises(RuntimeError, match="phase write failed"):
        service.create_phase(project["id"], PhaseCreate(name="Must not persist"))

    project_id = UUID(project["id"])
    assert db_session.query(ProjectPhase).filter(ProjectPhase.project_id == project_id).count() == 0


def test_project_delete_rolls_back_task_detachment_when_persistence_fails(client, db_session, monkeypatch):
    headers = _register_and_login(client)
    project = client.post(
        "/api/projects", json={"name": "Delete rollback"}, headers=headers
    ).json()
    task = client.post(
        f"/api/projects/{project['id']}/tasks",
        json={"title": "Keep project ownership"},
        headers=headers,
    ).json()
    service = ProjectService(db_session)
    project_id = UUID(project["id"])
    db_project = db_session.query(Project).filter(Project.id == project_id).one()

    def fail_delete(_project_id):
        raise RuntimeError("delete failed")

    monkeypatch.setattr(service.project_repo, "delete", fail_delete)

    with pytest.raises(RuntimeError, match="delete failed"):
        service.delete_project(db_project)

    persisted_task = db_session.query(Task).filter(Task.id == UUID(task["id"])).one()
    assert persisted_task.project_id == project_id
    assert persisted_task.phase_id is None
