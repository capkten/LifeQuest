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
