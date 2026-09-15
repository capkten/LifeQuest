from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.account import Account
from app.models.backpack import BackpackItem, ItemStatus, UsageAction, UsageHistory
from app.models.coin_transaction import CoinTransaction, CoinSource, CoinType
from app.models.cultivation import CultivationLog
from app.models.habit_completion import HabitCompletion
from app.models.habit_pause import HabitPauseInterval
from app.models.project import Project, ProjectPhase, ProjectMilestone
from app.models.shop import ShopItem, ExchangeHistory
from app.models.todo import Goal, Habit, Task, TaskStatus
from app.models.user import User
from app.models.finance_transaction import FinanceTransaction
from app.models.finance_daily_reward import FinanceDailyRewardClaim
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.finance import RecurringCreate, TransactionCreate, TransactionUpdate
from app.schemas.shop import ExchangeHistoryCreate
from app.schemas.todo import TaskCreate, TaskUpdate
from app.services.auth import create_access_token
from app.services.backpack import BackpackService
from app.services.calendar import CalendarService
from app.services.checkin import CheckinService
from app.services.cultivation import CultivationService
from app.services.finance import FinanceService
from app.services.habit_history import backfill_latest_completions
from app.services.project import ProjectService
from app.services.shop import ShopService
from app.services.stats import StatsService
from app.services.todo import TodoService
from app.repositories.user import UserRepository
from app.repositories.project import ProjectRepository, PhaseRepository, MilestoneRepository
from app.repositories.shop import ShopItemRepository


@pytest.fixture
def database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit.sqlite'}", connect_args={"timeout": 30})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    with factory() as session:
        yield session, factory
    engine.dispose()


@pytest.fixture
def clock(monkeypatch):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant[0].astimezone(tz) if tz else instant[0].replace(tzinfo=None)

    for module in ("app.timezone", "app.services.todo", "app.services.stats", "app.models.todo"):
        monkeypatch.setattr(f"{module}.datetime", FrozenDatetime)

    def set_time(value):
        instant[0] = value

    return set_time


def make_user(session, coins=100):
    name = uuid4().hex
    user = User(username=name, email=f"{name}@example.com", password_hash="unused", coins=coins)
    session.add(user)
    session.commit()
    return user


def make_item(session, user, stock=5):
    item = ShopItem(name="商品", created_by=user.id, coin_price=10, stock=stock)
    session.add(item)
    session.commit()
    return item


def purchase(session, user_id, item_id, quantity=1):
    return ShopService(session).purchase_item(user_id, ExchangeHistoryCreate(item_id=item_id, quantity=quantity))


@pytest.mark.parametrize("operation", ["create", "update"])
def test_task_api_rejects_foreign_project(client, db_session, operation):
    user, owner = make_user(db_session), make_user(db_session)
    project = Project(user_id=owner.id, name="私有项目")
    db_session.add(project)
    db_session.commit()
    headers = {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}
    if operation == "create":
        response = client.post("/api/todos/tasks", headers=headers,
                               json={"title": "任务", "project_id": str(project.id)})
    else:
        task = client.post("/api/todos/tasks", headers=headers, json={"title": "任务"}).json()
        response = client.put(f"/api/todos/tasks/{task['id']}", headers=headers,
                              json={"project_id": str(project.id)})
    assert response.status_code == 403
    assert db_session.query(Task).filter_by(project_id=project.id).count() == 0


def test_legacy_foreign_project_tasks_are_hidden_from_project_reads(client, db_session):
    owner, other = make_user(db_session), make_user(db_session)
    project = Project(user_id=owner.id, name="私有项目")
    db_session.add(project)
    db_session.flush()
    db_session.add(Task(
        user_id=other.id,
        project_id=project.id,
        title="不属于项目所有者的旧任务",
        status=TaskStatus.COMPLETED,
    ))
    db_session.commit()

    service = ProjectService(db_session)
    detail = service.get_project_detail(project.id, owner.id)
    assert detail["tasks"] == []
    assert detail["total_tasks"] == 0
    assert detail["completed_tasks"] == 0
    assert detail["progress"] == 0.0
    assert service.get_project_tasks(project.id, owner.id) == []

    auth = {"Authorization": "Bearer " + create_access_token({"sub": str(owner.id)})}
    listed = client.get("/api/projects", headers=auth)
    assert listed.status_code == 200
    assert listed.json()[0]["total_tasks"] == 0
    project_tasks = client.get(f"/api/projects/{project.id}/tasks", headers=auth)
    assert project_tasks.status_code == 200
    assert project_tasks.json() == []


@pytest.mark.parametrize(
    ("resource_name", "task_field"),
    [
        ("project", "project_id"),
        ("phase", "phase_id"),
        ("milestone", "milestone_id"),
    ],
)
def test_project_deletion_refuses_foreign_task_links(database, resource_name, task_field):
    session, factory = database
    owner, other = make_user(session), make_user(session)
    project = Project(user_id=owner.id, name="项目")
    session.add(project)
    session.flush()
    phase = ProjectPhase(project_id=project.id, name="阶段")
    milestone = ProjectMilestone(project_id=project.id, name="里程碑")
    session.add_all([phase, milestone])
    session.flush()
    target = {
        "project": project,
        "phase": phase,
        "milestone": milestone,
    }[resource_name]
    foreign_task = Task(
        user_id=other.id,
        title="其他用户的历史任务",
        **{task_field: target.id},
    )
    session.add(foreign_task)
    session.commit()

    with pytest.raises(HTTPException) as error:
        getattr(ProjectService(session), f"delete_{resource_name}")(target)

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "PROJECT_RESOURCE_HAS_FOREIGN_TASKS"
    session.refresh(foreign_task)
    assert getattr(foreign_task, task_field) == target.id
    assert session.get(type(target), target.id) is not None


def test_user_lock_uses_a_row_lock_instead_of_affected_rows():
    calls = []

    class Result:
        rowcount = 0

        def scalar_one_or_none(self):
            return uuid4()

    class Session:
        bind = type("Bind", (), {
            "dialect": type("Dialect", (), {"name": "mysql"})(),
        })()

        def execute(self, statement):
            calls.append(statement)
            return Result()

    UserRepository(Session()).lock(uuid4())

    assert len(calls) == 1
    assert calls[0]._for_update_arg is not None


def test_debit_coins_rejects_negative_amount_without_crediting_user(database):
    session, factory = database
    user = make_user(session)
    repository = UserRepository(session)

    repository.debit_coins(user.id, 0)
    with pytest.raises(ValueError):
        repository.debit_coins(user.id, -5)

    session.refresh(user)
    assert user.coins == 100


@pytest.mark.parametrize("field,model", [("phase_id", ProjectPhase), ("milestone_id", ProjectMilestone)])
def test_task_associations_require_matching_project(database, field, model):
    session, factory = database
    user = make_user(session)
    projects = [Project(user_id=user.id, name=name) for name in ("一", "二")]
    session.add_all(projects)
    session.flush()
    child = model(project_id=projects[0].id, name="节点")
    session.add(child)
    session.commit()
    for project_id in (None, projects[1].id):
        with pytest.raises(HTTPException):
            TodoService(session).create_task(user.id, TaskCreate(
                title="非法关联", project_id=project_id, **{field: child.id},
            ))
    task = TodoService(session).create_task(user.id, TaskCreate(
        title="合法关联", project_id=projects[0].id, **{field: child.id},
    ))
    moved = ProjectService(session).move_task(task, user.id, project_id=projects[1].id)
    assert moved.project_id == projects[1].id
    assert getattr(moved, field) is None
    cleared = ProjectService(session).move_task(
        task,
        user.id,
        project_id=None,
        phase_id=None,
        milestone_id=None,
    )
    assert cleared.project_id is None
    assert cleared.phase_id is None
    assert cleared.milestone_id is None
    with pytest.raises(HTTPException):
        TodoService(session).update_task(task, TaskUpdate(**{field: uuid4()}))


def test_project_task_validation_locks_parent_chain_after_user(database, monkeypatch):
    session, factory = database
    user = make_user(session)
    project = Project(user_id=user.id, name="项目")
    session.add(project)
    session.flush()
    phase = ProjectPhase(project_id=project.id, name="阶段")
    milestone = ProjectMilestone(project_id=project.id, name="里程碑")
    session.add_all([phase, milestone])
    session.commit()

    calls = []
    original_user_lock = UserRepository.lock
    original_project_lock = ProjectRepository.get_for_update
    original_phase_lock = PhaseRepository.get_for_update
    original_milestone_lock = MilestoneRepository.get_for_update

    def record_user_lock(repository, user_id):
        calls.append("user")
        return original_user_lock(repository, user_id)

    def record_project_lock(repository, project_id):
        calls.append("project")
        return original_project_lock(repository, project_id)

    def record_phase_lock(repository, phase_id):
        calls.append("phase")
        return original_phase_lock(repository, phase_id)

    def record_milestone_lock(repository, milestone_id):
        calls.append("milestone")
        return original_milestone_lock(repository, milestone_id)

    monkeypatch.setattr(UserRepository, "lock", record_user_lock)
    monkeypatch.setattr(ProjectRepository, "get_for_update", record_project_lock)
    monkeypatch.setattr(PhaseRepository, "get_for_update", record_phase_lock)
    monkeypatch.setattr(MilestoneRepository, "get_for_update", record_milestone_lock)

    TodoService(session).create_task(user.id, TaskCreate(
        title="按层级锁定",
        project_id=project.id,
        phase_id=phase.id,
        milestone_id=milestone.id,
    ))

    assert calls[:4] == ["user", "project", "phase", "milestone"]


def test_habit_history_only_marks_valid_scheduled_completions(database, clock):
    session, factory = database
    user = make_user(session)
    habit = Habit(
        user_id=user.id,
        title="周一习惯",
        frequency="weekdays",
        weekdays=[0],
        created_at=datetime(2026, 9, 1, 0, tzinfo=timezone.utc),
    )
    session.add(habit)
    session.flush()
    session.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=date(2026, 9, 6),
            completed_at=datetime(2026, 9, 6, 4),
        ),
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=date(2026, 9, 7),
            completed_at=datetime(2026, 9, 7, 4),
        ),
    ])
    session.add(HabitPauseInterval(
        habit_id=habit.id,
        user_id=user.id,
        paused_on=date(2026, 9, 12),
        resumed_on=date(2026, 9, 21),
    ))
    session.commit()

    history = TodoService(session).get_habit_history(
        habit.id,
        user.id,
        start_on=date(2026, 9, 6),
        end_on=date(2026, 9, 12),
    )
    days = {item["date"]: item for item in history["days"]}

    assert days[date(2026, 9, 6)]["scheduled"] is False
    assert days[date(2026, 9, 6)]["completed"] is False
    assert days[date(2026, 9, 6)]["completion_id"] is None
    assert days[date(2026, 9, 7)]["scheduled"] is True
    assert days[date(2026, 9, 7)]["completed"] is True
    assert days[date(2026, 9, 12)]["paused"] is True
    assert days[date(2026, 9, 12)]["completed"] is False


def test_habit_stats_total_is_scheduled_slots_not_active_habits(database, clock):
    session, factory = database
    user = make_user(session)
    daily = Habit(
        user_id=user.id,
        title="每日",
        frequency="daily",
        created_at=datetime(2026, 9, 1, 0, tzinfo=timezone.utc),
    )
    monday = Habit(user_id=user.id, title="周一", frequency="weekly")
    monday.created_at = datetime(2026, 9, 1, 0, tzinfo=timezone.utc)
    session.add_all([daily, monday])
    session.commit()

    stats = StatsService(session).get_habit_stats(user.id, "week")
    saturday = next(item for item in stats if item["date"] == "2026-09-12")
    monday_stat = next(item for item in stats if item["date"] == "2026-09-07")

    assert saturday["total"] == 1
    assert monday_stat["total"] == 2


def test_experience_rewards_update_current_and_cumulative_totals(database):
    session, factory = database
    user = make_user(session)
    repository = UserRepository(session)

    repository._update_experience_no_commit(user, 125)
    session.commit()
    session.refresh(user)

    assert user.level == 2
    assert user.experience == 25
    assert user.total_experience == 125


def test_finance_first_transaction_bonus_survives_transaction_deletion(database):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user)
    service = FinanceService(session)

    first = service.create_transaction(user.id, TransactionCreate(
        account_id=account.id,
        amount=Decimal("10.00"),
        type="expense",
        date=date(2026, 9, 12),
    ))
    session.refresh(user)
    first_experience = user.experience
    service.delete_transaction(first)
    recreated = service.create_transaction(user.id, TransactionCreate(
        account_id=account.id,
        amount=Decimal("10.00"),
        type="expense",
        date=date(2026, 9, 12),
    ))

    session.refresh(user)
    assert user.experience == first_experience + 2
    assert session.query(FinanceDailyRewardClaim).filter_by(
        user_id=user.id,
    ).count() == 1
    assert recreated is not None


def test_finance_first_transaction_bonus_uses_transaction_date(database, clock):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user)
    service = FinanceService(session)

    historical = service.create_transaction(user.id, TransactionCreate(
        account_id=account.id,
        amount=Decimal("10.00"),
        type="expense",
        date=date(2026, 9, 11),
    ))
    session.refresh(user)

    assert historical.date == date(2026, 9, 11)
    assert user.experience == 7
    assert session.query(FinanceDailyRewardClaim).filter_by(
        user_id=user.id,
        reward_date=date(2026, 9, 11),
    ).count() == 1

    service.create_transaction(user.id, TransactionCreate(
        account_id=account.id,
        amount=Decimal("10.00"),
        type="expense",
        date=date(2026, 9, 12),
    ))
    session.refresh(user)

    assert user.experience == 14
    assert session.query(FinanceDailyRewardClaim).filter_by(
        user_id=user.id,
        reward_date=date(2026, 9, 12),
    ).count() == 1


def test_move_endpoint_can_explicitly_clear_project_associations(client, db_session):
    user = make_user(db_session)
    project = Project(user_id=user.id, name="项目")
    db_session.add(project)
    db_session.flush()
    phase = ProjectPhase(project_id=project.id, name="阶段")
    milestone = ProjectMilestone(project_id=project.id, name="里程碑")
    db_session.add_all([phase, milestone])
    db_session.commit()
    task = TodoService(db_session).create_task(user.id, TaskCreate(
        title="待解绑",
        project_id=project.id,
        phase_id=phase.id,
        milestone_id=milestone.id,
    ))

    response = client.put(
        f"/api/projects/tasks/{task.id}/move",
        headers={"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})},
        json={"project_id": None, "phase_id": None, "milestone_id": None},
    )

    assert response.status_code == 200
    assert response.json()["project_id"] is None
    assert response.json()["phase_id"] is None
    assert response.json()["milestone_id"] is None
    db_session.refresh(task)
    assert task.project_id is None
    assert task.phase_id is None
    assert task.milestone_id is None


def test_milestone_due_date_can_be_cleared(client, db_session):
    user = make_user(db_session)
    project = Project(user_id=user.id, name="项目")
    db_session.add(project)
    db_session.flush()
    milestone = ProjectMilestone(
        project_id=project.id,
        name="有日期的里程碑",
        due_date=date(2026, 9, 20),
    )
    db_session.add(milestone)
    db_session.commit()

    response = client.put(
        f"/api/projects/milestones/{milestone.id}",
        headers={"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})},
        json={"due_date": None},
    )

    assert response.status_code == 200
    assert response.json()["due_date"] is None
    db_session.refresh(milestone)
    assert milestone.due_date is None


@pytest.mark.parametrize("entry", ["project", "update", "complete"])
def test_task_completion_rewards_are_shared_and_idempotent(database, entry):
    session, factory = database
    user = make_user(session)
    service = TodoService(session)
    task = service.create_task(user.id, TaskCreate(title="任务", coins_reward=10))
    if entry == "project":
        ProjectService(session).move_task(task, user.id, status=TaskStatus.COMPLETED)
    elif entry == "update":
        service.update_task(task, TaskUpdate(status=TaskStatus.COMPLETED, title="已更新"))
        assert task.title == "已更新"
    else:
        service.complete_task(task, user.id)
    session.refresh(user)
    coins = user.coins
    assert coins >= 110
    assert task.completed_at is not None
    service.complete_task(task, user.id)
    service.update_task(task, TaskUpdate(status=TaskStatus.PENDING))
    assert task.completed_at is None
    ProjectService(session).move_task(task, user.id, status=TaskStatus.COMPLETED)
    session.refresh(user)
    assert user.coins == coins
    assert session.query(CoinTransaction).filter_by(user_id=user.id, source="task").count() == 1


def test_task_completion_failure_rolls_back_status_and_rewards(database, monkeypatch):
    session, factory = database
    user = make_user(session)
    task = TodoService(session).create_task(user.id, TaskCreate(title="原名称"))

    def fail(*args, **kwargs):
        raise RuntimeError("settlement failed")

    monkeypatch.setattr(TodoService, "_check_achievements", fail)
    with pytest.raises(RuntimeError):
        TodoService(session).update_task(task, TaskUpdate(title="错误名称", status=TaskStatus.COMPLETED))
    session.refresh(task)
    session.refresh(user)
    assert task.status == TaskStatus.PENDING
    assert task.title == "原名称"
    assert task.completed_at is None
    assert user.coins == 100
    assert session.query(CoinTransaction).filter_by(user_id=user.id, source="task").count() == 0


@pytest.mark.parametrize(
    ("model", "method", "source"),
    [
        (Task, "complete_task", "task"),
        (Goal, "complete_goal", "goal"),
    ],
)
def test_cancelled_todos_cannot_be_completed_or_rewarded(database, model, method, source):
    session, factory = database
    user = make_user(session)
    todo = model(user_id=user.id, title="已取消", status=TaskStatus.CANCELLED)
    session.add(todo)
    session.commit()
    before = (user.coins, user.experience)

    with pytest.raises(HTTPException) as error:
        getattr(TodoService(session), method)(todo, user.id)

    assert error.value.status_code == 409
    session.refresh(todo)
    session.refresh(user)
    assert todo.status == TaskStatus.CANCELLED
    assert (user.coins, user.experience) == before
    assert session.query(CoinTransaction).filter_by(
        user_id=user.id, source=source,
    ).count() == 0
    assert session.query(CultivationLog).filter_by(
        user_id=user.id, source=source,
    ).count() == 0


def test_refund_returns_stock_and_removes_items_once(database):
    session, factory = database
    user = make_user(session)
    item = make_item(session, user)
    exchange = purchase(session, user.id, item.id, quantity=2)
    ShopService(session).refund_exchange(exchange)
    session.refresh(user)
    session.refresh(item)
    assert user.coins == 100
    assert item.stock == 5
    assert session.query(BackpackItem).filter_by(user_id=user.id).count() == 0
    history = session.query(UsageHistory).filter_by(action=UsageAction.REFUND).one()
    assert history.quantity == 2
    transactions = session.query(CoinTransaction).filter_by(
        user_id=user.id,
        source="shop",
    ).order_by(CoinTransaction.id).all()
    assert [(transaction.type, transaction.amount) for transaction in transactions] == [
        (CoinType.SPEND, 20),
        (CoinType.EARN, 20),
    ]
    assert transactions[0].source_id != transactions[1].source_id
    with pytest.raises(HTTPException):
        ShopService(session).refund_exchange(exchange)
    session.refresh(user)
    assert user.coins == 100


def test_consume_by_key_rolls_back_partial_mutation_inside_outer_transaction(database, monkeypatch):
    session, factory = database
    user = make_user(session)
    pill = ShopItem(
        item_key="tribulation-pill",
        name="渡劫丹",
        category="consumable",
        coin_price=100,
        stock=-1,
        is_active=True,
    )
    session.add(pill)
    session.commit()
    backpack_item = BackpackService(session).add_item(user.id, pill.id, quantity=2)

    def fail(*args, **kwargs):
        raise RuntimeError("history write failed")

    monkeypatch.setattr(BackpackService, "_log_history_no_commit", fail)
    with pytest.raises(RuntimeError):
        BackpackService(session).consume_by_key(user.id, "tribulation-pill", 1)

    session.commit()
    session.refresh(backpack_item)
    assert backpack_item.quantity == 2
    assert session.query(UsageHistory).filter_by(action=UsageAction.USE).count() == 0
    assert user.total_coins_earned == 0


@pytest.mark.parametrize("action", ["use", "discard", "equip"])
def test_refund_rejects_unavailable_items_without_partial_changes(database, action):
    session, factory = database
    user = make_user(session)
    item = make_item(session, user)
    exchange = purchase(session, user.id, item.id, quantity=2)
    backpack_item = session.query(BackpackItem).filter_by(user_id=user.id).one()
    service = BackpackService(session)
    if action == "equip":
        service.equip_item(backpack_item)
    else:
        getattr(service, f"{action}_item")(backpack_item, 1)
    with pytest.raises(HTTPException):
        ShopService(session).refund_exchange(exchange)
    session.refresh(user)
    session.refresh(item)
    session.refresh(exchange)
    assert user.coins == 80
    assert item.stock == 3
    assert exchange.status == "completed"
    assert session.query(UsageHistory).filter_by(action=UsageAction.REFUND).count() == 0
    remaining = session.query(BackpackItem).one()
    assert remaining.quantity == (2 if action == "equip" else 1)


def test_stale_session_cannot_refund_twice(database):
    session, factory = database
    user = make_user(session)
    item = make_item(session, user)
    exchange = purchase(session, user.id, item.id)
    with factory() as other:
        stale = other.get(ExchangeHistory, exchange.id)
        ShopService(session).refund_exchange(exchange)
        with pytest.raises(HTTPException):
            ShopService(other).refund_exchange(stale)
    session.refresh(user)
    assert user.coins == 100


def test_purchase_failure_restores_stock(database):
    session, factory = database
    user = make_user(session, coins=0)
    item = make_item(session, user)
    with pytest.raises(HTTPException):
        purchase(session, user.id, item.id)
    session.refresh(item)
    assert item.stock == 5
    assert session.query(ExchangeHistory).count() == 0
    assert session.query(BackpackItem).count() == 0


def test_purchase_reads_item_state_under_a_row_lock(database, monkeypatch):
    session, factory = database
    user = make_user(session)
    item = make_item(session, user)
    calls = []
    original = ShopItemRepository.get_for_update

    def record_lock(repository, item_id):
        calls.append(item_id)
        return original(repository, item_id)

    monkeypatch.setattr(ShopItemRepository, "get_for_update", record_lock)
    purchase(session, user.id, item.id)

    assert calls == [item.id]


def test_sequential_purchases_create_distinct_coin_source_ids(database):
    session, factory = database
    user = make_user(session)
    item = make_item(session, user, stock=5)

    first = purchase(session, user.id, item.id)
    second = purchase(session, user.id, item.id)
    transactions = session.query(CoinTransaction).filter_by(
        user_id=user.id,
        source=CoinSource.SHOP.value,
    ).order_by(CoinTransaction.id).all()

    assert [transaction.source_id for transaction in transactions] == [
        str(first.id),
        str(second.id),
    ]
    assert all(transaction.source_id for transaction in transactions)
    assert len({transaction.source_id for transaction in transactions}) == 2


def test_purchase_refresh_failure_rolls_back_the_entire_operation(database, monkeypatch):
    session, factory = database
    user = make_user(session)
    item = make_item(session, user)
    original_refresh = type(session).refresh

    def fail_exchange_refresh(current_session, instance, *args, **kwargs):
        if isinstance(instance, ExchangeHistory):
            raise RuntimeError("exchange refresh failed")
        return original_refresh(current_session, instance, *args, **kwargs)

    monkeypatch.setattr(type(session), "refresh", fail_exchange_refresh)
    with pytest.raises(RuntimeError):
        purchase(session, user.id, item.id)

    assert session.query(ExchangeHistory).count() == 0
    assert session.query(BackpackItem).count() == 0
    assert session.query(CoinTransaction).filter_by(source="shop").count() == 0
    session.refresh(user)
    session.refresh(item)
    assert user.coins == 100
    assert item.stock == 5


def test_parallel_purchases_cannot_overdraw(database):
    session, factory = database
    user = make_user(session, coins=10)
    item = make_item(session, user, stock=-1)
    user_id, item_id = user.id, item.id
    barrier = Barrier(2)

    def buy():
        with factory() as worker:
            cached_user = worker.get(User, user_id)
            assert cached_user.coins == 10
            barrier.wait(timeout=10)
            try:
                purchase(worker, user_id, item_id)
                return "success"
            except HTTPException as exc:
                assert exc.status_code == 400
                return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(buy) for attempt in range(2)]
        assert sorted(future.result(timeout=40) for future in futures) == ["rejected", "success"]
    session.refresh(user)
    assert user.coins == 0
    assert session.query(ExchangeHistory).count() == 1
    assert session.query(BackpackItem).one().quantity == 1


def make_account(session, user, balance=100):
    account = Account(user_id=user.id, name="账户", balance=balance)
    session.add(account)
    session.commit()
    return account


def expense(session, user_id, account_id, amount):
    return FinanceService(session).create_transaction(user_id, TransactionCreate(
        account_id=account_id, amount=amount, type="expense", date=date(2026, 9, 12),
    ))


def test_parallel_expenses_preserve_both_balance_changes(database):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user)
    user_id, account_id = user.id, account.id
    barrier = Barrier(2)

    def record(amount):
        with factory() as worker:
            cached = worker.get(Account, account_id)
            assert cached.balance == 100
            barrier.wait(timeout=10)
            expense(worker, user_id, account_id, amount)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(record, amount) for amount in (10, 20)]
        for future in futures:
            future.result(timeout=40)
    session.refresh(account)
    assert account.balance == 70
    assert session.query(FinanceTransaction).count() == 2


def test_parallel_task_entrypoints_share_one_settlement(database):
    session, factory = database
    user = make_user(session)
    task = TodoService(session).create_task(user.id, TaskCreate(title="任务"))
    task_id, user_id = task.id, user.id
    barrier = Barrier(2)

    def complete(entry):
        with factory() as worker:
            current = worker.get(Task, task_id)
            barrier.wait(timeout=10)
            if entry == "project":
                ProjectService(worker).move_task(current, user_id, status=TaskStatus.COMPLETED)
            else:
                TodoService(worker).complete_task(current, user_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(complete, entry) for entry in ("project", "todo")]
        for future in futures:
            future.result(timeout=40)
    session.refresh(task)
    assert task.status == TaskStatus.COMPLETED
    assert session.query(CoinTransaction).filter_by(user_id=user_id, source="task").count() == 1


def test_recurring_stale_retry_does_not_apply_balance_twice(database):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user)
    recurring = RecurringTransaction(user_id=user.id, account_id=account.id, type="expense",
                                     amount=10, frequency="daily", next_date=date(2026, 9, 12))
    session.add(recurring)
    session.commit()
    with factory() as other:
        stale = other.get(RecurringTransaction, recurring.id)
        original = FinanceService(session).trigger_recurring(recurring)
        retry = FinanceService(other).trigger_recurring(stale)
        assert original.id == retry.id
    session.refresh(account)
    assert account.balance == 90
    assert session.query(FinanceTransaction).count() == 1


def test_stale_transfer_cannot_overdraw_and_rolls_back(database):
    session, factory = database
    user = make_user(session)
    source, target = make_account(session, user), make_account(session, user, 0)
    with factory() as other:
        cached = other.get(Account, source.id)
        assert cached.balance == 100
        FinanceService(session).transfer(user.id, source.id, target.id, 80)
        with pytest.raises(HTTPException):
            FinanceService(other).transfer(user.id, source.id, target.id, 80)
    session.refresh(source)
    session.refresh(target)
    assert source.balance == 20
    assert target.balance == 80
    assert session.query(FinanceTransaction).count() == 1


def test_stale_transaction_update_and_delete_reverse_latest_amount(database):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user)
    transaction = expense(session, user.id, account.id, 10)
    with factory() as other:
        stale = other.get(FinanceTransaction, transaction.id)
        FinanceService(session).update_transaction(transaction, TransactionUpdate(amount=20), user.id)
        FinanceService(other).update_transaction(stale, TransactionUpdate(amount=30), user.id)
    session.refresh(account)
    assert account.balance == 70
    FinanceService(session).delete_transaction(transaction)
    session.refresh(account)
    assert account.balance == 100


def test_updating_transfer_beyond_source_balance_rolls_back_everything(database):
    session, factory = database
    user = make_user(session)
    source, target = make_account(session, user, 100), make_account(session, user, 0)
    created = FinanceService(session).transfer(user.id, source.id, target.id, 80)
    transaction = created["transaction"]

    with pytest.raises(HTTPException) as error:
        FinanceService(session).update_transaction(
            transaction,
            TransactionUpdate(amount=150),
            user.id,
        )

    assert error.value.status_code == 400
    session.refresh(source)
    session.refresh(target)
    session.refresh(transaction)
    assert source.balance == 20
    assert target.balance == 80
    assert transaction.amount == Decimal("80.00")
    assert transaction.type == "transfer"
    assert session.query(FinanceTransaction).count() == 1


def test_same_china_day_finance_reward_is_awarded_only_for_first_transaction(database, clock):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user, 100)
    service = FinanceService(session)

    expense(session, user.id, account.id, 10)
    session.refresh(user)
    first_experience = user.experience
    expense(session, user.id, account.id, 10)
    session.refresh(user)

    assert first_experience == 7
    assert user.experience == 9
    assert session.query(FinanceTransaction).filter_by(user_id=user.id, date=date(2026, 9, 12)).count() == 2


def test_non_transfer_transaction_rejects_target_account(database):
    session, factory = database
    user = make_user(session)
    other = make_user(session)
    account = make_account(session, user, 100)
    foreign_target = make_account(session, other, 100)

    with pytest.raises(HTTPException) as error:
        FinanceService(session).create_transaction(
            user.id,
            TransactionCreate(
                account_id=account.id,
                to_account_id=foreign_target.id,
                type="expense",
                amount=10,
                date=date(2026, 9, 12),
            ),
        )

    assert error.value.status_code == 400
    session.refresh(account)
    session.refresh(foreign_target)
    assert account.balance == 100
    assert foreign_target.balance == 100
    assert session.query(FinanceTransaction).count() == 0


def test_recurring_transfer_is_rejected_before_persistence(database):
    session, factory = database
    user = make_user(session)
    account = make_account(session, user, 100)

    with pytest.raises(HTTPException) as error:
        FinanceService(session).create_recurring(
            user.id,
            RecurringCreate(
                account_id=account.id,
                type="transfer",
                amount=10,
                frequency="daily",
                next_date=date(2026, 9, 12),
            ),
        )

    assert error.value.status_code == 400
    assert session.query(RecurringTransaction).count() == 0


def test_transfer_commit_failure_rolls_back_both_accounts(database, monkeypatch):
    session, factory = database
    user = make_user(session)
    source, target = make_account(session, user), make_account(session, user, 0)

    def fail():
        raise RuntimeError("commit failed")

    monkeypatch.setattr(session, "commit", fail)
    with pytest.raises(RuntimeError):
        FinanceService(session).transfer(user.id, source.id, target.id, Decimal("0.10"))
    session.refresh(source)
    session.refresh(target)
    assert source.balance == 100
    assert target.balance == 0
    assert session.query(FinanceTransaction).count() == 0


@pytest.mark.parametrize("frequency,previous,expected", [
    ("daily", datetime(2026, 9, 9, 2), 1),
    ("daily", datetime(2026, 9, 11, 2), 8),
    ("weekly", datetime(2026, 9, 1, 2), 8),
    ("weekly", datetime(2026, 8, 20, 2), 1),
    ("monthly", datetime(2026, 8, 1, 2), 8),
    ("monthly", datetime(2026, 7, 1, 2), 1),
])
def test_habit_streak_respects_period_gaps(database, clock, frequency, previous, expected):
    session, factory = database
    user = make_user(session)
    if frequency == "weekly":
        clock(datetime(2026, 9, 7, 2, tzinfo=timezone.utc))
    elif frequency == "monthly":
        clock(datetime(2026, 9, 1, 2, tzinfo=timezone.utc))
    habit = Habit(
        user_id=user.id,
        title="习惯",
        frequency=frequency,
        streak=7,
        best_streak=7,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    session.add(habit)
    session.flush()
    if frequency == "daily":
        completion_dates = [previous.date() - timedelta(days=offset) for offset in range(6, -1, -1)]
    elif frequency == "weekly":
        last_week = previous.date() - timedelta(days=previous.weekday())
        completion_dates = [last_week - timedelta(days=7 * offset) for offset in range(6, -1, -1)]
    else:
        completion_dates = [
            date(previous.year, previous.month - offset, 1)
            if previous.month > offset
            else date(previous.year - 1, previous.month - offset + 12, 1)
            for offset in range(6, -1, -1)
        ]
    for completed_on in completion_dates:
        session.add(HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        ))
    session.commit()
    TodoService(session).complete_habit(habit, user.id)
    assert habit.streak == expected
    assert habit.best_streak == max(7, expected)
    assert session.query(HabitCompletion).filter_by(habit_id=habit.id).count() == 8


def test_habit_history_survives_new_completion_deactivation_and_deletion(database, clock):
    session, factory = database
    user = make_user(session)
    habit = Habit(
        user_id=user.id,
        title="习惯",
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    session.add(habit)
    session.flush()
    session.add(HabitCompletion(
        habit_id=habit.id,
        user_id=user.id,
        completed_on=date(2026, 9, 11),
        completed_at=datetime(2026, 9, 11, 2),
    ))
    session.commit()
    service = StatsService(session)
    TodoService(session).complete_habit(habit, user.id)
    TodoService(session).complete_habit(habit, user.id)
    for deactivate in (True, False):
        if deactivate:
            habit.is_active = False
            session.commit()
        else:
            TodoService(session).delete_habit(habit.id)
        stats = {row["date"]: row["completed"] for row in service.get_habit_stats(user.id)}
        assert stats["2026-09-11"] == 1
        assert stats["2026-09-12"] == 1
    assert session.query(HabitCompletion).count() == 2


def test_habit_stats_ignore_invalid_completion_facts(database, clock):
    session, factory = database
    user = make_user(session)
    habit = Habit(
        user_id=user.id,
        title="统计有效计划日",
        frequency="weekdays",
        weekdays=[0],
        created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )
    session.add(habit)
    session.flush()
    session.add_all([
        HabitCompletion(
            habit_id=habit.id,
            user_id=user.id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time()),
        )
        for completed_on in (
            date(2026, 8, 31),
            date(2026, 9, 7),
            date(2026, 9, 12),
            date(2026, 9, 14),
        )
    ])
    session.commit()

    stats = {row["date"]: row["completed"] for row in StatsService(session).get_habit_stats(user.id)}

    assert stats["2026-09-07"] == 1
    assert stats["2026-09-12"] == 0


def test_habit_backfill_is_idempotent_and_does_not_invent_history(database, clock):
    session, factory = database
    user = make_user(session)
    session.add(Habit(user_id=user.id, title="旧习惯", streak=100,
                      last_completed_at=datetime(2026, 9, 11, 16)))
    session.commit()
    backfill_latest_completions(session)
    backfill_latest_completions(session)
    assert session.query(HabitCompletion).count() == 1
    assert session.query(HabitCompletion).one().completed_on == date(2026, 9, 12)


def test_china_midnight_is_shared_by_habits_checkin_and_summary(database, clock):
    session, factory = database
    user = make_user(session)
    habit = Habit(
        user_id=user.id,
        title="习惯",
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    session.add(habit)
    session.commit()
    todo = TodoService(session)
    checkin = CheckinService(session)
    cultivation = CultivationService(session)
    stats = StatsService(session)
    clock(datetime(2026, 9, 11, 15, 59, 59, tzinfo=timezone.utc))
    assert cultivation._utc_today() == date(2026, 9, 11)
    todo.complete_habit(habit, user.id)
    assert checkin.checkin(user.id)["checkin_date"] == date(2026, 9, 11)
    assert next(
        row for row in stats.get_habit_stats(user.id) if row["date"] == "2026-09-11"
    )["completed"] == 1
    clock(datetime(2026, 9, 11, 16, tzinfo=timezone.utc))
    assert cultivation._utc_today() == date(2026, 9, 12)
    assert not checkin.get_status(user.id)["checked_in"]
    assert todo.get_daily_summary(user.id)["summary"]["completed_habits"] == 0
    todo.complete_habit(habit, user.id)
    todo.complete_habit(habit, user.id)
    assert habit.streak == 2
    assert checkin.checkin(user.id)["checkin_date"] == date(2026, 9, 12)
    daily_summary = todo.get_daily_summary(user.id)
    assert daily_summary["summary"]["completed_habits"] == 1
    summary_habit = next(item for item in daily_summary["habits"] if item["id"] == habit.id)
    assert summary_habit["is_active"] is True
    assert summary_habit["paused_today"] is False
    assert summary_habit["scheduled_today"] is True
    assert summary_habit["excused_today"] is False
    assert session.query(HabitCompletion).count() == 2


def test_calendar_and_trends_use_china_dates(database, clock):
    session, factory = database
    user = make_user(session)
    instant = datetime(2026, 9, 11, 16)
    task = Task(user_id=user.id, title="凌晨任务", deadline=instant, created_at=instant,
                completed_at=instant, status=TaskStatus.COMPLETED)
    session.add(task)
    session.add(CoinTransaction(user_id=user.id, amount=10, type=CoinType.EARN,
                                source="task", created_at=instant))
    session.commit()
    calendar = CalendarService(session)
    assert calendar.get_day_detail(user.id, date(2026, 9, 11))["tasks"] == []
    assert len(calendar.get_day_detail(user.id, date(2026, 9, 12))["tasks"]) == 1
    events = calendar.get_events(user.id, date(2026, 9, 12), date(2026, 9, 12))
    assert events[0]["date"] == "2026-09-12"
    stats = StatsService(session)
    assert stats.get_task_trends(user.id)[-1]["completed"] == 1
    assert stats.get_coin_trends(user.id)[-1]["earned"] == 10
    assert len({row["date"] for row in stats.get_task_trends(user.id, "year")}) == 12


def test_task_deadline_offset_round_trips_and_matches_calendar(client, db_session):
    user = make_user(db_session)
    headers = {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}
    response = client.post("/api/todos/tasks", headers=headers,
                           json={"title": "凌晨任务", "deadline": "2026-09-12T00:00:00+08:00"})
    assert response.status_code == 200
    assert response.json()["deadline"] == "2026-09-11T16:00:00Z"
    events = client.get("/api/calendar/events?start=2026-09-12&end=2026-09-12", headers=headers)
    assert any(event["title"] == "凌晨任务" for event in events.json())


def test_legacy_foreign_project_name_is_not_exposed(client, db_session):
    user, owner = make_user(db_session), make_user(db_session)
    project = Project(user_id=owner.id, name="私有项目")
    db_session.add(project)
    db_session.flush()
    db_session.add(Task(user_id=user.id, title="旧任务", project_id=project.id,
                        deadline=datetime(2026, 9, 12, 2)))
    db_session.commit()
    headers = {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}
    tasks = client.get("/api/todos/tasks", headers=headers).json()
    assert tasks[0]["project_id"] is None
    assert tasks[0]["project_name"] is None
    assert tasks[0]["project_color"] is None
    events = client.get("/api/calendar/events?start=2026-09-12&end=2026-09-12", headers=headers).json()
    assert events[0]["project_id"] is None
    assert events[0]["project_name"] is None
    assert events[0]["project_color"] is None
    day = client.get("/api/calendar/day/2026-09-12", headers=headers)
    assert day.status_code == 200
    assert day.json()["tasks"][0]["project_id"] is None
    assert day.json()["tasks"][0]["project_name"] is None
    assert day.json()["tasks"][0]["project_color"] is None
