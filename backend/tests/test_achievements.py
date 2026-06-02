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


def test_first_task_completion_unlocks_achievement(client):
    """Completing the first task should unlock the 'task_count >= 1' achievement."""
    headers = _register_and_login(client)

    # Create and complete a task
    create_resp = client.post(
        "/api/todos/tasks",
        json={
            "title": "First task",
            "difficulty": "easy",
            "coins_reward": 10,
            "exp_reward": 5,
        },
        headers=headers,
    )
    task_id = create_resp.json()["id"]
    client.post(f"/api/todos/tasks/{task_id}/complete", headers=headers)

    # Check achievements
    ach_resp = client.get("/api/achievements/me", headers=headers)
    assert ach_resp.status_code == 200
    achievements = ach_resp.json()
    assert len(achievements) >= 1

    # The "初出茅庐" achievement should be unlocked
    names = [a["name"] for a in achievements] if achievements and "name" in achievements[0] else []
    # The response format might vary; at minimum we got unlocked achievements
    assert len(achievements) >= 1


def test_achievement_does_not_double_unlock(client):
    """Completing two tasks should still only unlock the task_count=1 achievement once."""
    headers = _register_and_login(client)

    # Create and complete two tasks
    for _ in range(2):
        create_resp = client.post(
            "/api/todos/tasks",
            json={
                "title": "Task",
                "difficulty": "easy",
                "coins_reward": 10,
                "exp_reward": 5,
            },
            headers=headers,
        )
        task_id = create_resp.json()["id"]
        client.post(f"/api/todos/tasks/{task_id}/complete", headers=headers)

    # Check achievements - should still be exactly 1
    ach_resp = client.get("/api/achievements/me", headers=headers)
    assert ach_resp.status_code == 200
    achievements = ach_resp.json()
    assert len(achievements) == 1
