from app.models.todo import Habit
from tests.conftest import has_column, run_startup_migrations


def test_daily_summary_preserves_active_and_schedule_state(
    client, auth_headers, db_session,
):
    habit = db_session.query(Habit).one()
    response = client.get("/api/todos/daily", headers=auth_headers)
    assert response.status_code == 200
    row = next(item for item in response.json()["habits"] if item["id"] == str(habit.id))
    assert row["is_active"] is True
    assert row["paused_today"] is False
    assert row["scheduled_today"] is True
    assert row["excused_today"] is False

    paused = client.post(f"/api/todos/habits/{habit.id}/pause", headers=auth_headers)
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False
    assert paused.json()["paused_today"] is True
    assert paused.json()["scheduled_today"] is False
    assert paused.json()["excused_today"] is False

    resumed = client.post(f"/api/todos/habits/{habit.id}/resume", headers=auth_headers)
    assert resumed.status_code == 200
    assert resumed.json()["is_active"] is True
    assert resumed.json()["paused_today"] is False
    assert resumed.json()["scheduled_today"] is True
    assert resumed.json()["excused_today"] is False


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
