import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError
from tests.conftest import run_startup_migrations


def _replace_tribulation_attempt_table(connection, *, unique_index=False):
    connection.exec_driver_sql("DROP TABLE tribulation_attempts")
    connection.exec_driver_sql(
        "CREATE TABLE tribulation_attempts ("
        "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
        "attempted_date DATE, attempted_at DATETIME)"
    )
    if unique_index:
        connection.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_tribulation_attempt_user_day "
            "ON tribulation_attempts (user_id, attempted_date)"
        )


def test_tribulation_date_repair_keeps_recoverable_collision_survivor(
    migration_database,
):
    from app.main import _deduplicate_tribulation_attempts

    connection = migration_database.connection()
    _replace_tribulation_attempt_table(connection)
    connection.execute(
        text(
            "INSERT INTO tribulation_attempts "
            "(id, user_id, attempted_date, attempted_at) VALUES "
            "('unknown-time', 'legacy-user', '2026-09-16', NULL), "
            "('known-time', 'legacy-user', '2026-09-15', '2026-09-15 16:00:00')"
        )
    )

    _deduplicate_tribulation_attempts(connection)

    rows = connection.execute(
        text(
            "SELECT id, attempted_date FROM tribulation_attempts ORDER BY id"
        )
    ).all()
    assert rows == [("known-time", "2026-09-16")]


def test_startup_migration_preserves_existing_unique_guard_on_unknown_collision(
    migration_database,
):
    connection = migration_database.connection()
    _replace_tribulation_attempt_table(connection, unique_index=True)
    connection.execute(
        text(
            "INSERT INTO tribulation_attempts "
            "(id, user_id, attempted_date, attempted_at) VALUES "
            "('unknown-time', 'legacy-user', '2026-09-16', NULL), "
            "('known-time', 'legacy-user', '2026-09-15', '2026-09-15 16:00:00')"
        )
    )
    migration_database.commit()

    run_startup_migrations(migration_database)
    run_startup_migrations(migration_database)

    rows = migration_database.execute(
        text(
            "SELECT id, attempted_date FROM tribulation_attempts ORDER BY id"
        )
    ).all()
    indexes = inspect(migration_database.get_bind()).get_indexes(
        "tribulation_attempts"
    )
    assert rows == [("known-time", "2026-09-16")]
    assert any(
        index["name"] == "uq_tribulation_attempt_user_day" and index["unique"]
        for index in indexes
    )


def test_startup_migration_preserves_duplicate_unrepairable_attempts(
    migration_database,
):
    connection = migration_database.connection()
    _replace_tribulation_attempt_table(connection)
    connection.execute(
        text(
            "INSERT INTO tribulation_attempts "
            "(id, user_id, attempted_date, attempted_at) VALUES "
            "('unknown-a', 'legacy-user', '2026-09-16', NULL), "
            "('unknown-b', 'legacy-user', '2026-09-16', NULL)"
        )
    )
    migration_database.commit()

    run_startup_migrations(migration_database)

    rows = migration_database.execute(
        text(
            "SELECT id, attempted_date FROM tribulation_attempts ORDER BY id"
        )
    ).all()
    indexes = inspect(migration_database.get_bind()).get_indexes(
        "tribulation_attempts"
    )
    assert rows == [("unknown-b", "2026-09-16")]
    assert any(
        index["name"] == "uq_tribulation_attempt_user_day" and index["unique"]
        for index in indexes
    )


def test_startup_migration_backfills_cumulative_experience(
    migration_database,
):
    migration_database.execute(
        text("INSERT INTO users (id, username, email, password_hash, level, experience, coins) "
             "VALUES (:id, :username, :email, :password_hash, :level, :experience, :coins)"),
        {
            "id": "legacy-experience-user",
            "username": "legacy-experience-user",
            "email": "legacy-experience@example.com",
            "password_hash": "unused",
            "level": 3,
            "experience": 7,
            "coins": 0,
        },
    )
    migration_database.commit()

    run_startup_migrations(migration_database)

    value = migration_database.execute(
        text("SELECT total_experience FROM users WHERE username = :username"),
        {"username": "legacy-experience-user"},
    ).scalar_one()
    assert value == 257


def test_startup_migration_creates_refresh_tokens_and_exchange_guards(
    migration_database,
):
    run_startup_migrations(migration_database)
    inspector = inspect(migration_database.get_bind())
    assert inspector.has_table("refresh_tokens")
    columns = {column["name"] for column in inspector.get_columns("refresh_tokens")}
    assert columns == {
        "id",
        "user_id",
        "token_hash",
        "jti",
        "expires_at",
        "revoked_at",
        "replaced_by_id",
        "created_at",
    }
    exchange_columns = {
        column["name"]
        for column in inspector.get_columns("exchange_history")
    }
    assert {"idempotency_key", "item_name_snapshot", "unit_price_snapshot"}.issubset(
        exchange_columns
    )
    assert any(
        index.get("name") == "uq_exchange_history_user_idempotency_key"
        and index.get("unique")
        for index in inspector.get_indexes("exchange_history")
    )


def test_exchange_idempotency_guard_allows_legacy_null_keys(
    migration_database,
):
    run_startup_migrations(migration_database)
    values = {
        "user_id": "legacy-user",
        "item_id": "legacy-item",
        "quantity": 1,
        "total_cost": 1,
        "status": "completed",
    }
    for exchange_id in ("legacy-exchange-1", "legacy-exchange-2"):
        migration_database.execute(
            text("INSERT INTO exchange_history "
                 "(id, user_id, item_id, quantity, total_cost, status, idempotency_key) "
                 "VALUES (:id, :user_id, :item_id, :quantity, :total_cost, :status, NULL)"),
            {**values, "id": exchange_id},
        )
    migration_database.commit()

    migration_database.execute(
        text("INSERT INTO exchange_history "
             "(id, user_id, item_id, quantity, total_cost, status, idempotency_key) "
             "VALUES (:id, :user_id, :item_id, :quantity, :total_cost, :status, :key)"),
        {**values, "id": "legacy-exchange-3", "key": "one-key"},
    )
    migration_database.commit()
    try:
        migration_database.execute(
            text("INSERT INTO exchange_history "
                 "(id, user_id, item_id, quantity, total_cost, status, idempotency_key) "
                 "VALUES (:id, :user_id, :item_id, :quantity, :total_cost, :status, :key)"),
            {**values, "id": "legacy-exchange-4", "key": "one-key"},
        )
        migration_database.commit()
    except IntegrityError:
        migration_database.rollback()
    else:
        raise AssertionError("duplicate non-null idempotency keys must be rejected")


def test_weekly_target_habit_fixture_creates_a_weekly_target(
    client,
    db_session,
    user,
    create_weekly_target_habit,
):
    habit = create_weekly_target_habit(db_session, user.id, weekly_target=4)

    assert habit.frequency == "weekly_target"
    assert habit.weekly_target == 4


def test_startup_migration_uses_the_supplied_database(database):
    database.execute(text("ALTER TABLE users DROP COLUMN total_experience"))
    database.commit()

    run_startup_migrations(database)

    assert "total_experience" in {
        column["name"]
        for column in inspect(database.get_bind()).get_columns("users")
    }


def test_tribulation_dates_are_repaired_to_china_days_before_unique_guard(
    migration_database,
):
    attempts = [
        ("older", "2026-09-14", "2026-09-14 16:00:00"),
        ("latest", "2026-09-15", "2026-09-15 15:59:59"),
        ("after-boundary", "2026-09-17", "2026-09-15 16:00:00"),
    ]
    for attempt_id, stored_date, attempted_at in attempts:
        migration_database.execute(
            text(
                "INSERT INTO tribulation_attempts "
                "(id, user_id, target_realm, base_probability, readiness_score, "
                "pill_bonus, final_probability, roll, success, cultivation_loss, "
                "attempted_date, attempted_at) "
                "VALUES (:id, 'legacy-user', 'foundation', 50, 50, 0, 50, 1, 0, 0, "
                ":attempted_date, :attempted_at)"
            ),
            {
                "id": attempt_id,
                "attempted_date": stored_date,
                "attempted_at": attempted_at,
            },
        )
    migration_database.commit()

    run_startup_migrations(migration_database)
    run_startup_migrations(migration_database)

    rows = migration_database.execute(
        text(
            "SELECT id, attempted_date FROM tribulation_attempts "
            "ORDER BY attempted_date, id"
        )
    ).all()
    assert rows == [("latest", "2026-09-15"), ("after-boundary", "2026-09-16")]
    assert any(
        constraint.get("column_names") == ["user_id", "attempted_date"]
        for constraint in inspect(migration_database.get_bind()).get_unique_constraints(
            "tribulation_attempts"
        )
    )


def test_exchange_history_migration_backfills_only_provable_snapshots(
    migration_database,
):
    migration_database.execute(
        text(
            "INSERT INTO shop_items (id, name, coin_price, is_active) "
            "VALUES ('legacy-item', 'Original item', 40, 1)"
        )
    )
    for exchange_id, item_id, quantity, total_cost in (
        ("known", "legacy-item", 2, 80),
        ("non-integral", "legacy-item", 2, 41),
        ("missing", "unavailable-item", 3, 10),
    ):
        migration_database.execute(
            text(
                "INSERT INTO exchange_history "
                "(id, user_id, item_id, quantity, total_cost, status) "
                "VALUES (:id, 'legacy-user', :item_id, :quantity, :total_cost, 'completed')"
            ),
            {
                "id": exchange_id,
                "item_id": item_id,
                "quantity": quantity,
                "total_cost": total_cost,
            },
        )
    migration_database.commit()

    run_startup_migrations(migration_database)
    migration_database.execute(
        text("UPDATE shop_items SET name = 'Renamed item', coin_price = 99, is_active = 0")
    )
    migration_database.commit()
    run_startup_migrations(migration_database)

    rows = migration_database.execute(
        text(
            "SELECT id, item_name_snapshot, unit_price_snapshot "
            "FROM exchange_history ORDER BY id"
        )
    ).all()
    assert rows == [
        ("known", "Original item", 40),
        ("missing", "未知商品", None),
        ("non-integral", "Original item", None),
    ]


def test_missing_exchange_item_stays_unknown_after_catalog_item_appears(
    migration_database,
):
    migration_database.execute(
        text(
            "INSERT INTO exchange_history "
            "(id, user_id, item_id, quantity, total_cost, status) "
            "VALUES ('missing-item', 'legacy-user', 'later-item', 2, 40, 'completed')"
        )
    )
    migration_database.commit()

    run_startup_migrations(migration_database)
    migration_database.execute(
        text(
            "INSERT INTO shop_items (id, name, coin_price, is_active) "
            "VALUES ('later-item', 'Added later', 25, 1)"
        )
    )
    migration_database.commit()
    run_startup_migrations(migration_database)

    snapshot = migration_database.execute(
        text(
            "SELECT item_name_snapshot, unit_price_snapshot "
            "FROM exchange_history WHERE id = 'missing-item'"
        )
    ).one()
    assert snapshot == ("未知商品", 20)


def test_startup_migration_rolls_back_foundation_changes_on_failure(
    migration_database,
):
    migration_engine = migration_database.get_bind()

    def fail_during_exchange_snapshot_ddl(
        _connection,
        _cursor,
        statement,
        _parameters,
        _context,
        _executemany,
    ):
        if "ALTER TABLE exchange_history ADD COLUMN unit_price_snapshot" in statement:
            raise RuntimeError("injected foundation migration failure")

    event.listen(migration_engine, "before_cursor_execute", fail_during_exchange_snapshot_ddl)
    try:
        with pytest.raises(RuntimeError, match="injected foundation migration failure"):
            run_startup_migrations(migration_database)
    finally:
        event.remove(migration_engine, "before_cursor_execute", fail_during_exchange_snapshot_ddl)

    assert not inspect(migration_engine).has_table("refresh_tokens")
    assert "total_experience" not in {
        column["name"]
        for column in inspect(migration_engine).get_columns("users")
    }
    exchange_columns = {
        column["name"]
        for column in inspect(migration_engine).get_columns("exchange_history")
    }
    assert not {
        "idempotency_key",
        "item_name_snapshot",
        "unit_price_snapshot",
    }.intersection(exchange_columns)
