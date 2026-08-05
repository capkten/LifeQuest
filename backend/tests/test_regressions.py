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
