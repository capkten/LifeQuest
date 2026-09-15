import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.exc import IntegrityError
from tests.conftest import run_startup_migrations


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
