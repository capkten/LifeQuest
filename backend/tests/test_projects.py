import pytest
from uuid import UUID

from app.models.project import Project, ProjectPhase
from app.models.todo import Task
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
