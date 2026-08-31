from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from uuid import UUID

import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")


APP_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _register_and_login(client, username, email):
    response = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "pass123456"},
    )
    assert response.status_code == 200, response.text
    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": "pass123456"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _local_utc_naive(year, month, day, hour=12, minute=0):
    value = datetime(year, month, day, hour, minute, tzinfo=APP_TIMEZONE)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _create_task(client, headers, title, **payload):
    response = client.post(
        "/api/todos/tasks",
        json={"title": title, **payload},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _set_task_state(*, completed_id=None, outside_id=None, db_session):
    from app.models.todo import Task, TaskStatus

    tasks = {task.id: task for task in db_session.query(Task).all()}
    for task_id, task in tasks.items():
        task.created_at = _local_utc_naive(2026, 8, 24)
        if task_id == completed_id:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = _local_utc_naive(2026, 8, 24, 0, 10)
            task.updated_at = task.completed_at
        elif task_id == outside_id:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = _local_utc_naive(2026, 8, 31, 0, 10)
            task.updated_at = task.completed_at
    db_session.commit()


def test_weekly_review_uses_china_boundaries_and_isolates_users(client, db_session):
    owner = _register_and_login(client, "review-owner", "review-owner@example.com")
    other = _register_and_login(client, "review-other", "review-other@example.com")

    completed = _create_task(client, owner, "本周完成")
    overdue = _create_task(
        client,
        owner,
        "逾期高优先级",
        deadline="2026-08-23T18:00:00+08:00",
        priority="urgent",
    )
    open_task = _create_task(
        client,
        owner,
        "本周待办",
        deadline="2026-08-28T18:00:00+08:00",
        priority="high",
    )
    outside = _create_task(client, owner, "下周完成")
    other_task = _create_task(client, other, "他人的任务")
    project = client.post(
        "/api/projects",
        json={"name": "没有下一动作的项目"},
        headers=owner,
    )
    assert project.status_code == 200, project.text

    from app.models.todo import Task
    db_session.query(Task).filter(Task.id == UUID(overdue["id"])).update(
        {
            Task.created_at: _local_utc_naive(2026, 8, 20),
            Task.deadline: _local_utc_naive(2026, 8, 23, 18),
        }
    )
    db_session.query(Task).filter(Task.id == UUID(open_task["id"])).update(
        {
            Task.created_at: _local_utc_naive(2026, 8, 24),
            Task.deadline: _local_utc_naive(2026, 8, 28, 18),
        }
    )
    db_session.query(Task).filter(Task.id == UUID(other_task["id"])).update(
        {Task.created_at: _local_utc_naive(2026, 8, 24)}
    )
    db_session.commit()
    _set_task_state(
        completed_id=UUID(completed["id"]),
        outside_id=UUID(outside["id"]),
        db_session=db_session,
    )

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=owner,
    )

    assert response.status_code == 200, response.text
    review = response.json()
    assert review["week_start"] == "2026-08-24"
    assert review["week_end"] == "2026-08-30"
    assert review["timezone"] == "Asia/Shanghai"
    assert review["summary"]["completed_count"] == 1
    assert review["summary"]["open_count"] == 2
    assert review["summary"]["overdue_count"] == 2
    assert {item["id"] for item in review["unfinished_high_priority"]} == {
        open_task["id"],
        overdue["id"],
    }
    assert [item["id"] for item in review["projects_without_next_action"]] == [project.json()["id"]]
    assert other_task["id"] not in {
        item["id"] for item in review["unfinished_high_priority"]
    }
    assert outside["id"] not in {
        item["id"] for item in review["unfinished_high_priority"]
    }


def test_weekly_review_includes_occurrences_habit_streaks_and_reward_deltas(client, db_session):
    headers = _register_and_login(client, "review-detail", "review-detail@example.com")
    recurring = _create_task(
        client,
        headers,
        "重复执行任务",
        deadline="2026-08-24T10:00:00+08:00",
        priority="high",
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-24",
            "ends_on": "2026-08-25",
            "timezone": "Asia/Shanghai",
        },
    )
    habit = client.post(
        "/api/todos/habits",
        json={"title": "每日复盘", "frequency": "daily"},
        headers=headers,
    )
    assert habit.status_code == 200, habit.text

    from app.models.coin_transaction import CoinTransaction, CoinType
    from app.models.cultivation import CultivationLog
    from app.models.task_schedule import TaskOccurrence
    from app.models.todo import Habit

    occurrence_completed = TaskOccurrence(
        task_id=UUID(recurring["id"]),
        occurrence_date=date(2026, 8, 24),
        status="completed",
        completed_at=_local_utc_naive(2026, 8, 24, 16),
        source_key=f"task:{recurring['id']}:2026-08-24",
    )
    occurrence_open = TaskOccurrence(
        task_id=UUID(recurring["id"]),
        occurrence_date=date(2026, 8, 25),
        status="pending",
        source_key=f"task:{recurring['id']}:2026-08-25",
    )
    db_session.add_all([occurrence_completed, occurrence_open])
    habit_row = db_session.query(Habit).filter(Habit.id == UUID(habit.json()["id"])).one()
    habit_row.created_at = _local_utc_naive(2026, 8, 1)
    habit_row.last_completed_at = _local_utc_naive(2026, 8, 26, 9)
    habit_row.streak = 4
    db_session.add_all(
        [
            CoinTransaction(
                user_id=habit_row.user_id,
                amount=12,
                type=CoinType.EARN.value,
                source="task",
                source_id="review-earn",
                description="本周奖励",
                created_at=_local_utc_naive(2026, 8, 26),
            ),
            CoinTransaction(
                user_id=habit_row.user_id,
                amount=3,
                type=CoinType.SPEND.value,
                source="shop",
                source_id="review-spend",
                description="本周消费",
                created_at=_local_utc_naive(2026, 8, 27),
            ),
            CultivationLog(
                user_id=habit_row.user_id,
                source="task",
                source_key="review-cultivation",
                cultivation_delta=17,
                spirit_stones_delta=10,
                created_at=_local_utc_naive(2026, 8, 27),
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    review = response.json()
    assert review["summary"]["completed_count"] == 2
    assert review["summary"]["open_count"] == 1
    assert review["summary"]["overdue_count"] == 1
    assert review["summary"]["habit_due_count"] == 7
    assert review["summary"]["habit_completed_count"] == 1
    assert review["habit_streak_changes"] == [
        {
            "id": habit.json()["id"],
            "title": "每日复盘",
            "due_count": 7,
            "completed_count": 1,
            "streak_before": 3,
            "streak_after": 4,
            "delta": 1,
        }
    ]
    assert review["rewards"] == {
        "coins_earned": 12,
        "coins_spent": 3,
        "coins_delta": 9,
        "experience": 17,
        "cultivation": 17,
        "spirit_stones": 10,
    }

    assert review["unfinished_high_priority"][0]["url"] == (
        f"/todos?tab=tasks&task_id={recurring['id']}&occurrence_date=2026-08-25"
    )


def test_empty_week_has_three_stable_suggestions_and_requires_monday(client):
    headers = _register_and_login(client, "review-empty", "review-empty@example.com")

    first = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=headers,
    )
    second = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=headers,
    )
    invalid = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-25"},
        headers=headers,
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert invalid.status_code == 422, invalid.text
    review = first.json()
    assert review["summary"] == {
        "completed_count": 0,
        "open_count": 0,
        "overdue_count": 0,
        "habit_due_count": 0,
        "habit_completed_count": 0,
    }
    assert len(review["suggestions"]) == 3
    assert review["suggestions"] == second.json()["suggestions"]
    assert all(item["title"] and item["reason"] and item["url"] for item in review["suggestions"])


def test_weekly_review_reads_unseen_recurring_occurrences_without_persisting_them(client, db_session):
    headers = _register_and_login(client, "review-materialize", "review-materialize@example.com")
    recurring = _create_task(
        client,
        headers,
        "尚未打开过的重复任务",
        deadline="2026-08-24T10:00:00+08:00",
        priority="high",
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-24",
            "ends_on": "2026-08-25",
            "timezone": "Asia/Shanghai",
        },
    )

    from app.models.todo import Task

    db_session.query(Task).filter(Task.id == UUID(recurring["id"])).update(
        {Task.created_at: _local_utc_naive(2026, 8, 20)}
    )
    db_session.commit()

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    review = response.json()
    assert review["summary"]["open_count"] == 2
    assert [item["occurrence_date"] for item in review["unfinished_high_priority"]] == [
        "2026-08-24",
        "2026-08-25",
    ]
    from app.models.task_schedule import TaskOccurrence

    assert db_session.query(TaskOccurrence).count() == 0


def test_weekly_review_excludes_cancelled_parent_occurrences(client, db_session):
    headers = _register_and_login(client, "review-cancelled", "review-cancelled@example.com")
    recurring = _create_task(
        client,
        headers,
        "已取消的重复任务",
        priority="urgent",
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-24",
            "ends_on": "2026-08-24",
        },
    )

    from app.models.todo import Task, TaskStatus

    db_session.query(Task).filter(Task.id == UUID(recurring["id"])).update(
        {Task.status: TaskStatus.CANCELLED.value}
    )
    db_session.commit()

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    review = response.json()
    assert review["summary"]["open_count"] == 0
    assert review["summary"]["overdue_count"] == 0
    assert review["unfinished_high_priority"] == []


def test_weekly_review_does_not_mark_a_future_week_overdue(client):
    headers = _register_and_login(client, "review-future", "review-future@example.com")
    _create_task(
        client,
        headers,
        "未来的重复任务",
        deadline="2099-01-05T10:00:00+08:00",
        priority="high",
        schedule={
            "rule_type": "daily",
            "starts_on": "2099-01-05",
            "ends_on": "2099-01-05",
        },
    )

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2099-01-05"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["summary"]["overdue_count"] == 0


def test_weekly_review_counts_recurring_completion_only_inside_selected_week(client, db_session):
    headers = _register_and_login(client, "review-completion-time", "review-completion-time@example.com")
    recurring = _create_task(
        client,
        headers,
        "补完成的重复任务",
        schedule={
            "rule_type": "daily",
            "starts_on": "2026-08-24",
            "ends_on": "2026-08-24",
        },
    )

    from app.models.task_schedule import TaskOccurrence

    db_session.add(TaskOccurrence(
        task_id=UUID(recurring["id"]),
        occurrence_date=date(2026, 8, 24),
        status="completed",
        completed_at=_local_utc_naive(2026, 8, 31, 12),
        source_key=f"task:{recurring['id']}:2026-08-24",
    ))
    db_session.commit()

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["summary"]["completed_count"] == 0


def test_weekly_review_uses_habit_creation_day_for_weekly_and_monthly_rules(client, db_session):
    headers = _register_and_login(client, "review-habit-rules", "review-habit-rules@example.com")
    weekly = client.post(
        "/api/todos/habits",
        json={"title": "周四习惯", "frequency": "weekly"},
        headers=headers,
    )
    monthly = client.post(
        "/api/todos/habits",
        json={"title": "每月十五日习惯", "frequency": "monthly"},
        headers=headers,
    )
    assert weekly.status_code == 200, weekly.text
    assert monthly.status_code == 200, monthly.text

    from app.models.todo import Habit

    db_session.query(Habit).filter(Habit.id == UUID(weekly.json()["id"])).update(
        {Habit.created_at: _local_utc_naive(2026, 8, 13)}
    )
    db_session.query(Habit).filter(Habit.id == UUID(monthly.json()["id"])).update(
        {Habit.created_at: _local_utc_naive(2026, 8, 15)}
    )
    db_session.commit()

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-10"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    changes = {item["title"]: item for item in response.json()["habit_streak_changes"]}
    assert changes["周四习惯"]["due_count"] == 1
    assert changes["每月十五日习惯"]["due_count"] == 1
    assert response.json()["summary"]["habit_due_count"] == 2


def test_weekly_review_counts_each_habit_completion_date(client, db_session):
    headers = _register_and_login(client, "review-habit-history", "review-habit-history@example.com")
    habit = client.post(
        "/api/todos/habits",
        json={"title": "连续完成习惯", "frequency": "daily"},
        headers=headers,
    )
    assert habit.status_code == 200, habit.text

    from app.models.habit_completion import HabitCompletion
    from app.models.todo import Habit

    habit_row = db_session.query(Habit).filter(Habit.id == UUID(habit.json()["id"])).one()
    habit_row.created_at = _local_utc_naive(2026, 8, 1)
    habit_row.streak = 4
    habit_row.last_completed_at = _local_utc_naive(2026, 8, 26, 9)
    db_session.add_all([
        HabitCompletion(
            habit_id=habit_row.id,
            completed_date=date(2026, 8, 24),
            completed_at=_local_utc_naive(2026, 8, 24, 9),
        ),
        HabitCompletion(
            habit_id=habit_row.id,
            completed_date=date(2026, 8, 25),
            completed_at=_local_utc_naive(2026, 8, 25, 9),
        ),
        HabitCompletion(
            habit_id=habit_row.id,
            completed_date=date(2026, 8, 26),
            completed_at=_local_utc_naive(2026, 8, 26, 9),
        ),
    ])
    db_session.commit()

    response = client.get(
        "/api/review/weekly",
        params={"week_start": "2026-08-24"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    review = response.json()
    assert review["summary"]["habit_completed_count"] == 3
    assert review["habit_streak_changes"][0]["completed_count"] == 3
    assert review["habit_streak_changes"][0]["streak_before"] == 1


def test_habit_completion_writes_a_daily_history_row(client, db_session):
    headers = _register_and_login(client, "review-habit-write", "review-habit-write@example.com")
    habit = client.post(
        "/api/todos/habits",
        json={"title": "记录完成日期", "frequency": "daily"},
        headers=headers,
    )
    assert habit.status_code == 200, habit.text

    completion = client.post(
        f"/api/todos/habits/{habit.json()['id']}/complete",
        headers=headers,
    )

    assert completion.status_code == 200, completion.text
    from app.models.habit_completion import HabitCompletion

    rows = db_session.query(HabitCompletion).all()
    assert len(rows) == 1
    assert str(rows[0].habit_id) == habit.json()["id"]
