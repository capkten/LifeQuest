from datetime import date
from uuid import UUID

from app.models.task_schedule import TaskOccurrence
from app.services.task_schedule import TaskScheduleService


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


def _create_task(client, headers, title, **overrides):
    payload = {
        "title": title,
        "deadline": "2026-08-31T09:00:00+08:00",
        "coins_reward": 1,
        "exp_reward": 1,
    }
    payload.update(overrides)
    response = client.post("/api/todos/tasks", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_daily_schedule_materializes_occurrences_until_target(client, db_session):
    headers = _login(client, "schedule-daily-user")
    task = _create_task(
        client,
        headers,
        "Daily review",
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-31",
            "ends_on": "2026-09-02",
        },
    )

    service = TaskScheduleService(db_session)
    occurrences = service.materialize_until(
        UUID(task["user_id"]), date(2026, 9, 5)
    )

    assert [item.occurrence_date for item in occurrences] == [
        date(2026, 8, 31),
        date(2026, 9, 1),
        date(2026, 9, 2),
    ]
    assert db_session.query(TaskOccurrence).count() == 3


def test_weekly_and_monthly_rules_are_deterministic(client, db_session):
    headers = _login(client, "schedule-rule-user")
    weekly = _create_task(
        client,
        headers,
        "Weekly planning",
        schedule={
            "rule_type": "weekly",
            "interval": 2,
            "weekdays": [0, 2],
            "starts_on": "2026-08-31",
            "ends_on": "2026-09-20",
        },
    )
    monthly = _create_task(
        client,
        headers,
        "Monthly review",
        schedule={
            "rule_type": "monthly",
            "starts_on": "2026-01-31",
            "ends_on": "2026-03-31",
        },
    )

    service = TaskScheduleService(db_session)
    weekly_dates = [
        item.occurrence_date
        for item in service.materialize_until(UUID(weekly["user_id"]), date(2026, 9, 20))
        if str(item.task_id) == weekly["id"]
    ]
    monthly_dates = [
        item.occurrence_date
        for item in service.materialize_until(UUID(monthly["user_id"]), date(2026, 3, 31))
        if str(item.task_id) == monthly["id"]
    ]

    assert weekly_dates == [
        date(2026, 8, 31),
        date(2026, 9, 2),
        date(2026, 9, 14),
        date(2026, 9, 16),
    ]
    assert monthly_dates == [date(2026, 1, 31), date(2026, 3, 31)]


def test_schedule_rejects_invalid_weekdays_and_month_days(client):
    headers = _login(client, "schedule-validation-user")
    invalid_weekday = client.post(
        "/api/todos/tasks",
        json={
            "title": "Invalid weekday",
            "schedule": {"rule_type": "weekly", "weekdays": [7]},
        },
        headers=headers,
    )
    invalid_month_day = client.post(
        "/api/todos/tasks",
        json={
            "title": "Invalid month day",
            "schedule": {"rule_type": "monthly", "day_of_month": 32},
        },
        headers=headers,
    )

    assert invalid_weekday.status_code == 422
    assert invalid_month_day.status_code == 422


def test_recurring_completion_is_idempotent_per_occurrence(client, db_session):
    headers = _login(client, "schedule-completion-user")
    task = _create_task(
        client,
        headers,
        "Complete recurring task",
        coins_reward=20,
        exp_reward=10,
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-31",
        },
    )

    first = client.post(
        f"/api/todos/tasks/{task['id']}/complete?occurrence_date=2026-08-31",
        headers=headers,
    )
    second = client.post(
        f"/api/todos/tasks/{task['id']}/complete?occurrence_date=2026-08-31",
        headers=headers,
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["occurrence_date"] == "2026-08-31"
    assert first.json()["occurrence_status"] == "completed"
    assert second.json()["occurrence_status"] == "completed"
    occurrence = db_session.query(TaskOccurrence).one()
    assert occurrence.status == "completed"
    assert occurrence.completed_at is not None

    from app.models.cultivation import CultivationLog

    logs = db_session.query(CultivationLog).filter(
        CultivationLog.user_id == UUID(task["user_id"]),
        CultivationLog.source_key == f"task:{task['id']}:2026-08-31",
    ).all()
    assert len(logs) == 1


def test_recurring_completion_uses_the_occurrence_deadline_for_quality(
    client, db_session, monkeypatch
):
    headers = _login(client, "schedule-quality-user")
    task = _create_task(
        client,
        headers,
        "Occurrence quality task",
        deadline="2026-08-31T09:00:00+08:00",
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-31",
        },
    )

    captured = {}

    def capture_quality(deadline, completed_at):
        captured["deadline"] = deadline
        return 1.0

    from app.services.todo import TodoService

    monkeypatch.setattr(
        TodoService,
        "_completion_quality",
        staticmethod(capture_quality),
    )

    completion = client.post(
        f"/api/todos/tasks/{task['id']}/complete?occurrence_date=2026-09-01",
        headers=headers,
    )

    assert completion.status_code == 200, completion.text
    assert captured["deadline"].date() == date(2026, 9, 1)


def test_completed_recurring_occurrence_cannot_be_rescheduled(client):
    headers = _login(client, "schedule-completed-occurrence-user")
    task = _create_task(
        client,
        headers,
        "Completed occurrence",
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-31",
        },
    )

    completed = client.post(
        f"/api/todos/tasks/{task['id']}/complete?occurrence_date=2026-08-31",
        headers=headers,
    )
    rejected = client.patch(
        f"/api/todos/tasks/{task['id']}/schedule",
        json={
            "occurrence_date": "2026-08-31",
            "new_occurrence_date": "2026-09-01",
        },
        headers=headers,
    )

    assert completed.status_code == 200, completed.text
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "TASK_ALREADY_COMPLETED"


def test_rescheduled_occurrence_does_not_reappear_on_its_original_date(
    client, db_session
):
    headers = _login(client, "schedule-occurrence-move-user")
    task = _create_task(
        client,
        headers,
        "Move one occurrence",
        schedule={
            "rule_type": "weekly",
            "weekdays": [0],
            "starts_on": "2026-08-31",
            "ends_on": "2026-09-14",
        },
    )

    moved = client.patch(
        f"/api/todos/tasks/{task['id']}/schedule",
        json={
            "occurrence_date": "2026-08-31",
            "new_occurrence_date": "2026-09-02",
        },
        headers=headers,
    )
    assert moved.status_code == 200, moved.text

    occurrences = TaskScheduleService(db_session).materialize_until(
        UUID(task["user_id"]), date(2026, 9, 14)
    )
    task_dates = sorted(
        item.occurrence_date
        for item in occurrences
        if str(item.task_id) == task["id"]
    )

    assert task_dates == [date(2026, 9, 2), date(2026, 9, 7), date(2026, 9, 14)]


def test_snooze_hides_task_until_requested_local_date(client):
    headers = _login(client, "schedule-snooze-user")
    task = _create_task(client, headers, "Snoozable task")

    snoozed = client.post(
        f"/api/todos/tasks/{task['id']}/snooze",
        json={
            "occurrence_date": "2026-08-31",
            "until": "2026-09-02T09:00:00+08:00",
        },
        headers=headers,
    )
    assert snoozed.status_code == 200, snoozed.text

    hidden = client.get(
        "/api/action-center/today?date=2026-08-31",
        headers=headers,
    )
    visible_again = client.get(
        "/api/action-center/today?date=2026-09-02",
        headers=headers,
    )

    assert hidden.status_code == 200
    assert hidden.json()["sections"]["today"] == []
    assert visible_again.status_code == 200
    assert visible_again.json()["sections"]["overdue"][0]["id"] == task["id"]


def test_reschedule_rejects_past_and_completed_tasks_and_is_user_scoped(client):
    owner_headers = _login(client, "schedule-reschedule-owner")
    other_headers = _login(client, "schedule-reschedule-other")
    task = _create_task(client, owner_headers, "Reschedulable task")

    past = client.patch(
        f"/api/todos/tasks/{task['id']}/schedule",
        json={"deadline": "2020-01-01T09:00:00+08:00"},
        headers=owner_headers,
    )
    forbidden = client.patch(
        f"/api/todos/tasks/{task['id']}/schedule",
        json={"deadline": "2026-09-03T09:00:00+08:00"},
        headers=other_headers,
    )
    moved = client.patch(
        f"/api/todos/tasks/{task['id']}/schedule",
        json={"deadline": "2026-09-03T09:00:00+08:00"},
        headers=owner_headers,
    )
    completed = client.post(
        f"/api/todos/tasks/{task['id']}/complete",
        headers=owner_headers,
    )
    rejected = client.patch(
        f"/api/todos/tasks/{task['id']}/schedule",
        json={"deadline": "2026-09-04T09:00:00+08:00"},
        headers=owner_headers,
    )

    assert past.status_code == 422
    assert forbidden.status_code == 403
    assert moved.status_code == 200, moved.text
    assert moved.json()["deadline"].startswith("2026-09-03")
    assert completed.status_code == 200
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "TASK_ALREADY_COMPLETED"
