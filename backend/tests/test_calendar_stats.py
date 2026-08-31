def _login(client):
    client.post(
        "/api/auth/register",
        json={"username": "calendar-user", "email": "calendar@example.com", "password": "testpassword123"},
    )
    token = client.post(
        "/api/auth/login",
        data={"username": "calendar-user", "password": "testpassword123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_calendar_filters_date_range_and_stats_use_current_user(client):
    headers = _login(client)
    task = client.post(
        "/api/todos/tasks",
        json={"title": "Calendar task", "deadline": "2026-08-04T10:00:00"},
        headers=headers,
    )
    assert task.status_code == 200

    events = client.get(
        "/api/calendar/events?start=2026-08-04&end=2026-08-04", headers=headers
    )
    assert events.status_code == 200
    assert any(event["title"] == "Calendar task" for event in events.json())

    outside = client.get(
        "/api/calendar/events?start=2026-08-05&end=2026-08-05", headers=headers
    )
    assert outside.status_code == 200
    assert not any(event["title"] == "Calendar task" for event in outside.json())

    overview = client.get("/api/stats/overview", headers=headers)
    assert overview.status_code == 200


def test_calendar_exposes_recurring_occurrence_identity_and_action(client):
    headers = _login(client)
    task = client.post(
        "/api/todos/tasks",
        json={
            "title": "Recurring calendar task",
            "deadline": "2026-08-31T10:00:00+08:00",
            "schedule": {
                "rule_type": "daily",
                "starts_on": "2026-08-31",
                "ends_on": "2026-09-02",
            },
        },
        headers=headers,
    )
    assert task.status_code == 200, task.text

    events = client.get(
        "/api/calendar/events?start=2026-08-31&end=2026-09-02",
        headers=headers,
    )
    assert events.status_code == 200
    recurring_events = [
        event for event in events.json() if event["title"] == "Recurring calendar task"
    ]
    assert [event["occurrence_date"] for event in recurring_events] == [
        "2026-08-31",
        "2026-09-01",
        "2026-09-02",
    ]
    assert all(event["action"] == "open" for event in recurring_events)
    assert all(event["target_id"] == task.json()["id"] for event in recurring_events)

    detail = client.get("/api/calendar/day/2026-09-01", headers=headers)
    assert detail.status_code == 200
    recurring_detail = next(
        item for item in detail.json()["tasks"] if item["title"] == "Recurring calendar task"
    )
    assert recurring_detail["occurrence_date"] == "2026-09-01"
    assert recurring_detail["action"] == "open"
    assert recurring_detail["target_id"] == task.json()["id"]
