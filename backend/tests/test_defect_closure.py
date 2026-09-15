from tests.conftest import has_column, run_startup_migrations


def test_daily_summary_habit_contract_contains_server_state(client, auth_headers):
    response = client.get("/api/todos/daily", headers=auth_headers)
    assert response.status_code == 200
    habit = response.json()["habits"][0]
    assert habit["is_active"] is True
    assert habit["paused_today"] is False
    assert habit["scheduled_today"] is True


def test_purchase_idempotency_key_returns_one_exchange(client, auth_headers, shop_item):
    first = client.post(
        "/api/shop/exchange",
        headers={**auth_headers, "Idempotency-Key": "purchase-test-1"},
        json={"item_id": str(shop_item.id), "quantity": 1},
    )
    second = client.post(
        "/api/shop/exchange",
        headers={**auth_headers, "Idempotency-Key": "purchase-test-1"},
        json={"item_id": str(shop_item.id), "quantity": 1},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_startup_migration_is_repeatable(migration_database):
    run_startup_migrations(migration_database)
    run_startup_migrations(migration_database)
    assert has_column(migration_database, "users", "total_experience")
