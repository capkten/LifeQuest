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

    # Verify rewards: task (20 coins, 15 exp) + "初出茅庐" achievement (50 coins, 100 exp)
    # 115 total exp triggers level-up at level 1 (requires 100): 115-100=15, level becomes 2
    user_after = client.get("/api/users/me", headers=headers).json()
    assert user_after["coins"] == coins_before + 70
    assert user_after["experience"] == 15
    assert user_after["level"] == 2


def test_complete_habit_awards_rewards(client):
    headers = _register_and_login(client)

    # Create a habit
    create_response = client.post(
        "/api/todos/habits",
        json={
            "title": "Morning exercise",
            "description": "Do 30 minutes of exercise",
            "difficulty": "medium",
            "coins_reward": 15,
            "exp_reward": 10,
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    habit_id = create_response.json()["id"]

    # Get user state before completion
    user_before = client.get("/api/users/me", headers=headers).json()
    coins_before = user_before["coins"]
    exp_before = user_before["experience"]

    # Complete the habit
    complete_response = client.post(
        f"/api/todos/habits/{habit_id}/complete",
        headers=headers,
    )
    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["streak"] == 1
    assert completed["best_streak"] == 1

    # Verify rewards were awarded
    user_after = client.get("/api/users/me", headers=headers).json()
    assert user_after["coins"] == coins_before + 15
    assert user_after["experience"] == exp_before + 10


def test_complete_goal_awards_rewards(client):
    headers = _register_and_login(client)

    # Create a goal
    create_response = client.post(
        "/api/todos/goals",
        json={
            "title": "Learn a new language",
            "difficulty": "hard",
            "coins_reward": 100,
            "exp_reward": 50,
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    goal_id = create_response.json()["id"]

    user_before = client.get("/api/users/me", headers=headers).json()
    coins_before = user_before["coins"]
    exp_before = user_before["experience"]

    # Complete the goal
    complete_response = client.post(
        f"/api/todos/goals/{goal_id}/complete",
        headers=headers,
    )
    assert complete_response.status_code == 200
    completed = complete_response.json()
    assert completed["status"] == "completed"
    assert completed["progress"] == 100.0

    # Verify rewards
    user_after = client.get("/api/users/me", headers=headers).json()
    assert user_after["coins"] == coins_before + 100
    assert user_after["experience"] == exp_before + 50


def test_complete_task_idempotent(client):
    """Completing a task twice should only award rewards once."""
    headers = _register_and_login(client)

    create_response = client.post(
        "/api/todos/tasks",
        json={
            "title": "Idempotent test",
            "difficulty": "medium",
            "coins_reward": 20,
            "exp_reward": 15,
        },
        headers=headers,
    )
    task_id = create_response.json()["id"]

    # First completion
    resp1 = client.post(f"/api/todos/tasks/{task_id}/complete", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "completed"

    user_after_first = client.get("/api/users/me", headers=headers).json()

    # Second completion - should not award rewards again
    resp2 = client.post(f"/api/todos/tasks/{task_id}/complete", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "completed"

    user_after_second = client.get("/api/users/me", headers=headers).json()
    assert user_after_second["coins"] == user_after_first["coins"]
    assert user_after_second["experience"] == user_after_first["experience"]


def test_complete_goal_idempotent(client):
    """Completing a goal twice should only award rewards once."""
    headers = _register_and_login(client)

    create_response = client.post(
        "/api/todos/goals",
        json={
            "title": "Idempotent goal test",
            "difficulty": "hard",
            "coins_reward": 100,
            "exp_reward": 50,
        },
        headers=headers,
    )
    goal_id = create_response.json()["id"]

    # First completion
    resp1 = client.post(f"/api/todos/goals/{goal_id}/complete", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "completed"

    user_after_first = client.get("/api/users/me", headers=headers).json()

    # Second completion - should not award rewards again
    resp2 = client.post(f"/api/todos/goals/{goal_id}/complete", headers=headers)
    assert resp2.status_code == 200

    user_after_second = client.get("/api/users/me", headers=headers).json()
    assert user_after_second["coins"] == user_after_first["coins"]
    assert user_after_second["experience"] == user_after_first["experience"]


def test_complete_habit_idempotent(client):
    """Completing a habit twice on the same day should only award rewards once."""
    headers = _register_and_login(client)

    create_response = client.post(
        "/api/todos/habits",
        json={
            "title": "Daily habit",
            "difficulty": "medium",
            "coins_reward": 15,
            "exp_reward": 10,
        },
        headers=headers,
    )
    habit_id = create_response.json()["id"]

    # First completion
    resp1 = client.post(f"/api/todos/habits/{habit_id}/complete", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["streak"] == 1

    user_after_first = client.get("/api/users/me", headers=headers).json()

    # Second completion same day - should not award rewards again
    resp2 = client.post(f"/api/todos/habits/{habit_id}/complete", headers=headers)
    assert resp2.status_code == 200
    # Streak should not increase
    assert resp2.json()["streak"] == 1

    user_after_second = client.get("/api/users/me", headers=headers).json()
    assert user_after_second["coins"] == user_after_first["coins"]
    assert user_after_second["experience"] == user_after_first["experience"]
