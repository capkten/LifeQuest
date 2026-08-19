from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.coin_transaction import CoinTransaction
from app.models.cultivation import CultivationLog, CultivationProfile
from app.models.todo import Goal, Habit, Task, TaskStatus
from app.models.user import User


def test_legacy_learned_techniques_are_deduplicated_before_unique_index(
    tmp_path, monkeypatch
):
    from app import main as main_module

    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'legacy-techniques.sqlite'}")
    Base.metadata.create_all(bind=legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(text("DROP TABLE learned_techniques"))
        connection.execute(text(
            "CREATE TABLE learned_techniques ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "technique_id VARCHAR(36) NOT NULL, learned_at DATETIME NOT NULL, "
            "level INTEGER NOT NULL DEFAULT 1)"
        ))
        connection.execute(text(
            "INSERT INTO learned_techniques "
            "(id, user_id, technique_id, learned_at, level) VALUES "
            "('old', 'user-1', 'technique-1', '2026-08-16 09:00:00', 1), "
            "('new', 'user-1', 'technique-1', '2026-08-17 09:00:00', 2), "
            "('other', 'user-1', 'technique-2', '2026-08-17 09:00:00', 1)"
        ))

    monkeypatch.setattr(main_module, "engine", legacy_engine)
    main_module._migrate_columns()
    main_module._migrate_columns()

    inspector = inspect(legacy_engine)
    unique_indexes = [
        index for index in inspector.get_indexes("learned_techniques")
        if index["unique"] and index["column_names"] == ["user_id", "technique_id"]
    ]
    unique_constraints = [
        constraint for constraint in inspector.get_unique_constraints("learned_techniques")
        if constraint["column_names"] == ["user_id", "technique_id"]
    ]
    with legacy_engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id FROM learned_techniques ORDER BY id"
        )).fetchall()

    assert rows == [("new",), ("other",)]
    assert len(unique_indexes) + len(unique_constraints) == 1
    legacy_engine.dispose()


def test_fresh_learned_techniques_have_one_composite_unique_definition(tmp_path):
    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'fresh-techniques.sqlite'}")
    Base.metadata.create_all(bind=fresh_engine)

    inspector = inspect(fresh_engine)
    unique_indexes = [
        index for index in inspector.get_indexes("learned_techniques")
        if index["unique"] and index["column_names"] == ["user_id", "technique_id"]
    ]
    unique_constraints = [
        constraint for constraint in inspector.get_unique_constraints("learned_techniques")
        if constraint["column_names"] == ["user_id", "technique_id"]
    ]

    assert len(unique_indexes) + len(unique_constraints) == 1
    fresh_engine.dispose()


def test_same_named_non_unique_learned_technique_index_is_replaced(tmp_path, monkeypatch):
    from app import main as main_module

    legacy_engine = create_engine(f"sqlite:///{tmp_path / 'same-named-index.sqlite'}")
    Base.metadata.create_all(bind=legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(text("DROP TABLE learned_techniques"))
        connection.execute(text(
            "CREATE TABLE learned_techniques ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "technique_id VARCHAR(36) NOT NULL, learned_at DATETIME NOT NULL, "
            "level INTEGER NOT NULL DEFAULT 1)"
        ))
        connection.execute(text(
            "CREATE INDEX uq_learned_technique_user_technique "
            "ON learned_techniques (user_id, technique_id)"
        ))
        connection.execute(text(
            "INSERT INTO learned_techniques "
            "(id, user_id, technique_id, learned_at, level) VALUES "
            "('only', 'user-1', 'technique-1', '2026-08-17 09:00:00', 1)"
        ))

    monkeypatch.setattr(main_module, "engine", legacy_engine)
    main_module._migrate_columns()
    main_module._migrate_columns()

    indexes = {
        index["name"]: index
        for index in inspect(legacy_engine).get_indexes("learned_techniques")
    }
    assert bool(indexes["uq_learned_technique_user_technique"]["unique"]) is True
    legacy_engine.dispose()


def test_task_reward_replay_after_reset_returns_original_settlement_without_duplicates(
    client, db_session
):
    from tests.test_todos import _register_and_login

    headers = _register_and_login(client)
    task = client.post(
        "/api/todos/tasks",
        json={"title": "Replay-safe task", "coins_reward": 20, "exp_reward": 15},
        headers=headers,
    ).json()

    first = client.post(f"/api/todos/tasks/{task['id']}/complete", headers=headers)
    assert first.status_code == 200
    first_payload = first.json()

    user = db_session.query(User).filter(User.username == "testuser").one()
    profile = db_session.query(CultivationProfile).filter(
        CultivationProfile.user_id == user.id
    ).one()
    first_state = (user.coins, user.total_coins_earned, user.level, user.experience, profile.cultivation, profile.spirit_stones)
    first_task_logs = db_session.query(CultivationLog).filter(
        CultivationLog.user_id == user.id,
        CultivationLog.source == "task",
    ).count()
    first_task_transactions = db_session.query(CoinTransaction).filter(
        CoinTransaction.user_id == user.id,
        CoinTransaction.source == "task",
    ).count()

    reset = client.put(
        f"/api/todos/tasks/{task['id']}",
        json={"status": "pending"},
        headers=headers,
    )
    assert reset.status_code == 200

    second = client.post(f"/api/todos/tasks/{task['id']}/complete", headers=headers)
    assert second.status_code == 200
    assert second.json()["cultivation_reward"] == first_payload["cultivation_reward"]

    db_session.expire_all()
    user = db_session.query(User).filter(User.username == "testuser").one()
    profile = db_session.query(CultivationProfile).filter(
        CultivationProfile.user_id == user.id
    ).one()
    assert (user.coins, user.total_coins_earned, user.level, user.experience, profile.cultivation, profile.spirit_stones) == first_state
    assert db_session.query(CultivationLog).filter(
        CultivationLog.user_id == user.id,
        CultivationLog.source == "task",
    ).count() == first_task_logs
    assert db_session.query(CoinTransaction).filter(
        CoinTransaction.user_id == user.id,
        CoinTransaction.source == "task",
    ).count() == first_task_transactions


def test_source_key_conflict_in_independent_sessions_returns_original_settlement(tmp_path):
    from app.services.todo import TodoService

    engine = create_engine(f"sqlite:///{tmp_path / 'source-key-conflict.sqlite'}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    first_session = session_factory()
    second_session = session_factory()
    try:
        user = User(
            username=f"source-{uuid4().hex}",
            email=f"source-{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        first_session.add(user)
        first_session.commit()

        first_user = first_session.get(User, user.id)
        first_result = TodoService(first_session)._update_rewards(
            first_user, 20, 15, "task", source_key="todo:task:conflict"
        )
        first_session.commit()
        first_user = first_session.get(User, user.id)
        first_profile = first_session.query(CultivationProfile).filter(
            CultivationProfile.user_id == user.id
        ).one()
        first_state = (
            first_user.coins,
            first_user.total_coins_earned,
            first_user.experience,
            first_profile.cultivation,
            first_profile.spirit_stones,
        )

        second_user = second_session.get(User, user.id)
        second_result = TodoService(second_session)._update_rewards(
            second_user, 20, 15, "task", source_key="todo:task:conflict"
        )
        second_session.commit()

        assert second_result.model_dump() == first_result.model_dump()
        assert second_session.query(CultivationLog).filter(
            CultivationLog.source_key == "todo:task:conflict"
        ).count() == 1
        assert second_session.query(CoinTransaction).filter(
            CoinTransaction.user_id == user.id,
            CoinTransaction.source == "task",
        ).count() == 1
        assert second_session.query(CultivationLog).filter(
            CultivationLog.source_key == "todo:task:conflict"
        ).count() == 1
        profile = second_session.query(CultivationProfile).filter(
            CultivationProfile.user_id == user.id
        ).one()
        assert (
            second_user.coins,
            second_user.total_coins_earned,
            second_user.experience,
            profile.cultivation,
            profile.spirit_stones,
        ) == first_state
    finally:
        first_session.close()
        second_session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("model", "source", "complete"),
    [
        (Task, "task", "complete_task"),
        (Habit, "habit", "complete_habit"),
        (Goal, "goal", "complete_goal"),
    ],
)
def test_lock_retry_preserves_completed_todo_state_and_claims_once(
    tmp_path, model, source, complete
):
    from app.services.todo import TodoService

    engine = create_engine(f"sqlite:///{tmp_path / f'{source}-lock-regression.sqlite'}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    injected = False

    def inject_lock(_conn, _cursor, statement, parameters, _context, _executemany):
        nonlocal injected
        if not injected and "insert into cultivation_logs" in statement.lower():
            injected = True
            raise OperationalError(
                statement,
                parameters,
                sqlite3.OperationalError("database is locked"),
            )

    event.listen(engine, "before_cursor_execute", inject_lock)
    try:
        user = User(
            username=f"regression-{uuid4().hex}",
            email=f"regression-{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        session.add(user)
        session.flush()
        todo = model(
            user_id=user.id,
            title=f"{source} lock regression",
            coins_reward=20,
            exp_reward=15,
        )
        session.add(todo)
        session.commit()
        source_key = f"todo:{source}:{todo.id}"
        if model is Habit:
            source_key += f":{datetime.now(timezone.utc).date().isoformat()}"

        getattr(TodoService(session), complete)(todo, user.id)
        session.expire_all()
        persisted = session.get(model, todo.id)

        assert injected is True
        if model is Habit:
            assert persisted.streak == 1
            assert persisted.best_streak == 1
            assert persisted.last_completed_at is not None
        else:
            assert persisted.status == TaskStatus.COMPLETED
        assert session.query(CultivationLog).filter_by(source_key=source_key).count() == 1
        assert session.query(CoinTransaction).filter_by(
            user_id=user.id, source=source
        ).count() == 1
    finally:
        event.remove(engine, "before_cursor_execute", inject_lock)
        session.close()
        engine.dispose()


def test_locked_source_key_sessions_retry_after_explicit_lock_window(tmp_path):
    from app.services.todo import TodoService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'source-key-locked.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 0.01},
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    setup = session_factory()
    lock_errors = []
    lock_seen = Event()
    barrier = Barrier(2)

    def record_lock_error(error_context):
        original = error_context.original_exception
        if "locked" in str(original).lower():
            lock_errors.append(original)
            lock_seen.set()

    event.listen(engine, "handle_error", record_lock_error)
    try:
        user = User(
            username=f"locked-{uuid4().hex}",
            email=f"locked-{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.commit()
        user_id = user.id
        from app.services.cultivation import CultivationService

        CultivationService(setup).ensure_profile(user_id)
        setup.commit()

        def hold_write_lock():
            holder_session = session_factory()
            try:
                holder_session.execute(
                    text("UPDATE users SET coins = coins WHERE id = :id"),
                    {"id": str(user_id)},
                )
                holder_session.flush()
                barrier.wait(timeout=2)
                assert lock_seen.wait(timeout=2)
                holder_session.commit()
            finally:
                holder_session.close()

        def attempt_losing_claim():
            loser_session = session_factory()
            try:
                loser_user = loser_session.get(User, user_id)
                barrier.wait(timeout=2)
                result = TodoService(loser_session)._update_rewards(
                    loser_user, 20, 15, "task", source_key="todo:task:locked"
                )
                loser_session.commit()
                return result
            finally:
                loser_session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            holder = executor.submit(hold_write_lock)
            loser_result = executor.submit(attempt_losing_claim).result(timeout=2)
            holder.result(timeout=2)

        assert lock_errors
        assert loser_result.cultivation == 15
        assert loser_result.spirit_stones == 9
        verify = session_factory()
        try:
            stored_user = verify.get(User, user_id)
            profile = verify.query(CultivationProfile).filter_by(user_id=user_id).one()
            assert (stored_user.coins, stored_user.total_coins_earned, stored_user.experience) == (20, 20, 15)
            assert (profile.cultivation, profile.spirit_stones) == (
                15,
                9,
            )
            assert verify.query(CultivationLog).filter_by(source_key="todo:task:locked").count() == 1
            assert verify.query(CoinTransaction).filter_by(user_id=user_id, source="task").count() == 1
        finally:
            verify.close()
    finally:
        event.remove(engine, "handle_error", record_lock_error)
        setup.close()
        engine.dispose()


def test_locked_source_key_retry_exhaustion_is_bounded(tmp_path, monkeypatch):
    from app.services import cultivation as cultivation_module
    from app.services.cultivation import CultivationService
    from app.services.todo import TodoService

    engine = create_engine(
        f"sqlite:///{tmp_path / 'source-key-lock-exhaustion.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 0.01},
    )
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    setup = session_factory()
    barrier = Barrier(2)
    release_lock = Event()
    monkeypatch.setattr(cultivation_module, "SOURCE_KEY_RETRY_COUNT", 2)
    monkeypatch.setattr(cultivation_module, "SOURCE_KEY_RETRY_DELAY_SECONDS", 0.01)
    try:
        user = User(
            username=f"exhaust-{uuid4().hex}",
            email=f"exhaust-{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.commit()
        CultivationService(setup).ensure_profile(user.id)
        setup.commit()
        user_id = user.id

        def hold_write_lock():
            holder_session = session_factory()
            try:
                holder_session.execute(
                    text("UPDATE users SET coins = coins WHERE id = :id"),
                    {"id": str(user_id)},
                )
                holder_session.flush()
                barrier.wait(timeout=2)
                assert release_lock.wait(timeout=2)
            finally:
                holder_session.rollback()
                holder_session.close()

        def exhaust_claim_retries():
            loser_session = session_factory()
            try:
                loser_user = loser_session.get(User, user_id)
                barrier.wait(timeout=2)
                TodoService(loser_session)._update_rewards(
                    loser_user, 20, 15, "task", source_key="todo:task:exhausted"
                )
            finally:
                loser_session.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            holder = executor.submit(hold_write_lock)
            started = monotonic()
            loser = executor.submit(exhaust_claim_retries)
            try:
                with pytest.raises(OperationalError, match="database is locked"):
                    loser.result(timeout=1)
                elapsed = monotonic() - started
            finally:
                release_lock.set()
                holder.result(timeout=2)

        assert elapsed < 1
    finally:
        setup.close()
        engine.dispose()


def test_non_lock_operational_error_is_reraised_unchanged_and_session_survives(
    client, db_session
):
    from app.services.cultivation import CultivationService

    user = User(
        username=f"non-lock-{uuid4().hex}",
        email=f"non-lock-{uuid4().hex}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    expected = OperationalError(
        "INSERT INTO cultivation_profiles",
        {},
        sqlite3.OperationalError("no such table: cultivation_profiles"),
    )

    def raise_non_lock_error(
        _conn, _cursor, statement, _parameters, _context, _executemany
    ):
        if "insert into cultivation_logs" in statement.lower():
            raise expected

    event.listen(db_session.bind, "before_cursor_execute", raise_non_lock_error)
    try:
        with pytest.raises(OperationalError) as caught:
            CultivationService(db_session).settle_todo_reward(
                user.id,
                "task",
                15,
                "medium",
                source_key="todo:task:non-lock-error",
            )

        assert caught.value is expected
        assert db_session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        event.remove(db_session.bind, "before_cursor_execute", raise_non_lock_error)
