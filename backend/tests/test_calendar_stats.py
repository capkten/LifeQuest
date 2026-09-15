from datetime import date, datetime, timezone
from uuid import uuid4

from app.models.user import User
from app.services.stats import StatsService


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


def test_calendar_keeps_pre_pause_history_and_marks_completed_habits(
    client,
    auth_headers,
    db_session,
    user,
    create_habit_with_pause_interval,
    complete_on,
):
    habit, _ = create_habit_with_pause_interval(
        db_session,
        user.id,
        paused_on=date(2026, 9, 10),
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    complete_on(db_session, habit, date(2026, 9, 9))

    response = client.get(
        "/api/calendar/events",
        params={"start": "2026-09-09", "end": "2026-09-11"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    events = response.json()
    assert next(
        event for event in events
        if event["date"] == "2026-09-09" and event["id"] == str(habit.id)
    )["status"] == "completed"
    assert not any(event["date"] == "2026-09-11" for event in events)


def test_weekly_target_stats_use_target_slots_not_daily_slots(
    database,
    clock,
    create_weekly_target_habit,
):
    user = User(
        username=f"stats-{uuid4().hex}",
        email=f"stats-{uuid4().hex}@example.com",
        password_hash="unused",
    )
    database.add(user)
    database.commit()
    habit = create_weekly_target_habit(
        database,
        user.id,
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    from app.models.habit_completion import HabitCompletion

    database.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        )
        for completed_on in [date(2026, 9, 8), date(2026, 9, 10)]
    ])
    database.commit()

    rows = StatsService(database).get_habit_stats(user.id, "week")

    assert sum(row["total"] for row in rows) == 6
    assert sum(row["completed"] for row in rows) == 2


def test_weekly_target_stats_include_the_current_intersecting_china_week(
    database,
    clock,
    create_weekly_target_habit,
):
    clock(datetime(2026, 9, 15, 8, tzinfo=timezone.utc))
    user = User(
        username=f"intersecting-{uuid4().hex}",
        email=f"intersecting-{uuid4().hex}@example.com",
        password_hash="unused",
    )
    database.add(user)
    database.commit()
    habit = create_weekly_target_habit(
        database,
        user.id,
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    from app.models.habit_completion import HabitCompletion

    database.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        )
        for completed_on in [date(2026, 9, 9), date(2026, 9, 10)]
    ])
    database.commit()

    rows = StatsService(database).get_habit_stats(user.id, "week")

    assert sum(row["total"] for row in rows) == 6
    assert sum(row["completed"] for row in rows) == 2


def test_calendar_day_detail_keeps_historical_inactive_habits(
    client,
    auth_headers,
    db_session,
    user,
    create_habit_with_pause_interval,
    complete_on,
):
    habit, _ = create_habit_with_pause_interval(
        db_session,
        user.id,
        paused_on=date(2026, 9, 10),
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    habit.is_active = False
    db_session.commit()
    complete_on(db_session, habit, date(2026, 9, 9))

    response = client.get(
        "/api/calendar/day/2026-09-09",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert any(item["id"] == str(habit.id) for item in response.json()["habits"])


def test_stats_overview_returns_cumulative_total_experience(database):
    user = User(
        username=f"overview-{uuid4().hex}",
        email=f"overview-{uuid4().hex}@example.com",
        password_hash="unused",
        experience=12,
        total_experience=212,
    )
    database.add(user)
    database.commit()

    overview = StatsService(database).get_overview(user.id)

    assert overview["total_exp"] == 212


def test_goal_update_rejects_progress_outside_percentage_bounds(client, auth_headers, goal):
    for progress in (-1, 101):
        response = client.put(
            f"/api/todos/goals/{goal.id}",
            headers=auth_headers,
            json={"progress": progress},
        )
        assert response.status_code == 422


def test_goal_status_update_settles_reward_once(
    client,
    auth_headers,
    db_session,
    goal,
):
    response = client.put(
        f"/api/todos/goals/{goal.id}",
        headers=auth_headers,
        json={"status": "completed", "progress": 100},
    )
    assert response.status_code == 200

    repeat = client.put(
        f"/api/todos/goals/{goal.id}",
        headers=auth_headers,
        json={"status": "completed", "progress": 100},
    )
    assert repeat.status_code == 200
    from app.models.coin_transaction import CoinTransaction

    assert db_session.query(CoinTransaction).filter_by(
        user_id=goal.user_id,
        source="goal",
    ).count() == 1
