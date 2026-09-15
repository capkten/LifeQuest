from datetime import date, datetime, timezone

from app.models.finance_transaction import FinanceTransaction
from app.models.todo import Habit
from app.models.coin_transaction import CoinSource, CoinTransaction, CoinType
from app.models.finance_category import CategoryType, FinanceCategory
from app.models.recurring_transaction import RecurringTransaction
from app.models.user import User
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


def test_coin_history_applies_source_and_date_filters_together(
    client, auth_headers, db_session, user,
):
    db_session.add_all([
        CoinTransaction(
            user_id=user.id,
            amount=4,
            type=CoinType.SPEND,
            source=CoinSource.SHOP,
            created_at=datetime(2026, 9, 14, 15, tzinfo=timezone.utc),
        ),
        CoinTransaction(
            user_id=user.id,
            amount=6,
            type=CoinType.SPEND,
            source=CoinSource.SHOP,
            created_at=datetime(2026, 9, 15, 15, tzinfo=timezone.utc),
        ),
        CoinTransaction(
            user_id=user.id,
            amount=8,
            type=CoinType.SPEND,
            source=CoinSource.TASK,
            created_at=datetime(2026, 9, 15, 15, tzinfo=timezone.utc),
        ),
    ])
    db_session.commit()

    response = client.get(
        "/api/coins/history",
        params={
            "coin_type": "spend",
            "source": "shop",
            "start_date": "2026-09-15T00:00:00Z",
            "end_date": "2026-09-15T23:59:59Z",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert [row["amount"] for row in response.json()["transactions"]] == [6]


def test_inactive_account_rejects_transaction_and_transfer(
    client, auth_headers, inactive_account, active_account,
):
    transaction = client.post(
        "/api/finance/transactions",
        headers=auth_headers,
        json={
            "account_id": str(inactive_account.id),
            "type": "expense",
            "amount": 1,
            "date": "2026-09-15",
        },
    )
    transfer = client.post(
        "/api/finance/accounts/transfer",
        headers=auth_headers,
        json={
            "from_account_id": str(inactive_account.id),
            "to_account_id": str(active_account.id),
            "amount": 1,
            "date": "2026-09-15",
        },
    )

    assert transaction.status_code == 409
    assert transaction.json()["detail"]["code"] == "ACCOUNT_INACTIVE"
    assert transfer.status_code == 409
    assert transfer.json()["detail"]["code"] == "ACCOUNT_INACTIVE"


def test_transaction_response_contains_account_and_category_names(
    client, auth_headers, transaction, db_session,
):
    category = FinanceCategory(
        user_id=transaction.user_id,
        name="测试支出分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    db_session.add(category)
    db_session.flush()
    transaction.category_id = category.id
    db_session.commit()

    response = client.get("/api/finance/transactions", headers=auth_headers)

    assert response.status_code == 200
    row = response.json()["items"][0]
    assert row["account_name"] == "测试账户"
    assert row["category_name"] == "测试支出分类"


def test_explicit_null_update_clears_optional_fields(
    client, auth_headers, goal, budget, db_session, user,
):
    category = FinanceCategory(
        user_id=user.id,
        name="预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    goal.description = "保留前的说明"
    goal.deadline = datetime(2026, 9, 20, 12, 0)
    budget.category_id = category.id
    budget.start_date = datetime(2026, 9, 1).date()
    user.avatar = "/uploads/avatars/old.png"
    db_session.add(category)
    db_session.commit()

    goal_response = client.put(
        f"/api/todos/goals/{goal.id}",
        headers=auth_headers,
        json={"description": None, "deadline": None},
    )
    budget_response = client.put(
        f"/api/finance/budgets/{budget.id}",
        headers=auth_headers,
        json={"category_id": None, "start_date": None},
    )
    user_response = client.put(
        "/api/users/me",
        headers=auth_headers,
        json={"avatar": None},
    )

    assert goal_response.status_code == 200
    assert goal_response.json()["description"] is None
    assert goal_response.json()["deadline"] is None
    assert budget_response.status_code == 200
    assert budget_response.json()["category_id"] is None
    assert budget_response.json()["start_date"] is None
    assert user_response.status_code == 200
    assert user_response.json()["avatar"] is None


def test_inactive_account_rejects_recurring_creation_without_mutation(
    client, auth_headers, inactive_account, db_session,
):
    inactive_account.balance = 100
    db_session.commit()

    response = client.post(
        "/api/finance/recurring",
        headers=auth_headers,
        json={
            "account_id": str(inactive_account.id),
            "type": "expense",
            "amount": 10,
            "frequency": "daily",
            "next_date": "2026-09-15",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACCOUNT_INACTIVE"
    db_session.refresh(inactive_account)
    assert inactive_account.balance == 100
    assert db_session.query(RecurringTransaction).count() == 0
    assert db_session.query(FinanceTransaction).count() == 0


def test_owner_can_list_inactive_accounts_for_reactivation(
    client, auth_headers, inactive_account, active_account,
):
    default_response = client.get("/api/finance/accounts", headers=auth_headers)
    managed_response = client.get(
        "/api/finance/accounts",
        params={"include_inactive": "true"},
        headers=auth_headers,
    )

    assert default_response.status_code == 200
    assert managed_response.status_code == 200
    assert str(inactive_account.id) not in {item["id"] for item in default_response.json()}
    assert {str(inactive_account.id), str(active_account.id)} <= {
        item["id"] for item in managed_response.json()
    }


def test_trigger_recurring_rejects_legacy_inactive_account_without_mutation(
    client, auth_headers, inactive_account, db_session,
):
    inactive_account.balance = 100
    recurring = RecurringTransaction(
        user_id=inactive_account.user_id,
        account_id=inactive_account.id,
        type="expense",
        amount=10,
        frequency="daily",
        next_date=date(2026, 9, 15),
    )
    db_session.add(recurring)
    db_session.commit()

    response = client.post(
        f"/api/finance/recurring/{recurring.id}/trigger",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACCOUNT_INACTIVE"
    db_session.refresh(inactive_account)
    db_session.refresh(recurring)
    assert inactive_account.balance == 100
    assert recurring.next_date == date(2026, 9, 15)
    assert db_session.query(FinanceTransaction).count() == 0


def test_trigger_recurring_rejects_legacy_category_type_mismatch_without_mutation(
    client, auth_headers, active_account, db_session,
):
    active_account.balance = 100
    category = FinanceCategory(
        user_id=active_account.user_id,
        name="收入分类",
        type=CategoryType.INCOME,
        is_system=False,
    )
    db_session.add(category)
    db_session.flush()
    recurring = RecurringTransaction(
        user_id=active_account.user_id,
        account_id=active_account.id,
        category_id=category.id,
        type="expense",
        amount=10,
        frequency="daily",
        next_date=date(2026, 9, 15),
    )
    db_session.add(recurring)
    db_session.commit()

    response = client.post(
        f"/api/finance/recurring/{recurring.id}/trigger",
        headers=auth_headers,
    )

    assert response.status_code == 422
    db_session.refresh(active_account)
    assert active_account.balance == 100
    assert db_session.query(FinanceTransaction).count() == 0


def test_trigger_recurring_rejects_legacy_foreign_category_without_mutation(
    client, auth_headers, active_account, db_session, user,
):
    active_account.balance = 100
    foreign_user = User(
        username="foreign-recurring-user",
        email="foreign-recurring@example.com",
        password_hash="not-used",
    )
    db_session.add(foreign_user)
    db_session.flush()
    category = FinanceCategory(
        user_id=foreign_user.id,
        name="他人分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    recurring = RecurringTransaction(
        user_id=user.id,
        account_id=active_account.id,
        category_id=category.id,
        type="expense",
        amount=10,
        frequency="daily",
        next_date=date(2026, 9, 15),
    )
    db_session.add(category)
    db_session.flush()
    recurring.category_id = category.id
    db_session.add(recurring)
    db_session.commit()

    response = client.post(
        f"/api/finance/recurring/{recurring.id}/trigger",
        headers=auth_headers,
    )

    assert response.status_code == 404
    db_session.refresh(active_account)
    assert active_account.balance == 100
    assert db_session.query(FinanceTransaction).count() == 0
