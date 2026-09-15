from sqlalchemy import inspect, text
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
