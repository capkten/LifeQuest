from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.todo import Habit
from app.models.habit_completion import HabitCompletion
from app.models.habit_leave import HabitLeaveInterval
from app.models.habit_pause import HabitPauseInterval
from app.services.calendar import CalendarService
from app.schemas.todo import HabitBackfillCreate, HabitCreate, HabitUpdate
from app.services.todo import TodoService
from app.services.calendar import CalendarService
from app.services.habit_schedule import (
    is_due,
    month_has_active_schedule,
    month_period,
    week_has_active_schedule,
    week_start,
)
from tests.test_daily_workbench import clock, make_user, headers


def test_weekly_target_list_and_history_use_target_slots(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="力量训练",
        frequency="weekly_target",
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.flush()
    for completed_on in (date(2026, 9, 1), date(2026, 9, 3), date(2026, 9, 5), date(2026, 9, 8)):
        db_session.add(HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        ))
    db_session.commit()

    service = TodoService(db_session)
    current = service._set_completed_today(habit)
    history = service.get_habit_history(
        habit.id,
        user.id,
        start_on=date(2026, 9, 3),
        end_on=date(2026, 9, 12),
    )

    assert current.scheduled_count == 6
    assert current.completed_count == 4
    assert current.completion_rate == round(4 / 6 * 100, 1)
    assert history["scheduled_count"] == 6
    assert history["completed_count"] == 4
    assert history["completion_rate"] == round(4 / 6 * 100, 1)


def test_last_completed_at_without_a_completion_record_does_not_create_history(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="无法证明的旧完成",
        last_completed_at=datetime(2026, 9, 11, 16),
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.commit()
    service = TodoService(db_session)

    current = service._set_completed_today(habit)
    history = service.get_habit_history(
        habit.id,
        user.id,
        start_on=date(2026, 9, 11),
        end_on=date(2026, 9, 11),
    )

    assert current.total_completed == 0
    assert current.completed_today is False
    assert history["days"][0]["completed"] is False


def test_weekly_target_backfill_cannot_exceed_target(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="补记上限",
        frequency="weekly_target",
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.flush()
    for completed_on in (date(2026, 9, 8), date(2026, 9, 9), date(2026, 9, 10)):
        db_session.add(HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        ))
    db_session.commit()
    service = TodoService(db_session)

    with pytest.raises(HTTPException) as error:
        service.backfill_habit(
            habit,
            user.id,
            HabitBackfillCreate(completed_on=date(2026, 9, 11), note="不应写入"),
        )

    assert error.value.status_code == 409
    assert db_session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 3


def test_weekly_target_backfill_counts_later_completed_days_in_current_week(
    client, db_session, clock,
):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="补记不能挤占已完成容量",
        frequency="weekly_target",
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.flush()
    db_session.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        )
        for completed_on in (
            date(2026, 9, 8),
            date(2026, 9, 9),
            date(2026, 9, 11),
        )
    ])
    db_session.commit()
    clock(datetime(2026, 9, 12, 2, tzinfo=timezone.utc))

    with pytest.raises(HTTPException) as error:
        TodoService(db_session).backfill_habit(
            habit,
            user.id,
            HabitBackfillCreate(completed_on=date(2026, 9, 10)),
        )

    assert error.value.status_code == 409
    assert db_session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 3


def test_habit_metrics_ignore_invalid_completion_facts(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="只统计有效计划日",
        frequency="weekdays",
        weekdays=[0],
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.flush()
    db_session.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        )
        for completed_on in (
            date(2026, 8, 31),  # before the habit was created
            date(2026, 9, 7),   # valid Monday
            date(2026, 9, 12),  # not a planned day
            date(2026, 9, 14),  # future relative to today
        )
    ])
    db_session.commit()

    service = TodoService(db_session)
    current = service._set_completed_today(habit)
    service._recalculate_habit_streak(habit, [], [])

    assert current.total_completed == 1
    assert current.scheduled_count == 1
    assert current.completed_count == 1
    assert current.completed_today is False
    assert habit.streak == 1


def test_schedule_activity_respects_habit_creation_date():
    weekly_target = Habit(
        title="新建周目标",
        user_id=UUID(int=1),
        frequency="weekly_target",
        weekly_target=3,
        created_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
    )
    monthly = Habit(
        title="新建月计划",
        user_id=UUID(int=1),
        frequency="monthly",
        created_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
    )

    assert week_has_active_schedule(weekly_target, week_start(date(2026, 8, 31))) is False
    assert week_has_active_schedule(weekly_target, week_start(date(2026, 9, 7))) is True
    assert month_has_active_schedule(monthly, month_period(date(2026, 9, 1))) is False
    assert month_has_active_schedule(monthly, month_period(date(2026, 10, 1))) is True


@pytest.mark.parametrize("days", [[], [0, 0], [-1], [7], [True], ["1"], None])
def test_invalid_weekdays(days):
    with pytest.raises(ValidationError):
        HabitCreate(title="阅读", frequency="weekdays", weekdays=days)


def test_non_string_completion_note_returns_validation_error(client, db_session, clock):
    user = make_user(db_session)
    auth = headers(user)
    habit = client.post("/api/todos/habits", headers=auth, json={"title": "训练"}).json()

    response = client.post(
        f"/api/todos/habits/{habit['id']}/complete",
        headers=auth,
        json={"note": 123},
    )

    assert response.status_code == 422


def test_non_string_leave_reason_returns_validation_error(client, db_session, clock):
    user = make_user(db_session)
    auth = headers(user)
    habit = client.post("/api/todos/habits", headers=auth, json={"title": "训练"}).json()

    response = client.post(
        f"/api/todos/habits/{habit['id']}/leave",
        headers=auth,
        json={"leave_on": "2026-09-12", "return_on": "2026-09-13", "reason": 123},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("empty_note", [None, ""])
def test_repeated_completion_does_not_clear_existing_note(client, db_session, clock, empty_note):
    user = make_user(db_session)
    auth = headers(user)
    habit = client.post("/api/todos/habits", headers=auth, json={"title": "训练"}).json()
    path = f"/api/todos/habits/{habit['id']}/complete"

    assert client.post(path, headers=auth, json={"note": "保留这条备注"}).status_code == 200
    response = client.post(path, headers=auth, json={"note": empty_note})

    assert response.status_code == 200
    record = db_session.query(HabitCompletion).one()
    assert record.note == "保留这条备注"


def test_legacy_schedule_migration_is_repeatable(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text
    from app import main as main_module
    from app.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy-habits.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE habits DROP COLUMN weekdays"))
            connection.execute(text("ALTER TABLE habits DROP COLUMN weekly_target"))
            habit_columns = {column[1] for column in connection.execute(text("PRAGMA table_info(habits)"))}
            if "streak_reset_on" in habit_columns:
                connection.execute(text("ALTER TABLE habits DROP COLUMN streak_reset_on"))
            connection.execute(text("INSERT INTO habits (id, user_id, title, frequency) VALUES ('habit', 'user', '旧习惯', 'weekly')"))
        monkeypatch.setattr(main_module, "engine", engine)
        main_module._migrate_columns()
        main_module._migrate_columns()
        assert "weekdays" in {column["name"] for column in inspect(engine).get_columns("habits")}
        assert "streak_reset_on" in {column["name"] for column in inspect(engine).get_columns("habits")}
        with engine.connect() as connection:
            assert connection.execute(text("SELECT title, frequency, weekdays FROM habits")).one() == ("旧习惯", "weekly", None)
    finally:
        engine.dispose()


def test_legacy_completion_migration_merges_duplicate_metadata_and_adds_unique_guard(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text
    from app import main as main_module
    from app.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'duplicate-completions.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE habit_completions"))
            connection.execute(text(
                "CREATE TABLE habit_completions ("
                "id VARCHAR(36) PRIMARY KEY, habit_id VARCHAR(36) NOT NULL, "
                "user_id VARCHAR(36) NOT NULL, completed_on DATE NOT NULL, "
                "completed_at DATETIME NOT NULL, note VARCHAR(500), "
                "is_makeup BOOLEAN NOT NULL DEFAULT 0, created_at DATETIME)"
            ))
            connection.execute(text(
                "INSERT INTO habit_completions "
                "(id, habit_id, user_id, completed_on, completed_at, note, is_makeup) VALUES "
                "('completion-old', 'habit', 'user', '2026-09-12', '2026-09-12 02:00:00', '保留的历史备注', 1), "
                "('completion-new', 'habit', 'user', '2026-09-12', '2026-09-12 12:00:00', NULL, 0)"
            ))
        monkeypatch.setattr(main_module, "engine", engine)
        main_module._migrate_columns()
        main_module._migrate_columns()

        indexes = [index for index in inspect(engine).get_indexes("habit_completions")
                   if index["unique"] and index["column_names"] == ["habit_id", "completed_on"]]
        with engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT id, note, is_makeup FROM habit_completions ORDER BY id"
            )).fetchall()

        assert rows == [("completion-new", "保留的历史备注", 1)]
        assert len(indexes) == 1
    finally:
        engine.dispose()


def test_legacy_completion_migration_adds_missing_timestamp_before_deduplication(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, inspect, text
    from app import main as main_module
    from app.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'old-completions.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE habit_completions"))
            connection.execute(text(
                "CREATE TABLE habit_completions ("
                "id VARCHAR(36) PRIMARY KEY, habit_id VARCHAR(36) NOT NULL, "
                "user_id VARCHAR(36) NOT NULL, completed_on DATE NOT NULL, "
                "created_at DATETIME)"
            ))
            connection.execute(text(
                "INSERT INTO habit_completions "
                "(id, habit_id, user_id, completed_on, created_at) VALUES "
                "('completion-old', 'habit', 'user', '2026-09-12', '2026-09-12 02:00:00'), "
                "('completion-new', 'habit', 'user', '2026-09-12', '2026-09-12 12:00:00')"
            ))
        monkeypatch.setattr(main_module, "engine", engine)

        main_module._migrate_columns()
        main_module._migrate_columns()

        columns = {column["name"] for column in inspect(engine).get_columns("habit_completions")}
        with engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT id, completed_at, note, is_makeup FROM habit_completions"
            )).fetchall()

        assert {"completed_at", "note", "is_makeup"}.issubset(columns)
        assert rows == [("completion-new", "2026-09-12 12:00:00", None, 0)]
    finally:
        engine.dispose()


def test_legacy_completion_migration_backfills_existing_null_timestamps_before_deduplication(
    tmp_path, monkeypatch,
):
    from sqlalchemy import create_engine, inspect, text
    from app import main as main_module
    from app.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 'nullable-completions.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE habit_completions"))
            connection.execute(text(
                "CREATE TABLE habit_completions ("
                "id VARCHAR(36) PRIMARY KEY, habit_id VARCHAR(36) NOT NULL, "
                "user_id VARCHAR(36) NOT NULL, completed_on DATE NOT NULL, "
                "completed_at DATETIME, note VARCHAR(500), "
                "is_makeup BOOLEAN NOT NULL DEFAULT 0, created_at DATETIME)"
            ))
            connection.execute(text(
                "INSERT INTO habit_completions "
                "(id, habit_id, user_id, completed_on, completed_at, note, created_at) VALUES "
                "('completion-old', 'habit', 'user', '2026-09-12', "
                "'2026-09-12 02:00:00', NULL, '2026-09-12 02:00:00'), "
                "('completion-null', 'habit', 'user', '2026-09-12', NULL, "
                "'回填后的最新备注', '2026-09-12 12:00:00')"
            ))
        monkeypatch.setattr(main_module, "engine", engine)

        main_module._migrate_columns()
        main_module._migrate_columns()

        columns = {column["name"] for column in inspect(engine).get_columns("habit_completions")}
        with engine.connect() as connection:
            rows = connection.execute(text(
                "SELECT id, completed_at, note FROM habit_completions"
            )).fetchall()

        assert "completed_at" in columns
        assert rows == [("completion-null", "2026-09-12 12:00:00", "回填后的最新备注")]
    finally:
        engine.dispose()


def test_changing_habit_schedule_resets_streak_history_boundary(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="周末训练",
        frequency="daily",
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.commit()
    service = TodoService(db_session)

    clock(datetime(2026, 9, 12, 2, tzinfo=timezone.utc))
    service.complete_habit(habit, user.id)
    changed = service.update_habit(
        habit,
        HabitUpdate(frequency="weekdays", weekdays=[0, 5]),
    )

    assert changed.streak == 0
    assert changed.streak_reset_on == date(2026, 9, 12)

    clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    completed = service.complete_habit(changed, user.id)

    assert completed.streak == 1


def test_schedule_change_allows_same_day_completion_when_no_prior_completion(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="当天改计划后完成",
        frequency="daily",
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.commit()
    service = TodoService(db_session)

    clock(datetime(2026, 9, 12, 2, tzinfo=timezone.utc))
    changed = service.update_habit(
        habit,
        HabitUpdate(frequency="weekdays", weekdays=[5]),
    )

    assert changed.streak == 0
    assert changed.streak_reset_on == date(2026, 9, 11)

    completed = service.complete_habit(changed, user.id)

    assert completed.streak == 1
    assert completed.best_streak == 1


def test_daily_streak_can_cross_a_pause_longer_than_a_year(client, db_session):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="长期暂停后的习惯",
        frequency="daily",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.flush()
    db_session.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=date(2025, 1, 1),
            completed_at=datetime(2025, 1, 1, 2),
        ),
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=date(2026, 2, 1),
            completed_at=datetime(2026, 2, 1, 2),
        ),
    ])
    pause = HabitPauseInterval(
        habit_id=habit.id,
        user_id=user.id,
        paused_on=date(2025, 1, 2),
        resumed_on=date(2026, 2, 1),
    )
    db_session.add(pause)
    db_session.commit()

    TodoService(db_session)._recalculate_habit_streak(habit, [pause], [])

    assert habit.streak == 2


def test_schedule_round_trip_and_partial_updates(client, db_session, clock):
    user = make_user(db_session)
    auth = headers(user)
    response = client.post("/api/todos/habits", headers=auth, json={
        "title": "阅读", "frequency": "weekdays", "weekdays": [5, 0],
    })
    assert response.status_code == 200
    habit = response.json()
    assert habit["weekdays"] == [0, 5]
    assert habit["scheduled_today"] is True
    path = f'/api/todos/habits/{habit["id"]}'
    assert client.put(path, headers=auth, json={"title": "跑步"}).json()["weekdays"] == [0, 5]
    assert client.put(path, headers=auth, json={"weekdays": None}).status_code == 422
    assert client.put(path, headers=auth, json={"frequency": None}).status_code == 422
    changed = client.put(path, headers=auth, json={"frequency": "daily"})
    assert changed.json()["weekdays"] is None
    assert client.put(path, headers=auth, json={"frequency": "weekdays"}).status_code == 422
    other = make_user(db_session)
    assert client.put(path, headers=headers(other), json={"title": "越权"}).status_code == 403
    assert client.post(path + "/complete", headers=headers(other)).status_code == 403


def test_schedule_calendar_and_summary_agree(client, db_session, clock):
    user = make_user(db_session)
    service = TodoService(db_session)
    habit = service.create_habit(user.id, HabitCreate(title="跑步", frequency="weekdays", weekdays=[0, 5]))
    habit.created_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    db_session.commit()
    assert is_due(habit, date(2026, 9, 12))
    assert not is_due(habit, date(2026, 9, 13))
    for offset in range(7):
        target = date(2026, 9, 7 + offset)
        assert CalendarService._is_habit_due_on_date(habit, target) == is_due(habit, target)
    assert str(habit.id) in str(service.get_daily_summary(user.id))
    clock(datetime(2026, 9, 12, 16, tzinfo=timezone.utc))
    assert str(habit.id) not in str(service.get_daily_summary(user.id))
    with pytest.raises(HTTPException) as error:
        service.complete_habit(habit, user.id)
    assert error.value.status_code == 409
    assert db_session.query(HabitCompletion).count() == 0


def test_calendar_excludes_habits_before_their_creation_date(client, db_session):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="未来才开始的习惯",
        frequency="daily",
        created_at=datetime(2026, 9, 12, 16, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.commit()
    calendar = CalendarService(db_session)

    before_events = calendar.get_events(user.id, date(2026, 9, 12), date(2026, 9, 12))
    after_events = calendar.get_events(user.id, date(2026, 9, 13), date(2026, 9, 13))

    assert [event for event in before_events if event["type"] == "habit"] == []
    assert len([event for event in after_events if event["type"] == "habit"]) == 1
    assert calendar.get_day_detail(user.id, date(2026, 9, 12))["habits"] == []
    assert len(calendar.get_day_detail(user.id, date(2026, 9, 13))["habits"]) == 1


def test_rest_days_do_not_break_streak_and_no_duplicate_rewards(client, db_session, clock):
    user = make_user(db_session)
    service = TodoService(db_session)
    habit = service.create_habit(user.id, HabitCreate(title="跑步", frequency="weekdays", weekdays=[0, 5]))
    service.complete_habit(habit, user.id)
    assert habit.streak == 1
    clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    service.complete_habit(habit, user.id)
    assert habit.streak == 2
    db_session.refresh(user)
    coins = user.coins
    service.complete_habit(habit, user.id)
    db_session.refresh(user)
    assert user.coins == coins
    assert db_session.query(HabitCompletion).count() == 2
    clock(datetime(2026, 9, 21, 2, tzinfo=timezone.utc))
    service.complete_habit(habit, user.id)
    assert habit.streak == 1


def test_schedule_change_resets_current_streak_not_history(client, db_session, clock):
    user = make_user(db_session)
    service = TodoService(db_session)
    habit = service.create_habit(user.id, HabitCreate(title="跑步", frequency="weekdays", weekdays=[5]))
    service.complete_habit(habit, user.id)
    service.update_habit(habit, HabitUpdate(weekdays=[0, 5]))
    assert habit.streak == 0
    assert habit.best_streak == 1
    assert db_session.query(HabitCompletion).count() == 1
    service.update_habit(habit, HabitUpdate(is_active=False))
    with pytest.raises(HTTPException):
        service.complete_habit(habit, user.id)


@pytest.mark.parametrize("frequency,completed_at", [
    ("weekly", datetime(2026, 9, 8, 2, tzinfo=timezone.utc)),
    ("monthly", datetime(2026, 9, 2, 2, tzinfo=timezone.utc)),
])
def test_off_plan_normal_completion_is_rejected_without_reward_or_streak_change(
    client, db_session, clock, frequency, completed_at,
):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="非计划日",
        frequency=frequency,
        streak=4,
        best_streak=5,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.commit()
    service = TodoService(db_session)
    before_coins = user.coins
    before_experience = user.experience
    clock(completed_at)

    with pytest.raises(HTTPException) as error:
        service.complete_habit(habit, user.id)

    assert error.value.status_code == 409
    db_session.refresh(user)
    db_session.refresh(habit)
    assert db_session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 0
    assert user.coins == before_coins
    assert user.experience == before_experience
    assert habit.streak == 4
    assert habit.best_streak == 5


def test_weekly_target_counts_days_caps_rewards_and_advances_weekly_streak(client, db_session, clock):
    user = make_user(db_session)
    service = TodoService(db_session)
    habit = service.create_habit(user.id, HabitCreate(
        title="力量训练", frequency="weekly_target", weekly_target=3,
    ))
    habit.created_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    db_session.commit()

    for day in (9, 10, 11):
        clock(datetime(2026, 9, day, 2, tzinfo=timezone.utc))
        habit = service.complete_habit(habit, user.id)
    assert habit.weekly_completed == 3
    assert habit.weekly_remaining == 0
    assert habit.streak == 1
    summary_habit = next(item for item in service.get_daily_summary(user.id)["habits"] if item["id"] == habit.id)
    assert summary_habit["weekly_completed"] == 3
    assert summary_habit["weekly_remaining"] == 0
    assert db_session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 3
    db_session.refresh(user)
    coins_after_goal = user.coins

    clock(datetime(2026, 9, 12, 2, tzinfo=timezone.utc))
    with pytest.raises(HTTPException) as blocked:
        service.complete_habit(habit, user.id)
    assert blocked.value.status_code == 409
    assert db_session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 3

    clock(datetime(2026, 9, 11, 10, tzinfo=timezone.utc))
    same_day = service.complete_habit(habit, user.id)
    db_session.refresh(user)
    assert same_day.weekly_completed == 3
    assert user.coins == coins_after_goal

    for day in (14, 15, 16):
        clock(datetime(2026, 9, day, 2, tzinfo=timezone.utc))
        habit = service.complete_habit(habit, user.id)
    assert habit.weekly_completed == 3
    assert habit.streak == 2
    assert db_session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 6


@pytest.mark.parametrize("excluded_kind", ["pause", "leave"])
def test_weekly_target_capacity_ignores_excluded_and_future_records(
    client, db_session, clock, excluded_kind,
):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="清理异常记录",
        frequency="weekly_target",
        weekly_target=3,
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.flush()
    db_session.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        )
        for completed_on in (
            date(2026, 9, 8),  # excluded by the interval below
            date(2026, 9, 9),
            date(2026, 9, 10),
            date(2026, 9, 13),  # future relative to the action date
        )
    ])
    if excluded_kind == "pause":
        db_session.add(HabitPauseInterval(
            habit_id=habit.id,
            user_id=user.id,
            paused_on=date(2026, 9, 8),
            resumed_on=date(2026, 9, 9),
        ))
    else:
        db_session.add(HabitLeaveInterval(
            habit_id=habit.id,
            user_id=user.id,
            leave_on=date(2026, 9, 8),
            return_on=date(2026, 9, 9),
        ))
    db_session.commit()
    clock(datetime(2026, 9, 12, 2, tzinfo=timezone.utc))
    service = TodoService(db_session)

    assert service._weekly_completion_count(habit.id, date(2026, 9, 12)) == 2

    completed = service.complete_habit(habit, user.id)

    assert completed.weekly_completed == 3
    assert completed.weekly_remaining == 0
    assert db_session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 5


@pytest.mark.parametrize("payload", [
    {"title": "训练", "frequency": "weekly_target"},
    {"title": "训练", "frequency": "weekly_target", "weekly_target": 0},
    {"title": "训练", "frequency": "weekly_target", "weekly_target": 8},
    {"title": "训练", "frequency": "daily", "weekly_target": 3},
])
def test_weekly_target_validation_is_explicit(client, db_session, payload):
    user = make_user(db_session)
    response = client.post("/api/todos/habits", headers=headers(user), json=payload)
    assert response.status_code == 422


def test_weekly_target_partial_update_and_cross_user_completion_are_protected(client, db_session, clock):
    user, other = make_user(db_session), make_user(db_session)
    auth = headers(user)
    response = client.post("/api/todos/habits", headers=auth, json={
        "title": "训练", "frequency": "weekly_target", "weekly_target": 3,
    })
    habit = response.json()
    path = f'/api/todos/habits/{habit["id"]}'
    updated = client.put(path, headers=auth, json={"title": "训练新版"})
    assert updated.status_code == 200
    assert updated.json()["weekly_target"] == 3
    assert client.put(path, headers=auth, json={"weekly_target": 0}).status_code == 422
    assert client.put(path, headers=auth, json={"frequency": "daily"}).json()["weekly_target"] is None
    assert client.put(path, headers=auth, json={"weekly_target": 3}).status_code == 422
    assert client.put(path, headers=headers(other), json={"weekly_target": 2}).status_code == 403
    assert client.post(path + "/complete", headers=headers(other)).status_code == 403


def test_pause_resume_records_exclusive_resume_day_and_is_idempotent(client, db_session, clock):
    user, other = make_user(db_session), make_user(db_session)
    auth = headers(user)
    habit = client.post("/api/todos/habits", headers=auth, json={"title": "阅读"}).json()
    path = f'/api/todos/habits/{habit["id"]}'

    paused = client.post(path + "/pause", headers=auth)
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False
    assert paused.json()["paused_today"] is True
    assert paused.json()["pause_intervals"][-1]["paused_on"] == "2026-09-12"
    assert paused.json()["pause_intervals"][-1]["resumed_on"] is None
    assert client.post(path + "/pause", headers=auth).json()["pause_intervals"] == paused.json()["pause_intervals"]
    assert client.post(path + "/complete", headers=auth).status_code == 409

    assert client.get(path + "/pause-intervals", headers=auth).json() == paused.json()["pause_intervals"]
    assert client.post(path + "/pause", headers=headers(other)).status_code == 403
    resumed = client.post(path + "/resume", headers=auth)
    assert resumed.status_code == 200
    interval = resumed.json()["pause_intervals"][-1]
    assert resumed.json()["is_active"] is True
    assert resumed.json()["paused_today"] is False
    assert interval["resumed_on"] == "2026-09-12"
    assert client.post(path + "/resume", headers=auth).json()["pause_intervals"] == resumed.json()["pause_intervals"]


def test_pause_interval_excludes_plans_and_does_not_break_daily_streak(client, db_session, clock):
    user = make_user(db_session)
    service = TodoService(db_session)
    habit = service.create_habit(user.id, HabitCreate(title="阅读"))
    service.complete_habit(habit, user.id)
    clock(datetime(2026, 9, 13, 2, tzinfo=timezone.utc))
    service.pause_habit(habit, user.id)
    clock(datetime(2026, 9, 15, 2, tzinfo=timezone.utc))
    resumed = service.resume_habit(habit, user.id)
    assert resumed.pause_intervals[-1].paused_on == date(2026, 9, 13)
    assert resumed.pause_intervals[-1].resumed_on == date(2026, 9, 15)
    calendar = CalendarService(db_session)
    assert calendar.get_day_detail(user.id, date(2026, 9, 13))["habits"] == []
    assert calendar.get_day_detail(user.id, date(2026, 9, 14))["habits"] == []
    assert len(calendar.get_day_detail(user.id, date(2026, 9, 15))["habits"]) == 1
    resumed = service.complete_habit(resumed, user.id)
    assert resumed.streak == 2
    assert db_session.query(HabitPauseInterval).filter_by(habit_id=habit.id).count() == 1


def test_pause_interval_does_not_break_weekly_streak(client, db_session, clock):
    user = make_user(db_session)
    service = TodoService(db_session)
    clock(datetime(2026, 9, 7, 2, tzinfo=timezone.utc))
    habit = service.create_habit(user.id, HabitCreate(title="周计划", frequency="weekly"))
    service.complete_habit(habit, user.id)
    assert habit.streak == 1

    clock(datetime(2026, 9, 8, 2, tzinfo=timezone.utc))
    service.pause_habit(habit, user.id)
    clock(datetime(2026, 9, 21, 2, tzinfo=timezone.utc))
    habit = service.resume_habit(habit, user.id)
    habit = service.complete_habit(habit, user.id)

    assert habit.streak == 2


def test_pause_interval_does_not_break_monthly_streak(client, db_session, clock):
    user = make_user(db_session)
    service = TodoService(db_session)
    clock(datetime(2026, 9, 1, 2, tzinfo=timezone.utc))
    habit = service.create_habit(user.id, HabitCreate(title="月计划", frequency="monthly"))
    service.complete_habit(habit, user.id)
    assert habit.streak == 1

    clock(datetime(2026, 9, 2, 2, tzinfo=timezone.utc))
    service.pause_habit(habit, user.id)
    clock(datetime(2026, 11, 1, 2, tzinfo=timezone.utc))
    habit = service.resume_habit(habit, user.id)
    habit = service.complete_habit(habit, user.id)

    assert habit.streak == 2


def test_legacy_inactive_update_is_recorded_and_resume_closes_interval(client, db_session, clock):
    user = make_user(db_session)
    auth = headers(user)
    habit = client.post("/api/todos/habits", headers=auth, json={"title": "阅读"}).json()
    path = f'/api/todos/habits/{habit["id"]}'
    inactive = client.put(path, headers=auth, json={"is_active": False}).json()
    assert inactive["pause_intervals"][-1]["paused_on"] == "2026-09-12"
    active = client.put(path, headers=auth, json={"is_active": True}).json()
    assert active["pause_intervals"][-1]["resumed_on"] == "2026-09-12"
    assert active["is_active"] is True


def test_habit_completion_note_is_persisted_without_duplicate_reward(client, db_session, clock):
    user = make_user(db_session)
    auth = headers(user)
    habit = client.post(
        "/api/todos/habits",
        headers=auth,
        json={"title": "训练", "coins_reward": 7, "exp_reward": 3},
    ).json()
    path = f'/api/todos/habits/{habit["id"]}'
    before = client.get("/api/users/me", headers=auth).json()

    first = client.post(path + "/complete", headers=auth, json={"note": "完成了核心训练"})
    assert first.status_code == 200
    after_first = client.get("/api/users/me", headers=auth).json()
    assert after_first["coins"] == before["coins"] + 7

    repeated = client.post(path + "/complete", headers=auth, json={"note": "补充了训练感受"})
    assert repeated.status_code == 200
    after_repeated = client.get("/api/users/me", headers=auth).json()
    assert after_repeated["coins"] == after_first["coins"]
    repeated_without_note = client.post(path + "/complete", headers=auth)
    assert repeated_without_note.status_code == 200
    assert db_session.query(HabitCompletion).count() == 1
    record = db_session.query(HabitCompletion).one()
    assert record.note == "补充了训练感受"
    history = client.get(path + "/history", headers=auth, params={
        "start_on": "2026-09-12", "end_on": "2026-09-12",
    })
    assert history.status_code == 200
    assert history.json()["days"][0]["note"] == "补充了训练感受"
    assert history.json()["days"][0]["is_makeup"] is False


def test_habit_backfill_is_idempotent_updates_streak_and_has_no_reward(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="阅读",
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.commit()
    service = TodoService(db_session)
    before_coins = user.coins

    backfill = HabitBackfillCreate(completed_on=date(2026, 9, 11), note="昨天读完一章")
    saved = service.backfill_habit(habit, user.id, backfill)
    assert saved.streak == 1
    assert saved.best_streak == 1
    assert saved.last_completed_at is not None
    assert service._local_date(saved.last_completed_at) == date(2026, 9, 11)
    db_session.refresh(user)
    assert user.coins == before_coins

    repeated = service.backfill_habit(
        saved,
        user.id,
        HabitBackfillCreate(completed_on=date(2026, 9, 11), note="更新备注"),
    )
    assert repeated.streak == 1
    assert db_session.query(HabitCompletion).count() == 1
    record = db_session.query(HabitCompletion).filter_by(habit_id=habit.id).one()
    assert record.note == "更新备注"
    assert record.is_makeup is True

    completed_today = service.complete_habit(repeated, user.id)
    assert completed_today.streak == 2
    db_session.refresh(user)
    assert user.coins == before_coins + habit.coins_reward


def test_habit_backfill_rejects_today_old_dates_and_non_plan_days(client, db_session, clock):
    user = make_user(db_session)
    habit = Habit(
        user_id=user.id,
        title="周一训练",
        frequency="weekdays",
        weekdays=[0],
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    db_session.add(habit)
    db_session.commit()
    service = TodoService(db_session)

    with pytest.raises(HTTPException) as today_error:
        service.backfill_habit(habit, user.id, HabitBackfillCreate(completed_on=date(2026, 9, 12)))
    assert today_error.value.status_code == 422
    with pytest.raises(HTTPException) as old_error:
        service.backfill_habit(habit, user.id, HabitBackfillCreate(completed_on=date(2026, 6, 13)))
    assert old_error.value.status_code == 422
    with pytest.raises(HTTPException) as rest_day_error:
        service.backfill_habit(habit, user.id, HabitBackfillCreate(completed_on=date(2026, 9, 11)))
    assert rest_day_error.value.status_code == 409


def test_habit_leave_excludes_schedule_validates_overlap_and_can_be_revoked(client, db_session, clock):
    user, other = make_user(db_session), make_user(db_session)
    auth = headers(user)
    habit = client.post("/api/todos/habits", headers=auth, json={"title": "跑步"}).json()
    db_habit = db_session.query(Habit).filter(Habit.id == UUID(habit["id"])).one()
    db_habit.created_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    db_session.commit()
    path = f'/api/todos/habits/{habit["id"]}'

    leave = client.post(path + "/leave", headers=auth, json={
        "leave_on": "2026-09-12", "return_on": "2026-09-14", "reason": "出差",
    })
    assert leave.status_code == 200
    leave_data = leave.json()
    assert leave_data["excused_today"] is True
    assert leave_data["scheduled_today"] is False
    assert leave_data["leave_intervals"][-1]["reason"] == "出差"
    leave_id = leave_data["leave_intervals"][-1]["id"]
    assert client.post(path + "/complete", headers=auth).status_code == 409
    assert client.post(path + "/leave", headers=auth, json={
        "leave_on": "2026-09-13", "return_on": "2026-09-15",
    }).status_code == 409
    assert client.get(path + "/history", headers=headers(other)).status_code == 403
    assert client.get(path + "/leave-intervals", headers=headers(other)).status_code == 403
    assert client.post(path + "/leave", headers=headers(other), json={
        "leave_on": "2026-09-15", "return_on": "2026-09-16",
    }).status_code == 403

    clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    history = client.get(path + "/history", headers=auth, params={
        "start_on": "2026-09-12", "end_on": "2026-09-14",
    }).json()
    assert history["scheduled_count"] == 1
    assert history["days"][0]["excused"] is True
    assert history["days"][0]["scheduled"] is False
    assert history["days"][2]["scheduled"] is True
    calendar = client.get("/api/calendar/day/2026-09-12", headers=auth)
    assert calendar.status_code == 200
    assert calendar.json()["habits"] == []

    revoked = client.delete(path + f"/leave/{leave_id}", headers=auth)
    assert revoked.status_code == 200
    assert revoked.json()["leave_intervals"] == []
    assert revoked.json()["excused_today"] is False
    assert client.get(path + "/leave-intervals", headers=auth).json() == []
    assert len(client.get("/api/calendar/day/2026-09-12", headers=auth).json()["habits"]) == 1
    assert client.post(path + "/complete", headers=auth).status_code == 200
    assert db_session.query(HabitLeaveInterval).count() == 0
