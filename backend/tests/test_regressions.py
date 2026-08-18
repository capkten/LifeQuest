from multiprocessing import get_context
from queue import Empty
from time import monotonic
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.cultivation import CultivationLog, CultivationProfile
from app.models.todo import Goal, Habit, Task, TaskStatus
from app.models.user import User
from app.services.todo import TodoService

from app.models.coin_transaction import CoinTransaction


def _collect_process_messages(results, expected, timeout=5):
    messages = []
    deadline = monotonic() + timeout
    while len(messages) < expected:
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        try:
            messages.append(results.get(timeout=remaining))
        except Empty:
            break
    return messages


def _run_achievement_threshold_process(db_path, user_id, achievement_id, barrier, results):
    """Race an achievement threshold check from an independent process/session."""
    import time

    from sqlalchemy import create_engine, event
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.orm import sessionmaker

    from app.services.achievement import AchievementService

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"timeout": 30},
    )
    synchronized = False

    @event.listens_for(engine, "before_cursor_execute")
    def synchronize_threshold_reads(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ):
        nonlocal synchronized
        if not synchronized and "from user_achievements" in statement.lower():
            synchronized = True
            results.put(("barrier_reached",))
            barrier.wait(timeout=20)

    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        service = AchievementService(session)
        for attempt in range(3):
            try:
                unlocked = service.check_and_unlock(
                    UUID(user_id), "task_count", 1
                )
                break
            except OperationalError as exc:
                if "locked" not in str(exc).lower() or attempt == 2:
                    raise
                session.rollback()
                time.sleep(0.1)
        results.put(("ok", len(unlocked)))
    except Exception as exc:
        session.rollback()
        results.put(("error", repr(exc)))
    finally:
        session.close()
        engine.dispose()


def _run_todo_completion_process(db_path, kind, todo_id, user_id, barrier, results):
    """Start the same completion from two independent OS processes."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker

    from app.models.todo import Goal, Habit, Task
    from app.services.todo import TodoService

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"timeout": 30},
    )
    synchronized = False
    table_name = {"task": "tasks", "habit": "habits", "goal": "goals"}[kind]

    @event.listens_for(engine, "before_cursor_execute")
    def synchronize_completion_updates(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ):
        nonlocal synchronized
        if not synchronized and f"update {table_name}" in statement.lower():
            synchronized = True
            results.put(("barrier_reached",))
            barrier.wait(timeout=20)

    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        model = {"task": Task, "habit": Habit, "goal": Goal}[kind]
        todo = session.get(model, UUID(todo_id))
        completed = getattr(TodoService(session), f"complete_{kind}")(
            todo, UUID(user_id)
        )
        results.put(("ok", str(completed.id)))
    except Exception as exc:
        session.rollback()
        results.put(("error", repr(exc)))
    finally:
        session.close()
        engine.dispose()


def _register_and_login(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "regression-user",
            "email": "regression@example.com",
            "password": "testpassword123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "regression-user", "password": "testpassword123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_first_goal_completion_records_base_and_achievement_rewards(client, db_session):
    headers = _register_and_login(client)
    goal_response = client.post(
        "/api/todos/goals",
        json={
            "title": "Regression goal",
            "difficulty": "hard",
            "coins_reward": 100,
            "exp_reward": 50,
        },
        headers=headers,
    )
    assert goal_response.status_code == 200
    goal_id = goal_response.json()["id"]

    before = client.get("/api/users/me", headers=headers).json()
    completion = client.post(f"/api/todos/goals/{goal_id}/complete", headers=headers)
    assert completion.status_code == 200

    after_first = client.get("/api/users/me", headers=headers).json()
    assert after_first["coins"] == before["coins"] + 150
    assert after_first["experience"] == before["experience"] + 50

    transactions = (
        db_session.query(CoinTransaction)
        .filter(CoinTransaction.user_id == UUID(before["id"]))
        .order_by(CoinTransaction.id)
        .all()
    )
    assert [(transaction.source, transaction.amount) for transaction in transactions] == [
        ("goal", 100),
        ("achievement", 50),
    ]

    second_completion = client.post(f"/api/todos/goals/{goal_id}/complete", headers=headers)
    assert second_completion.status_code == 200
    after_second = client.get("/api/users/me", headers=headers).json()
    assert after_second["coins"] == after_first["coins"]
    assert after_second["experience"] == after_first["experience"]


def test_checkin_response_reports_written_rewards_and_repeat_is_not_rewarded(client, db_session):
    headers = _register_and_login(client)

    first = client.post("/api/checkin", headers=headers)
    assert first.status_code == 200
    payload = first.json()
    assert payload["reward_coins"] > 0
    assert payload["reward_exp"] > 0

    user_id = UUID(client.get("/api/users/me", headers=headers).json()["id"])
    checkin_transactions = (
        db_session.query(CoinTransaction)
        .filter(
            CoinTransaction.user_id == user_id,
            CoinTransaction.source == "checkin",
        )
        .all()
    )
    assert len(checkin_transactions) == 1
    assert checkin_transactions[0].amount == payload["reward_coins"]

    repeat = client.post("/api/checkin", headers=headers)
    assert repeat.status_code == 400
    assert (
        db_session.query(CoinTransaction)
        .filter(
            CoinTransaction.user_id == user_id,
            CoinTransaction.source == "checkin",
        )
        .count()
        == 1
    )


def test_coin_history_returns_filtered_transactions_and_totals(client, db_session):
    headers = _register_and_login(client)
    checkin = client.post("/api/checkin", headers=headers)
    assert checkin.status_code == 200

    user_id = UUID(client.get("/api/users/me", headers=headers).json()["id"])
    from app.models.coin_transaction import CoinSource, CoinType
    from app.repositories.coin_transaction import CoinTransactionRepository

    CoinTransactionRepository(db_session).create_transaction(
        user_id=user_id,
        amount=7,
        coin_type=CoinType.SPEND,
        source=CoinSource.SHOP,
        description="test spend",
    )

    earned = client.get("/api/coins/history?coin_type=earn", headers=headers)
    spent = client.get("/api/coins/history?coin_type=spend", headers=headers)

    assert earned.status_code == 200
    assert spent.status_code == 200
    assert earned.json()["transactions"]
    assert all(item["type"] == "earn" for item in earned.json()["transactions"])
    assert earned.json()["total_earned"] == checkin.json()["reward_coins"]
    assert spent.json()["transactions"][0]["type"] == "spend"
    assert spent.json()["total_spent"] == 7
    assert spent.json()["count"] == 1


def test_todo_coin_sources_are_unique_for_repeated_completion(client, db_session):
    headers = _register_and_login(client)
    task = client.post(
        "/api/todos/tasks",
        json={"title": "Unique reward", "coins_reward": 12, "exp_reward": 4},
        headers=headers,
    ).json()
    user_id = UUID(client.get("/api/users/me", headers=headers).json()["id"])

    assert client.post(f"/api/todos/tasks/{task['id']}/complete", headers=headers).status_code == 200
    assert client.post(f"/api/todos/tasks/{task['id']}/complete", headers=headers).status_code == 200

    rows = db_session.query(CoinTransaction).filter(
        CoinTransaction.user_id == user_id,
        CoinTransaction.source == "task",
    ).all()
    assert len(rows) == 1
    assert rows[0].source_id

    duplicate = CoinTransaction(
        user_id=user_id,
        amount=12,
        type="earn",
        source="task",
        source_id=rows[0].source_id,
        description="duplicate source probe",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_concurrent_task_habit_goal_completion_settles_each_source_once(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'completion-concurrency.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    setup = SessionLocal()
    try:
        user = User(
            username="concurrent-user",
            email="concurrent@example.com",
            password_hash="not-used",
        )
        setup.add(user)
        setup.flush()
        setup.add(CultivationProfile(user_id=user.id))
        task = Task(user_id=user.id, title="Concurrent task", coins_reward=11, exp_reward=3)
        habit = Habit(user_id=user.id, title="Concurrent habit", coins_reward=13, exp_reward=4)
        goal = Goal(user_id=user.id, title="Concurrent goal", coins_reward=17, exp_reward=5)
        setup.add_all([task, habit, goal])
        setup.commit()
        user_id = user.id
        ids = {"task": task.id, "habit": habit.id, "goal": goal.id}
    finally:
        setup.close()

    def complete(kind):
        db = SessionLocal()
        try:
            service = TodoService(db)
            model = {"task": Task, "habit": Habit, "goal": Goal}[kind]
            item = db.query(model).filter(model.id == ids[kind]).one()
            return getattr(service, f"complete_{kind}")(item, user_id)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(complete, kind) for kind in ("task", "habit", "goal") for _ in range(2)]
        results = [future.result() for future in futures]

    assert len(results) == 6
    verify = SessionLocal()
    try:
        transactions = verify.query(CoinTransaction).filter(
            CoinTransaction.user_id == user_id,
            CoinTransaction.source.in_(["task", "habit", "goal"]),
        ).all()
        logs = verify.query(CultivationLog).filter(CultivationLog.user_id == user_id).all()
        assert {transaction.source for transaction in transactions} == {"task", "habit", "goal"}
        assert len(transactions) == 3
        assert {log.source for log in logs} == {"task", "habit", "goal"}
        assert len(logs) == 3
    finally:
        verify.close()
        Base.metadata.drop_all(bind=engine)


def test_achievement_threshold_race_uses_database_constraint_not_process_lock(
    tmp_path, monkeypatch
):
    from tests.test_startup_config import _create_legacy_reward_database
    from app import main as main_module
    from app.models.achievement import UserAchievement

    legacy_engine = _create_legacy_reward_database(tmp_path / "achievement-race.sqlite")
    user_id = uuid4()
    achievement_id = uuid4()
    with legacy_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users "
            "(id, username, email, password_hash, level, experience, coins, "
            "total_coins_earned, title) VALUES "
            "(:user_id, 'race-user', 'race@example.com', 'hashed', 1, 0, 0, 0, '初学者')"
        ), {"user_id": user_id.hex})
        connection.execute(text(
            "INSERT INTO achievements "
            "(id, name, description, condition_type, condition_value, coin_reward, exp_reward) "
            "VALUES (:achievement_id, 'Race achievement', 'test', 'task_count', 1, 50, 0)"
        ), {"achievement_id": achievement_id.hex})

    monkeypatch.setattr(main_module, "engine", legacy_engine)
    main_module._migrate_columns()

    context = get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(
            target=_run_achievement_threshold_process,
            args=(
                str(tmp_path / "achievement-race.sqlite"),
                str(user_id),
                str(achievement_id),
                barrier,
                results,
            ),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=30)
        assert not process.is_alive()
        assert process.exitcode == 0

    messages = _collect_process_messages(results, expected=len(processes) * 2)
    markers = [message for message in messages if message[0] == "barrier_reached"]
    outcomes = [message for message in messages if message[0] in {"ok", "error"}]
    assert len(markers) == 2, messages
    assert len(outcomes) == 2, messages
    assert all(outcome[0] == "ok" for outcome in outcomes), outcomes
    assert sum(outcome[1] for outcome in outcomes) == 1

    verify = sessionmaker(autocommit=False, autoflush=False, bind=legacy_engine)()
    try:
        assert verify.query(UserAchievement).filter_by(user_id=user_id).count() == 1
        assert verify.query(CoinTransaction).filter_by(
            user_id=user_id, source="achievement"
        ).count() == 1
    finally:
        verify.close()
        legacy_engine.dispose()


@pytest.mark.parametrize(
    ("model", "kind", "source"),
    [(Task, "task", "task"), (Habit, "habit", "habit"), (Goal, "goal", "goal")],
)
def test_distinct_process_completion_claims_one_settlement_per_source(
    tmp_path, model, kind, source
):
    database_path = tmp_path / f"{kind}-process-race.sqlite"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))

    setup = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        user = User(
            username=f"process-{kind}-{uuid4().hex}",
            email=f"process-{kind}-{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.flush()
        setup.add(CultivationProfile(user_id=user.id))
        todo = model(
            user_id=user.id,
            title=f"Process race {kind}",
            coins_reward=20,
            exp_reward=15,
        )
        setup.add(todo)
        setup.commit()
        todo_id = todo.id
        user_id = user.id
    finally:
        setup.close()

    context = get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(
            target=_run_todo_completion_process,
            args=(str(database_path), kind, str(todo_id), str(user_id), barrier, results),
        )
        for _ in range(2)
    ]
    try:
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=30)
            assert not process.is_alive()
            assert process.exitcode == 0

        messages = _collect_process_messages(results, expected=len(processes) * 2)
        markers = [message for message in messages if message[0] == "barrier_reached"]
        outcomes = [message for message in messages if message[0] in {"ok", "error"}]
        assert len(markers) == 2, messages
        assert len(outcomes) == 2, messages
        assert all(outcome[0] == "ok" for outcome in outcomes), outcomes

        verify = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        try:
            persisted = verify.get(model, todo_id)
            if kind == "habit":
                assert persisted.streak == 1
            else:
                assert persisted.status == TaskStatus.COMPLETED
            assert verify.query(CoinTransaction).filter_by(
                user_id=user_id, source=source
            ).count() == 1
            assert verify.query(CultivationLog).filter_by(
                user_id=user_id, source=source
            ).count() == 1
        finally:
            verify.close()
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()
        engine.dispose()
