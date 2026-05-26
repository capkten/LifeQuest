def _register_and_login(client):
    """Helper: register a user and return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_task(client):
    headers = _register_and_login(client)

    response = client.post(
        "/api/todos/tasks",
        json={
            "title": "Learn Python",
            "description": "Complete Python tutorial",
            "difficulty": "hard",
            "coins_reward": 30,
            "exp_reward": 20,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Learn Python"
    assert data["difficulty"] == "hard"
    assert data["status"] == "pending"
    assert data["coins_reward"] == 30
    assert data["exp_reward"] == 20
    assert data["id"] is not None

    # Verify the task appears in the list
    list_response = client.get("/api/todos/tasks", headers=headers)
    assert list_response.status_code == 200
    tasks = list_response.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == data["id"]


def test_complete_task_awards_rewards(client):
    headers = _register_and_login(client)

    # Create a task
    create_response = client.post(
        "/api/todos/tasks",
        json={
            "title": "Complete project",
            "difficulty": "medium",
            "coins_reward": 20,
            "exp_reward": 15,
        },
        headers=headers,
    )
    task_id = create_response.json()["id"]

    # Get user state before completion
    user_before = client.get("/api/users/me", headers=headers).json()
    coins_before = user_before["coins"]
    exp_before = user_before["experience"]

    # Complete the task
    complete_response = client.post(
        f"/api/todos/tasks/{task_id}/complete",
        headers=headers,
    )
    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None

    # Verify rewards were awarded
    user_after = client.get("/api/users/me", headers=headers).json()
    assert user_after["coins"] == coins_before + 20
    assert user_after["experience"] == exp_before + 15
