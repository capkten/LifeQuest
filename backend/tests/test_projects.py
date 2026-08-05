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
