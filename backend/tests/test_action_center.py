from datetime import datetime, timezone
from uuid import UUID

from app.models.todo import Habit, Task


def _login(client, username):
    email = f"{username}@example.com"
    registered = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "testpassword123"},
    )
    assert registered.status_code == 200
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "testpassword123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_task(client, headers, title, deadline, priority="medium"):
    response = client.post(
        "/api/todos/tasks",
        json={
            "title": title,
            "deadline": deadline,
            "priority": priority,
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_action_center_orders_open_tasks_and_excludes_completed_tasks(client, db_session):
    headers = _login(client, "action-order-user")
    overdue = _create_task(
        client,
        headers,
        "Overdue task",
        "2026-08-30T08:00:00+00:00",
        priority="low",
    )
    today_high = _create_task(
        client,
        headers,
        "High priority task",
        "2026-08-31T10:00:00+00:00",
        priority="high",
    )
    today_urgent = _create_task(
        client,
        headers,
        "Urgent priority task",
        "2026-08-31T12:00:00+00:00",
        priority="urgent",
    )
    completed = _create_task(
        client,
        headers,
        "Already completed task",
        "2026-08-31T08:00:00+00:00",
    )
    completion = client.post(
        f"/api/todos/tasks/{completed['id']}/complete",
        headers=headers,
    )
    assert completion.status_code == 200
    completed_row = db_session.get(Task, UUID(completed["id"]))
    completed_row.completed_at = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    db_session.commit()

    response = client.get(
        "/api/action-center/today?date=2026-08-31",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["date"] == "2026-08-31"
    assert payload["timezone"] == "Asia/Shanghai"
    assert [item["id"] for item in payload["sections"]["overdue"]] == [overdue["id"]]
    assert [item["id"] for item in payload["sections"]["today"]] == [
        today_urgent["id"],
        today_high["id"],
    ]
    assert all(
        item["id"] != completed["id"]
        for section in payload["sections"].values()
        for item in section
    )
    assert payload["summary"]["overdue_count"] == 1
    assert payload["summary"]["open_count"] == 3
    assert payload["summary"]["completed_count"] >= 1
    assert payload["next_action"]["id"] == overdue["id"]


def test_action_center_is_scoped_to_current_user(client):
    first_headers = _login(client, "action-scope-first")
    second_headers = _login(client, "action-scope-second")
    first_task = _create_task(
        client,
        first_headers,
        "First user's task",
        "2026-08-31T09:00:00+00:00",
    )
    _create_task(
        client,
        second_headers,
        "Second user's task",
        "2026-08-31T09:00:00+00:00",
    )

    response = client.get(
        "/api/action-center/today?date=2026-08-31",
        headers=first_headers,
    )

    assert response.status_code == 200
    items = response.json()["sections"]["today"]
    assert [item["id"] for item in items] == [first_task["id"]]


def test_action_center_uses_habit_frequency_and_completed_state(client, db_session):
    headers = _login(client, "action-habit-user")
    weekly = client.post(
        "/api/todos/habits",
        json={"title": "Weekly habit", "frequency": "weekly"},
        headers=headers,
    )
    daily = client.post(
        "/api/todos/habits",
        json={"title": "Daily habit", "frequency": "daily"},
        headers=headers,
    )
    assert weekly.status_code == 200
    assert daily.status_code == 200

    weekly_row = db_session.get(Habit, UUID(weekly.json()["id"]))
    daily_row = db_session.get(Habit, UUID(daily.json()["id"]))
    weekly_row.created_at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    daily_row.created_at = datetime(2026, 8, 31, tzinfo=timezone.utc)
    weekly_row.last_completed_at = datetime(2026, 8, 31, 1, tzinfo=timezone.utc)
    db_session.commit()

    response = client.get(
        "/api/action-center/today?date=2026-08-31",
        headers=headers,
    )

    assert response.status_code == 200
    habits = response.json()["sections"]["habits"]
    assert [item["title"] for item in habits] == ["Weekly habit", "Daily habit"]
    assert habits[0]["completed"] is True
    assert habits[1]["completed"] is False
    assert response.json()["summary"]["habit_due_count"] == 2
    assert response.json()["summary"]["habit_completed_count"] == 1


def test_action_center_returns_empty_sections_and_no_next_action(client):
    headers = _login(client, "action-empty-user")

    response = client.get(
        "/api/action-center/today?date=2026-08-31",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sections"] == {
        "overdue": [],
        "today": [],
        "habits": [],
        "calendar": [],
    }
    assert payload["summary"] == {
        "open_count": 0,
        "overdue_count": 0,
        "completed_count": 0,
        "habit_due_count": 0,
        "habit_completed_count": 0,
    }
    assert payload["next_action"] is None
