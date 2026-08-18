from uuid import UUID

from app.models.coin_transaction import CoinTransaction
def _register_and_login(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "regression-user",
            "email": "regression@example.com",
            "password": "testpassword123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": "regression-user", "password": "testpassword123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_first_goal_completion_records_base_and_achievement_rewards(client, db_session):
    headers = _register_and_login(client)
    goal_response = client.post(
        "/api/todos/goals",
        json={
            "title": "Regression goal",
            "difficulty": "hard",
            "coins_reward": 100,
            "exp_reward": 50,
        },
        headers=headers,
    )
    assert goal_response.status_code == 200
    goal_id = goal_response.json()["id"]

    before = client.get("/api/users/me", headers=headers).json()
    completion = client.post(f"/api/todos/goals/{goal_id}/complete", headers=headers)
    assert completion.status_code == 200

    after_first = client.get("/api/users/me", headers=headers).json()
    assert after_first["coins"] == before["coins"] + 150
    assert after_first["experience"] == before["experience"] + 50

    transactions = (
        db_session.query(CoinTransaction)
        .filter(CoinTransaction.user_id == UUID(before["id"]))
        .order_by(CoinTransaction.id)
        .all()
    )
    assert [(transaction.source, transaction.amount) for transaction in transactions] == [
        ("goal", 100),
        ("achievement", 50),
    ]

    second_completion = client.post(f"/api/todos/goals/{goal_id}/complete", headers=headers)
    assert second_completion.status_code == 200
    after_second = client.get("/api/users/me", headers=headers).json()
    assert after_second["coins"] == after_first["coins"]
    assert after_second["experience"] == after_first["experience"]


def test_checkin_response_reports_written_rewards_and_repeat_is_not_rewarded(client, db_session):
    headers = _register_and_login(client)

    first = client.post("/api/checkin", headers=headers)
    assert first.status_code == 200
    payload = first.json()
    assert payload["reward_coins"] > 0
    assert payload["reward_exp"] > 0

    user_id = UUID(client.get("/api/users/me", headers=headers).json()["id"])
    checkin_transactions = (
        db_session.query(CoinTransaction)
        .filter(
            CoinTransaction.user_id == user_id,
            CoinTransaction.source == "checkin",
        )
        .all()
    )
    assert len(checkin_transactions) == 1
    assert checkin_transactions[0].amount == payload["reward_coins"]

    repeat = client.post("/api/checkin", headers=headers)
    assert repeat.status_code == 400
    assert (
        db_session.query(CoinTransaction)
        .filter(
            CoinTransaction.user_id == user_id,
            CoinTransaction.source == "checkin",
        )
        .count()
        == 1
    )


def test_coin_history_returns_filtered_transactions_and_totals(client, db_session):
    headers = _register_and_login(client)
    checkin = client.post("/api/checkin", headers=headers)
    assert checkin.status_code == 200

    user_id = UUID(client.get("/api/users/me", headers=headers).json()["id"])
    from app.models.coin_transaction import CoinSource, CoinType
    from app.repositories.coin_transaction import CoinTransactionRepository

    CoinTransactionRepository(db_session).create_transaction(
        user_id=user_id,
        amount=7,
        coin_type=CoinType.SPEND,
        source=CoinSource.SHOP,
        description="test spend",
    )

    earned = client.get("/api/coins/history?coin_type=earn", headers=headers)
    spent = client.get("/api/coins/history?coin_type=spend", headers=headers)

    assert earned.status_code == 200
    assert spent.status_code == 200
    assert earned.json()["transactions"]
    assert all(item["type"] == "earn" for item in earned.json()["transactions"])
    assert earned.json()["total_earned"] == checkin.json()["reward_coins"]
    assert spent.json()["transactions"][0]["type"] == "spend"
    assert spent.json()["total_spent"] == 7
    assert spent.json()["count"] == 1
