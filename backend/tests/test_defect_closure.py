from app.models.todo import Habit
from app.models.coin_transaction import CoinSource, CoinTransaction, CoinType
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
    assert row["pause_intervals"] == []
    assert row["leave_intervals"] == []

    paused = client.post(f"/api/todos/habits/{habit.id}/pause", headers=auth_headers)
    assert paused.status_code == 200
    assert paused.json()["is_active"] is False
    assert paused.json()["paused_today"] is True
    assert paused.json()["scheduled_today"] is False
    assert paused.json()["excused_today"] is False
    assert len(paused.json()["pause_intervals"]) == 1
    assert paused.json()["pause_intervals"][0]["resumed_on"] is None
    assert paused.json()["leave_intervals"] == []

    resumed = client.post(f"/api/todos/habits/{habit.id}/resume", headers=auth_headers)
    assert resumed.status_code == 200
    assert resumed.json()["is_active"] is True
    assert resumed.json()["paused_today"] is False
    assert resumed.json()["scheduled_today"] is True
    assert resumed.json()["excused_today"] is False
    assert resumed.json()["pause_intervals"][0]["resumed_on"] is not None
    resumed_daily = client.get("/api/todos/daily", headers=auth_headers).json()
    resumed_row = next(item for item in resumed_daily["habits"] if item["id"] == str(habit.id))
    assert resumed_row["pause_intervals"] == resumed.json()["pause_intervals"]
    assert resumed_row["leave_intervals"] == []


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


def test_coin_history_filters_and_returns_transactions_key(
    client, auth_headers, db_session, coin_rows, user,
):
    db_session.add_all([
        CoinTransaction(
            user_id=user.id,
            amount=10,
            type=CoinType.EARN,
            source=CoinSource.TASK,
            description="earned",
        ),
        CoinTransaction(
            user_id=user.id,
            amount=3,
            type=CoinType.SPEND,
            source=CoinSource.SHOP,
            description="first spend",
        ),
        CoinTransaction(
            user_id=user.id,
            amount=5,
            type=CoinType.SPEND,
            source=CoinSource.SHOP,
            description="second spend",
        ),
    ])
    db_session.commit()
    assert len(coin_rows()) == 3

    response = client.get(
        "/api/coins/history",
        params={"coin_type": "spend", "skip": 1, "limit": 1},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert set(response.json()) >= {"transactions", "total_earned", "total_spent", "count"}
    assert len(response.json()["transactions"]) == 1
    assert response.json()["transactions"][0]["type"] == "spend"
    assert response.json()["total_earned"] == 10
    assert response.json()["total_spent"] == 8
    assert response.json()["count"] == 2


def test_coin_history_rejects_unknown_direction(client, auth_headers):
    response = client.get(
        "/api/coins/history",
        params={"coin_type": "invalid"},
        headers=auth_headers,
    )

    assert response.status_code == 422
