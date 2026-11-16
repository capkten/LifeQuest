from datetime import datetime, timedelta, timezone

import pytest


BASE = "/api/cultivation/retreat"


@pytest.fixture
def retreat_clock(monkeypatch, clock):
    instant = [datetime(2026, 11, 16, 2, tzinfo=timezone.utc)]

    def set_time(value):
        instant[0] = value
        clock(value)

    monkeypatch.setattr("app.services.cultivation_retreat.utc_now", lambda: instant[0])
    monkeypatch.setattr("app.services.encounter_engine.random.random", lambda: 1.0)
    set_time(instant[0])
    return set_time


def start(client, headers, minutes=25, todo_id=None):
    response = client.post(
        f"{BASE}/start",
        headers=headers,
        json={"target_duration": minutes, "todo_id": todo_id},
    )
    assert response.status_code == 200, response.text
    return response.json()


def finish(client, headers, session, **payload):
    return client.post(
        f"{BASE}/{session['id']}/complete", headers=headers, json=payload
    )


def overview(client, headers):
    response = client.get("/api/cultivation/overview", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def create_task(client, headers, **values):
    response = client.post(
        "/api/todos/tasks", headers=headers, json={"title": "专注事项", **values}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("minutes,exp,stones", [(25, 12, 7), (45, 22, 13)])
def test_completing_the_bound_task_converts_half_the_qi_and_keeps_task_rewards_separate(
    client, auth_headers, retreat_clock, minutes, exp, stones
):
    task = create_task(client, auth_headers)
    session = start(client, auth_headers, minutes, task["id"])
    retreat_clock(datetime(2026, 11, 16, 2, tzinfo=timezone.utc) + timedelta(minutes=minutes))
    response = finish(client, auth_headers, session, mark_todo_complete=True)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["qi_gained"], result["exp_gained"], result["coins_gained"]) == (minutes, exp, stones)
    settlement = result["settlement_result"]
    assert settlement["conversion_rate"] == 0.5
    assert settlement["task_completed"] is True
    assert settlement["task_previously_completed"] is False
    assert (settlement["task_reward"]["cultivation"], settlement["task_reward"]["spirit_stones"]) == (15, 9)
    task_state = client.get(f"/api/todos/tasks/{task['id']}", headers=auth_headers).json()
    assert task_state["status"] == "completed"
    state = overview(client, auth_headers)
    summary = result["return_summary"]
    assert state["cultivation"] == exp + 15 + exp // 10 + summary["encounter_reward"]["cultivation"]
    assert state["spirit_stones"] == stones + 9 + summary["encounter_reward"]["spirit_stones"]
    assert len(state["recent_rewards"]) == 4


@pytest.mark.parametrize("action,seconds,qi,exp,stones", [
    ("complete", 20 * 60 - 1, 19, 4, 2),
    ("abort", 13 * 60 + 59, 13, 3, 1),
    ("abort", 59, 0, 0, 0),
])
def test_early_end_uses_whole_minutes_without_completing_the_task(
    client, auth_headers, retreat_clock, action, seconds, qi, exp, stones
):
    task = create_task(client, auth_headers)
    session = start(client, auth_headers, todo_id=task["id"])
    retreat_clock(datetime(2026, 11, 16, 2, tzinfo=timezone.utc) + timedelta(seconds=seconds))
    response = client.post(
        f"{BASE}/{session['id']}/{action}", headers=auth_headers,
        json={"mark_todo_complete": True},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "aborted"
    assert (result["qi_gained"], result["exp_gained"], result["coins_gained"]) == (qi, exp, stones)
    assert result["settlement_result"]["conversion_rate"] == 0.25
    assert result["settlement_result"]["task_reward"] is None
    assert client.get(f"/api/todos/tasks/{task['id']}", headers=auth_headers).json()["status"] == "pending"
    state = overview(client, auth_headers)
    assert (state["cultivation"], state["spirit_stones"], state["aptitude_points"]) == (exp, stones, 0)


@pytest.mark.parametrize("action", ["complete", "abort"])
def test_repeated_settlement_returns_the_immutable_result_without_rewarding_again(
    client, auth_headers, retreat_clock, action
):
    task = create_task(client, auth_headers)
    session = start(client, auth_headers, todo_id=task["id"])
    retreat_clock(datetime(2026, 11, 16, 2, 25, tzinfo=timezone.utc))
    response = client.post(f"{BASE}/{session['id']}/{action}", headers=auth_headers, json={"mark_todo_complete": True})
    assert response.status_code == 200, response.text
    settled = response.json()
    before = overview(client, auth_headers)
    retreat_clock(datetime(2026, 11, 17, 3, tzinfo=timezone.utc))
    for endpoint in ("complete", "abort", "complete"):
        replay = client.post(f"{BASE}/{session['id']}/{endpoint}", headers=auth_headers, json={"mark_todo_complete": False})
        assert replay.status_code == 200, replay.text
        assert replay.json() == settled
    after = overview(client, auth_headers)
    for key in ("cultivation", "spirit_stones", "merit", "mind_state", "aptitude_points", "recent_rewards"):
        assert after[key] == before[key]


def test_daily_qi_cap_uses_the_china_settlement_date_and_resets_at_midnight(
    client, auth_headers, retreat_clock
):
    retreat_clock(datetime(2026, 11, 16, 11, 25, tzinfo=timezone.utc))
    first = start(client, auth_headers, 235)
    retreat_clock(datetime(2026, 11, 16, 15, 20, tzinfo=timezone.utc))
    result = finish(client, auth_headers, first).json()
    assert result["qi_gained"] == 235
    assert result["settlement_result"]["daily_qi_total"] == 235
    assert result["settlement_result"]["daily_qi_cap_reached"] is False
    second = start(client, auth_headers)
    retreat_clock(datetime(2026, 11, 16, 15, 45, tzinfo=timezone.utc))
    capped = finish(client, auth_headers, second).json()
    assert (capped["qi_gained"], capped["exp_gained"], capped["coins_gained"]) == (5, 1, 0)
    assert capped["settlement_result"]["daily_qi_total"] == 240
    assert capped["settlement_result"]["daily_qi_cap_reached"] is True
    third = start(client, auth_headers)
    retreat_clock(datetime(2026, 11, 16, 15, 55, tzinfo=timezone.utc))
    exhausted = client.post(f"{BASE}/{third['id']}/abort", headers=auth_headers).json()
    assert (exhausted["qi_gained"], exhausted["exp_gained"], exhausted["coins_gained"]) == (0, 0, 0)
    assert exhausted["settlement_result"]["daily_qi_cap_reached"] is True
    crossing_midnight = start(client, auth_headers)
    retreat_clock(datetime(2026, 11, 16, 16, 20, tzinfo=timezone.utc))
    next_day = finish(client, auth_headers, crossing_midnight).json()
    assert next_day["qi_gained"] == 25
    assert next_day["settlement_result"]["daily_qi_total"] == 25
    assert next_day["settlement_result"]["daily_qi_cap_reached"] is False


def test_startup_migration_preserves_old_history_and_active_session_rules(
    client, auth_headers, db_session, user, retreat_clock, run_startup_migrations
):
    from sqlalchemy import text
    from app.models.cultivation_retreat import CultivationRetreat

    old_history = CultivationRetreat(
        user_id=user.id, target_duration=25, status="completed",
        started_at=datetime(2026, 11, 15, 2), ended_at=datetime(2026, 11, 15, 2, 25),
        actual_duration=25, exp_gained=333, coins_gained=222,
        encounter_result={"title": "旧机缘", "reward_payload": {"exp": 83}},
    )
    old_active = CultivationRetreat(
        user_id=user.id, target_duration=25, status="active",
        started_at=datetime(2026, 11, 16, 2),
    )
    db_session.add_all([old_history, old_active])
    db_session.commit()
    historical_id, active_id = str(old_history.id), str(old_active.id)
    db_session.execute(text(
        "CREATE TABLE legacy_retreats AS SELECT id, user_id, todo_id, target_duration, "
        "actual_duration, status, started_at, ended_at, exp_gained, coins_gained, "
        "encounter_id, encounter_result, created_at FROM cultivation_retreats"
    ))
    db_session.execute(text("DROP TABLE cultivation_retreats"))
    db_session.execute(text("ALTER TABLE legacy_retreats RENAME TO cultivation_retreats"))
    db_session.commit()
    db_session.expunge_all()
    run_startup_migrations(db_session)
    run_startup_migrations(db_session)

    response = client.get(f"{BASE}/history", headers=auth_headers)
    assert response.status_code == 200, response.text
    history = {row["id"]: row for row in response.json()}
    persisted = history[historical_id]
    assert (persisted["exp_gained"], persisted["coins_gained"]) == (333, 222)
    assert persisted["encounter_result"]["title"] == "旧机缘"
    assert persisted["qi_gained"] is persisted["rule_version"] is persisted["settlement_id"] is persisted["settlement_result"] is persisted["return_summary"] is None
    active = client.get(f"{BASE}/active", headers=auth_headers).json()
    assert active["id"] == active_id and active["rule_version"] is None
    retreat_clock(datetime(2026, 11, 16, 2, 26, tzinfo=timezone.utc))
    settled = finish(client, auth_headers, active)
    assert settled.status_code == 200, settled.text
    assert (settled.json()["exp_gained"], settled.json()["coins_gained"]) == (250, 125)
    assert settled.json()["qi_gained"] is settled.json()["return_summary"] is None
    assert start(client, auth_headers)["rule_version"] == "b_v1"
    remaining_history = client.get(f"{BASE}/history", headers=auth_headers).json()
    assert next(row for row in remaining_history if row["id"] == historical_id) == persisted


@pytest.mark.parametrize("complete_before,mark_complete", [(True, True), (False, False)])
def test_only_a_task_completed_in_this_settlement_gets_the_half_rate(
    client, auth_headers, retreat_clock, complete_before, mark_complete
):
    task = create_task(client, auth_headers)
    if complete_before:
        response = client.post(f"/api/todos/tasks/{task['id']}/complete", headers=auth_headers)
        assert response.status_code == 200
    before = overview(client, auth_headers)
    session = start(client, auth_headers, todo_id=task["id"])
    retreat_clock(datetime(2026, 11, 16, 2, 25, tzinfo=timezone.utc))
    result = finish(client, auth_headers, session, mark_todo_complete=mark_complete).json()
    assert (result["exp_gained"], result["coins_gained"]) == (6, 3)
    assert result["settlement_result"]["task_completed"] is False
    assert result["settlement_result"]["task_previously_completed"] is complete_before
    assert result["settlement_result"]["task_reward"] is None
    after = overview(client, auth_headers)
    encounter = result["return_summary"]["encounter_reward"]
    assert after["cultivation"] - before["cultivation"] == 6 + encounter["cultivation"]
    assert after["spirit_stones"] - before["spirit_stones"] == 3 + encounter["spirit_stones"]
    assert len(after["recent_rewards"]) - len(before["recent_rewards"]) == 3


def test_task_and_retreat_rewards_roll_back_together_after_database_failure(
    client, auth_headers, retreat_clock, db_session
):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    task = create_task(client, auth_headers)
    session = start(client, auth_headers, todo_id=task["id"])
    before = overview(client, auth_headers)
    retreat_clock(datetime(2026, 11, 16, 2, 25, tzinfo=timezone.utc))
    db_session.execute(text(
        "CREATE TRIGGER reject_retreat BEFORE INSERT ON cultivation_logs "
        "WHEN NEW.source = 'retreat' BEGIN SELECT RAISE(ABORT, 'settlement unavailable'); END"
    ))
    db_session.commit()
    try:
        with pytest.raises(IntegrityError, match="settlement unavailable"):
            finish(client, auth_headers, session, mark_todo_complete=True)
        assert client.get(f"{BASE}/active", headers=auth_headers).json()["id"] == session["id"]
        assert client.get(f"/api/todos/tasks/{task['id']}", headers=auth_headers).json()["status"] == "pending"
        after = overview(client, auth_headers)
        for key in ("cultivation", "spirit_stones", "merit", "mind_state", "aptitude_points", "recent_rewards"):
            assert after[key] == before[key]
    finally:
        db_session.execute(text("DROP TRIGGER reject_retreat"))
        db_session.commit()
    retried = finish(client, auth_headers, session, mark_todo_complete=True)
    assert retried.status_code == 200, retried.text
    assert (retried.json()["exp_gained"], retried.json()["coins_gained"]) == (12, 7)
    assert retried.json()["settlement_result"]["daily_qi_total"] == 25


def test_high_profile_efficiency_cannot_multiply_the_b_rule(
    client, auth_headers, retreat_clock, db_session, user
):
    from app.models.cultivation import CultivationProfile

    db_session.add(CultivationProfile(user_id=user.id, aptitude_points=225, cultivation_efficiency=1.6))
    db_session.commit()
    session = start(client, auth_headers)
    retreat_clock(datetime(2026, 11, 16, 3, tzinfo=timezone.utc))
    result = finish(client, auth_headers, session).json()
    assert (result["qi_gained"], result["exp_gained"], result["coins_gained"]) == (25, 6, 3)
    assert overview(client, auth_headers)["aptitude_points"] == 225


def test_concurrent_http_settlements_return_one_result_and_reward_once(
    client, auth_headers, user, retreat_clock, database, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import sessionmaker
    from app.database import get_db
    from app.main import app
    from app.models.user import User

    database.add(User(id=user.id, username="concurrent-focus", email="concurrent@example.com", password_hash="unused", coins=100))
    database.commit()
    sessions = sessionmaker(bind=database.get_bind())

    def get_file_db():
        with sessions() as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, get_file_db)
    task = create_task(client, auth_headers)
    session = start(client, auth_headers, todo_id=task["id"])
    retreat_clock(datetime(2026, 11, 16, 2, 25, tzinfo=timezone.utc))
    barrier = Barrier(2)

    def settle(_):
        barrier.wait(timeout=10)
        response = finish(client, auth_headers, session, mark_todo_complete=True)
        assert response.status_code == 200, response.text
        return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(settle, range(2)))
    assert results[0] == results[1]
    state = overview(client, auth_headers)
    encounter = results[0]["return_summary"]["encounter_reward"]
    assert (state["cultivation"], state["spirit_stones"]) == (28 + encounter["cultivation"], 16 + encounter["spirit_stones"])
    assert len(state["recent_rewards"]) == 4
    assert client.get(f"/api/todos/tasks/{task['id']}", headers=auth_headers).json()["status"] == "completed"


def test_80_percent_completion_uses_actual_qi_without_filling_the_target(
    client, auth_headers, retreat_clock
):
    task = create_task(client, auth_headers)
    session = start(client, auth_headers, todo_id=task["id"])
    retreat_clock(datetime(2026, 11, 16, 2, 20, tzinfo=timezone.utc))
    response = finish(client, auth_headers, session, mark_todo_complete=True)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "completed"
    assert (result["qi_gained"], result["exp_gained"], result["coins_gained"]) == (20, 10, 6)
    assert result["settlement_result"]["task_completed"] is True


@pytest.mark.parametrize("seconds,qi,merit,mind", [(59, 0, 0, 50), (60, 1, 2, 51)])
def test_retreat_resource_rewards_require_at_least_one_qi(
    client, auth_headers, retreat_clock, seconds, qi, merit, mind
):
    session = start(client, auth_headers)
    retreat_clock(datetime(2026, 11, 16, 2, tzinfo=timezone.utc) + timedelta(seconds=seconds))
    result = client.post(f"{BASE}/{session['id']}/abort", headers=auth_headers).json()
    assert result["qi_gained"] == qi
    assert (result["exp_gained"], result["coins_gained"]) == (0, 0)
    state = overview(client, auth_headers)
    assert (state["merit"], state["mind_state"], state["aptitude_points"], state["contribution"]) == (merit, mind, 0, 0)


def test_retreat_logs_do_not_consume_the_daily_task_aptitude_allowance(
    client, auth_headers, retreat_clock
):
    retreat_clock(datetime.now(timezone.utc))
    for _ in range(8):
        session = start(client, auth_headers)
        response = client.post(f"{BASE}/{session['id']}/abort", headers=auth_headers)
        assert response.status_code == 200
    task = create_task(client, auth_headers)
    completed = client.post(f"/api/todos/tasks/{task['id']}/complete", headers=auth_headers)
    assert completed.status_code == 200, completed.text
    assert completed.json()["cultivation_reward"]["aptitude_points"] == 1


def test_unbound_focus_settles_qi_through_the_reward_ledger(
    client, auth_headers, retreat_clock
):
    session = start(client, auth_headers)
    retreat_clock(datetime(2026, 11, 16, 2, 25, tzinfo=timezone.utc))

    response = finish(client, auth_headers, session)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (result["exp_gained"], result["coins_gained"]) == (6, 3)
    assert result["qi_gained"] == 25
    assert result["rule_version"] == "b_v1"
    reward = result["settlement_result"]["retreat_reward"]
    assert result["settlement_id"] == reward["log_id"]
    assert (reward["cultivation"], reward["spirit_stones"]) == (6, 3)
    assert (reward["merit"], reward["mind_state_delta"], reward["contribution"], reward["aptitude_points"]) == (2, 1, 0, 0)
    state = overview(client, auth_headers)
    encounter = result["return_summary"]["encounter_reward"]
    assert (state["cultivation"], state["spirit_stones"], state["merit"], state["mind_state"], state["aptitude_points"]) == (6 + encounter["cultivation"], 3 + encounter["spirit_stones"], 2, 51, 0)
    assert {row["source"]: (row["cultivation"], row["spirit_stones"]) for row in state["recent_rewards"]} == {
        "retreat": (6, 3), "retreat_omen": (0, 0),
        "retreat_encounter": (encounter["cultivation"], encounter["spirit_stones"]),
    }
    history = client.get(f"{BASE}/history", headers=auth_headers).json()
    assert history == [result]
