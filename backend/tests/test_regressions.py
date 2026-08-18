from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.cultivation import CultivationLog, CultivationProfile
from app.models.todo import Goal, Habit, Task
from app.models.user import User
from app.services.todo import TodoService

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


def test_todo_coin_sources_are_unique_for_repeated_completion(client, db_session):
    headers = _register_and_login(client)
    task = client.post(
        "/api/todos/tasks",
        json={"title": "Unique reward", "coins_reward": 12, "exp_reward": 4},
        headers=headers,
    ).json()
    user_id = UUID(client.get("/api/users/me", headers=headers).json()["id"])

    assert client.post(f"/api/todos/tasks/{task['id']}/complete", headers=headers).status_code == 200
    assert client.post(f"/api/todos/tasks/{task['id']}/complete", headers=headers).status_code == 200

    rows = db_session.query(CoinTransaction).filter(
        CoinTransaction.user_id == user_id,
        CoinTransaction.source == "task",
    ).all()
    assert len(rows) == 1
    assert rows[0].source_id

    duplicate = CoinTransaction(
        user_id=user_id,
        amount=12,
        type="earn",
        source="task",
        source_id=rows[0].source_id,
        description="duplicate source probe",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_concurrent_task_habit_goal_completion_settles_each_source_once(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'completion-concurrency.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    setup = SessionLocal()
    try:
        user = User(
            username="concurrent-user",
            email="concurrent@example.com",
            password_hash="not-used",
        )
        setup.add(user)
        setup.flush()
        setup.add(CultivationProfile(user_id=user.id))
        task = Task(user_id=user.id, title="Concurrent task", coins_reward=11, exp_reward=3)
        habit = Habit(user_id=user.id, title="Concurrent habit", coins_reward=13, exp_reward=4)
        goal = Goal(user_id=user.id, title="Concurrent goal", coins_reward=17, exp_reward=5)
        setup.add_all([task, habit, goal])
        setup.commit()
        user_id = user.id
        ids = {"task": task.id, "habit": habit.id, "goal": goal.id}
    finally:
        setup.close()

    def complete(kind):
        db = SessionLocal()
        try:
            service = TodoService(db)
            model = {"task": Task, "habit": Habit, "goal": Goal}[kind]
            item = db.query(model).filter(model.id == ids[kind]).one()
            return getattr(service, f"complete_{kind}")(item, user_id)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(complete, kind) for kind in ("task", "habit", "goal") for _ in range(2)]
        results = [future.result() for future in futures]

    assert len(results) == 6
    verify = SessionLocal()
    try:
        transactions = verify.query(CoinTransaction).filter(
            CoinTransaction.user_id == user_id,
            CoinTransaction.source.in_(["task", "habit", "goal"]),
        ).all()
        logs = verify.query(CultivationLog).filter(CultivationLog.user_id == user_id).all()
        assert {transaction.source for transaction in transactions} == {"task", "habit", "goal"}
        assert len(transactions) == 3
        assert {log.source for log in logs} == {"task", "habit", "goal"}
        assert len(logs) == 3
    finally:
        verify.close()
        Base.metadata.drop_all(bind=engine)
