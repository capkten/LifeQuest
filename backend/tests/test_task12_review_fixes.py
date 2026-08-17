from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.coin_transaction import CoinTransaction
from app.models.cultivation import CultivationLog, CultivationProfile
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
        profile = second_session.query(CultivationProfile).filter(
            CultivationProfile.user_id == user.id
        ).one()
        assert (second_user.coins, second_user.experience, profile.cultivation, profile.spirit_stones) == first_state
    finally:
        first_session.close()
        second_session.close()
        engine.dispose()
