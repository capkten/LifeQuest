from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import Base

from app import main


def _create_legacy_reward_database(path):
    """Create an existing-style SQLite database without Task 2 reward indexes."""
    legacy_engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(bind=legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(text("DROP TABLE user_achievements"))
        connection.execute(text("DROP TABLE coin_transactions"))
        connection.execute(text(
            "CREATE TABLE user_achievements ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "achievement_id VARCHAR(36) NOT NULL, unlocked_at DATETIME)"
        ))
        connection.execute(text(
            "CREATE TABLE coin_transactions ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id VARCHAR(36) NOT NULL, "
            "amount INTEGER NOT NULL, type VARCHAR(10), source VARCHAR(20), "
            "source_id VARCHAR(36), description VARCHAR(200), created_at DATETIME)"
        ))
    return legacy_engine


def test_health_endpoint_requires_no_authentication(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_reports_database_failure(client, monkeypatch):
    def fail_connect():
        raise OSError("database unavailable")

    monkeypatch.setattr(main.engine, "connect", fail_connect)
    response = client.get("/api/health")
    assert response.status_code == 503


def test_startup_migrates_reward_idempotency_constraints_deterministically(
    tmp_path, monkeypatch
):
    legacy_engine = _create_legacy_reward_database(tmp_path / "legacy-rewards.sqlite")
    user_id = uuid4().hex
    achievement_id = uuid4().hex
    with legacy_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO user_achievements "
            "(id, user_id, achievement_id, unlocked_at) VALUES "
            "('b-keeper-candidate', :user_id, :achievement_id, '2026-08-18 10:00:00'), "
            "('a-keeper-candidate', :user_id, :achievement_id, '2026-08-19 10:00:00')"
        ), {"user_id": user_id, "achievement_id": achievement_id})
        connection.execute(text(
            "INSERT INTO coin_transactions "
            "(user_id, amount, type, source, source_id, description) VALUES "
            "(:user_id, 50, 'earn', 'achievement', 'achievement-1', 'old 1'), "
            "(:user_id, 50, 'earn', 'achievement', 'achievement-1', 'old 2'), "
            "(:user_id, 3, 'earn', 'checkin', NULL, 'legacy null 1'), "
            "(:user_id, 4, 'earn', 'checkin', NULL, 'legacy null 2')"
        ), {"user_id": user_id})

    monkeypatch.setattr(main, "engine", legacy_engine)
    main._migrate_columns()
    main._migrate_columns()

    inspector = inspect(legacy_engine)
    user_achievement_indexes = [
        index for index in inspector.get_indexes("user_achievements")
        if index["unique"] and index["column_names"] == ["user_id", "achievement_id"]
    ]
    coin_indexes = [
        index for index in inspector.get_indexes("coin_transactions")
        if index["unique"] and index["column_names"] == ["user_id", "source", "source_id"]
    ]
    with legacy_engine.connect() as connection:
        user_achievement_rows = connection.execute(text(
            "SELECT id FROM user_achievements"
        )).fetchall()
        transaction_rows = connection.execute(text(
            "SELECT amount, source_id FROM coin_transactions ORDER BY id"
        )).fetchall()

    assert user_achievement_rows == [("a-keeper-candidate",)]
    assert transaction_rows == [
        (50, "achievement-1"),
        (3, None),
        (4, None),
    ]
    assert len(user_achievement_indexes) == 1
    assert len(coin_indexes) == 1

    with pytest.raises(IntegrityError):
        with legacy_engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO user_achievements "
                "(id, user_id, achievement_id) VALUES "
                "('duplicate', :user_id, :achievement_id)"
            ), {"user_id": user_id, "achievement_id": achievement_id})

    with pytest.raises(IntegrityError):
        with legacy_engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO coin_transactions "
                "(user_id, amount, type, source, source_id) VALUES "
                "(:user_id, 50, 'earn', 'achievement', 'achievement-1')"
            ), {"user_id": user_id})

    legacy_engine.dispose()


def test_fresh_schema_has_one_reward_idempotency_definition(tmp_path):
    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'fresh-rewards.sqlite'}")
    Base.metadata.create_all(bind=fresh_engine)

    inspector = inspect(fresh_engine)
    user_achievement_definitions = [
        constraint for constraint in inspector.get_unique_constraints("user_achievements")
        if constraint["column_names"] == ["user_id", "achievement_id"]
    ] + [
        index for index in inspector.get_indexes("user_achievements")
        if index["unique"] and index["column_names"] == ["user_id", "achievement_id"]
    ]
    coin_definitions = [
        constraint for constraint in inspector.get_unique_constraints("coin_transactions")
        if constraint["column_names"] == ["user_id", "source", "source_id"]
    ] + [
        index for index in inspector.get_indexes("coin_transactions")
        if index["unique"] and index["column_names"] == ["user_id", "source", "source_id"]
    ]

    assert len(user_achievement_definitions) == 1
    assert len(coin_definitions) == 1
    fresh_engine.dispose()
