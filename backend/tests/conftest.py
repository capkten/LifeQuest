import os
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from types import SimpleNamespace

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
_runtime_directory = tempfile.TemporaryDirectory(prefix="lifequest-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_runtime_directory.name) / 'startup.db'}"
os.environ["MCP_AUTOSTART"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.services.achievement import AchievementService

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def isolated_files(tmp_path):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.services.note.NOTES_DIR", tmp_path / "notes_data")
        patch.setattr("app.api.notes.UPLOAD_DIR", tmp_path / "uploads" / "notes")
        avatar_dir = tmp_path / "uploads" / "avatars"
        avatar_dir.mkdir(parents=True)
        patch.setattr("app.api.users.UPLOAD_DIR", avatar_dir)
        yield


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    # Seed achievements in the test database
    db = TestingSessionLocal()
    try:
        service = AchievementService(db)
        service.seed_achievements()
    finally:
        db.close()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def database(tmp_path):
    """Yield an isolated SQLAlchemy session backed by a temporary database."""
    isolated_engine = create_engine(
        f"sqlite:///{tmp_path / 'database.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=isolated_engine)
    isolated_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=isolated_engine,
    )
    session = isolated_session_local()
    try:
        yield session
    finally:
        session.close()
        isolated_engine.dispose()


@pytest.fixture
def migration_database(tmp_path, monkeypatch):
    """Yield a temporary legacy-shaped database for startup migration tests."""
    from app import main as main_module

    migration_engine = create_engine(
        f"sqlite:///{tmp_path / 'migration.sqlite'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=migration_engine)
    with migration_engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS refresh_tokens"))
        indexes = inspect(connection).get_indexes("exchange_history")
        for index in indexes:
            if index.get("name") == "uq_exchange_history_user_idempotency_key":
                connection.exec_driver_sql(
                    'DROP INDEX "uq_exchange_history_user_idempotency_key"'
                )
        existing_columns = {
            column["name"] for column in inspect(connection).get_columns("users")
        }
        if "total_experience" in existing_columns:
            connection.exec_driver_sql("ALTER TABLE users DROP COLUMN total_experience")
        exchange_columns = {
            column["name"] for column in inspect(connection).get_columns("exchange_history")
        }
        for column_name in ("idempotency_key", "item_name_snapshot", "unit_price_snapshot"):
            if column_name in exchange_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE exchange_history DROP COLUMN {column_name}"
                )

    session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=migration_engine,
    )
    monkeypatch.setattr(main_module, "engine", migration_engine)
    monkeypatch.setattr(main_module, "SessionLocal", session_local)
    session = session_local()
    try:
        yield session
    finally:
        session.close()
        migration_engine.dispose()


@pytest.fixture
def user(db_session):
    from app.services.auth import get_password_hash

    username = f"defect-{uuid4().hex}"
    account = User(
        username=username,
        email=f"{username}@example.com",
        password_hash=get_password_hash("testpassword123"),
        coins=100,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def login_payload(user):
    return {"username": user.username, "password": "testpassword123"}


@pytest.fixture
def auth_headers(client, db_session, user):
    from app.models.todo import Habit
    from app.services.auth import create_access_token

    habit = Habit(user_id=user.id, title="每日回归习惯", frequency="daily")
    db_session.add(habit)
    db_session.commit()
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture
def shop_item(db_session, user):
    from app.models.shop import ShopItem

    item = ShopItem(
        created_by=user.id,
        name="回归商品",
        coin_price=10,
        stock=10,
        is_active=True,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def run_startup_migrations(database):
    from app.main import _migrate_columns

    return _migrate_columns(database.get_bind())


def has_column(database_session, table_name, column_name):
    return column_name in {
        column["name"]
        for column in inspect(database_session.get_bind()).get_columns(table_name)
    }


@pytest.fixture(name="run_startup_migrations")
def run_startup_migrations_fixture():
    return run_startup_migrations


@pytest.fixture(name="has_column")
def has_column_fixture():
    return has_column


@pytest.fixture
def clock(monkeypatch):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant[0].astimezone(tz) if tz else instant[0].replace(tzinfo=None)

    for module in ("app.timezone", "app.services.todo", "app.services.stats", "app.models.todo"):
        monkeypatch.setattr(f"{module}.datetime", FrozenDatetime)

    return lambda value: instant.__setitem__(0, value)


@pytest.fixture
def notebook(db_session, user):
    from app.models.note import Notebook

    value = Notebook(user_id=user.id, name=f"Notebook {uuid4().hex[:8]}")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def project(db_session, user):
    from app.models.project import Project

    value = Project(user_id=user.id, name=f"Project {uuid4().hex[:8]}")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def equipped_item(db_session, user, shop_item):
    from app.models.backpack import BackpackItem, ItemStatus, ItemType

    value = BackpackItem(
        user_id=user.id,
        shop_item_id=shop_item.id,
        item_type=ItemType.GEAR,
        status=ItemStatus.EQUIPPED,
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def referenced_item(db_session, user, shop_item):
    from app.models.backpack import BackpackItem, ItemStatus, ItemType

    value = BackpackItem(
        user_id=user.id,
        shop_item_id=shop_item.id,
        item_type=ItemType.GEAR,
        status=ItemStatus.ACTIVE,
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def exchange(db_session, user, shop_item):
    from app.models.shop import ExchangeHistory, ExchangeStatus

    value = ExchangeHistory(
        user_id=user.id,
        item_id=shop_item.id,
        quantity=1,
        total_cost=shop_item.coin_price,
        status=ExchangeStatus.COMPLETED,
        item_name_snapshot=shop_item.name,
        unit_price_snapshot=shop_item.coin_price,
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def debt(db_session, user):
    from app.models.debt import Debt, DebtStatus, DebtType

    value = Debt(
        user_id=user.id,
        creditor="测试对象",
        type=DebtType.BORROW,
        amount=Decimal("100.00"),
        remaining=Decimal("100.00"),
        status=DebtStatus.ACTIVE,
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def budget(db_session, user):
    from app.models.budget import Budget, BudgetPeriod

    value = Budget(
        user_id=user.id,
        amount=Decimal("100.00"),
        period=BudgetPeriod.MONTHLY,
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def transaction(db_session, user):
    from app.models.account import Account, AccountType
    from app.models.finance_transaction import FinanceTransaction, FinanceTransactionType

    account = Account(user_id=user.id, name="测试账户", type=AccountType.CASH, balance=0)
    db_session.add(account)
    db_session.flush()
    value = FinanceTransaction(
        user_id=user.id,
        account_id=account.id,
        type=FinanceTransactionType.EXPENSE,
        amount=Decimal("10.00"),
        date=datetime(2026, 9, 12).date(),
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def goal(db_session, user):
    from app.models.todo import Goal

    value = Goal(user_id=user.id, title="测试目标")
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def goal_or_budget(goal):
    return SimpleNamespace(url=f"/api/todos/goals/{goal.id}", model=goal)


@pytest.fixture
def inactive_account(db_session, user):
    from app.models.account import Account, AccountType

    value = Account(user_id=user.id, name="停用账户", type=AccountType.CASH, is_active=False)
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def active_account(db_session, user):
    from app.models.account import Account, AccountType

    value = Account(user_id=user.id, name="启用账户", type=AccountType.CASH, is_active=True)
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def coin_rows(db_session, user):
    from app.models.coin_transaction import CoinTransaction

    return lambda: db_session.query(CoinTransaction).filter_by(user_id=user.id).all()


@pytest.fixture
def create_daily_habit():
    def create(session, _auth_headers=None, **values):
        from app.models.todo import Habit

        user_id = values.pop("user_id", None)
        frequency = values.pop("frequency", "daily")
        if user_id is None and _auth_headers:
            from app.services.auth import decode_access_token

            token = _auth_headers["Authorization"].split(" ", 1)[1]
            user_id = decode_access_token(token)["sub"]
        habit = Habit(
            user_id=user_id,
            title=values.pop("title", "每日习惯"),
            frequency=frequency,
            **values,
        )
        if habit.user_id is None:
            raise ValueError("create_daily_habit requires a user or auth headers")
        session.add(habit)
        session.commit()
        session.refresh(habit)
        return habit

    return create


@pytest.fixture
def create_habit_with_pause_interval(create_daily_habit):
    def create(session, user_or_headers, paused_on, resumed_on=None, **values):
        from app.models.habit_pause import HabitPauseInterval

        if isinstance(user_or_headers, dict):
            from app.services.auth import decode_access_token

            token = user_or_headers["Authorization"].split(" ", 1)[1]
            user_id = decode_access_token(token)["sub"]
            habit = create_daily_habit(session, user_id=user_id, **values)
        else:
            user_id = user_or_headers
            habit = create_daily_habit(session, user_id=user_id, **values)
        interval = HabitPauseInterval(
            habit_id=habit.id,
            user_id=user_id,
            paused_on=paused_on,
            resumed_on=resumed_on,
        )
        session.add(interval)
        session.commit()
        return habit, interval

    return create


@pytest.fixture
def create_nested_note_tree():
    def create(session, notebook_id, names=("Folder", "Note")):
        from app.models.note_node import NoteNode, normalize_name

        folder_name, note_name = names
        folder = NoteNode(
            notebook_id=notebook_id,
            type="folder",
            name=folder_name,
            normalized_name=normalize_name(folder_name),
            path=f"/{folder_name}",
        )
        session.add(folder)
        session.flush()
        note = NoteNode(
            notebook_id=notebook_id,
            parent_id=folder.id,
            type="note",
            name=note_name,
            normalized_name=normalize_name(note_name),
            path=f"/{folder_name}/{note_name}",
        )
        session.add(note)
        session.commit()
        return folder, note

    return create


@pytest.fixture
def snapshot_tree(db_session):
    def snapshot(notebook_id):
        from app.models.note_node import NoteNode

        return [
            (node.id, node.parent_id, node.type, node.name, node.path)
            for node in db_session.query(NoteNode)
            .filter_by(notebook_id=notebook_id)
            .order_by(NoteNode.path, NoteNode.id)
            .all()
        ]

    return snapshot


@pytest.fixture
def snapshot_shop_user_state(db_session):
    def snapshot(user_id):
        from app.models.backpack import BackpackItem
        from app.models.coin_transaction import CoinTransaction
        from app.models.shop import ExchangeHistory, ShopItem
        from app.models.user import User

        user_row = db_session.query(User).filter_by(id=user_id).one()
        return {
            "coins": user_row.coins,
            "items": [
                (item.shop_item_id, item.quantity, item.status.value if hasattr(item.status, "value") else item.status)
                for item in db_session.query(BackpackItem).filter_by(user_id=user_id).all()
            ],
            "exchanges": [
                (item.id, item.item_id, item.quantity, item.total_cost, item.status)
                for item in db_session.query(ExchangeHistory).filter_by(user_id=user_id).all()
            ],
            "stock": {
                item.id: item.stock
                for item in db_session.query(ShopItem).all()
            },
            "coins_log": db_session.query(CoinTransaction).filter_by(user_id=user_id).count(),
        }

    return snapshot


@pytest.fixture
def latest_history_action(db_session):
    def latest(user_id, item_id=None):
        from app.models.backpack import UsageHistory

        query = db_session.query(UsageHistory).filter_by(user_id=user_id)
        if item_id is not None:
            query = query.filter_by(item_id=item_id)
        row = query.order_by(UsageHistory.created_at.desc(), UsageHistory.id.desc()).first()
        return row.action.value if row and hasattr(row.action, "value") else row.action if row else None

    return latest


@pytest.fixture
def get_item(db_session):
    def get(item_id):
        from app.models.backpack import BackpackItem
        from app.models.shop import ShopItem

        return (
            db_session.query(BackpackItem).filter_by(id=item_id).first()
            or db_session.query(ShopItem).filter_by(id=item_id).first()
        )

    return get


@pytest.fixture
def exchange_history_name(db_session):
    def get(exchange_or_id):
        from app.models.shop import ExchangeHistory, ShopItem

        exchange_id = getattr(exchange_or_id, "id", exchange_or_id)
        exchange = db_session.query(ExchangeHistory).filter_by(id=exchange_id).one()
        return exchange.item_name_snapshot or db_session.query(ShopItem.name).filter_by(id=exchange.item_id).scalar()

    return get


@pytest.fixture
def create_weekly_target_habit(create_daily_habit):
    def create(session, user_id, weekly_target=3, **values):
        return create_daily_habit(
            session,
            user_id=user_id,
            frequency="weekly_target",
            weekly_target=weekly_target,
            **values,
        )

    return create


@pytest.fixture
def add_completion_dates():
    def add(session, habit, dates, user_id=None):
        from app.models.habit_completion import HabitCompletion

        user_id = user_id or habit.user_id
        for completed_on in dates:
            session.add(HabitCompletion(
                habit_id=habit.id,
                user_id=user_id,
                completed_on=completed_on,
                completed_at=datetime.combine(completed_on, datetime.min.time(), tzinfo=timezone.utc),
            ))
        session.commit()

    return add


@pytest.fixture
def complete_on():
    def complete(session, habit, completed_on, user_id=None):
        from app.models.habit_completion import HabitCompletion

        completion = HabitCompletion(
            habit_id=habit.id,
            user_id=user_id or habit.user_id,
            completed_on=completed_on,
            completed_at=datetime.combine(completed_on, datetime.min.time(), tzinfo=timezone.utc),
        )
        session.add(completion)
        session.commit()
        return completion

    return complete


@pytest.fixture
def count_goal_reward(db_session):
    def count(user_id, goal_id):
        from app.models.coin_transaction import CoinTransaction

        return db_session.query(CoinTransaction).filter_by(
            user_id=user_id,
            source="goal",
            source_id=str(goal_id),
        ).count()

    return count


@pytest.fixture
def fail_on_second_rename():
    original_rename = Path.rename
    calls = {"count": 0}

    def rename(path, target):
        calls["count"] += 1
        if calls["count"] >= 2:
            raise AssertionError("Path.rename called more than once")
        return original_rename(path, target)

    return rename


@pytest.fixture
def users(db_session):
    first = User(
        username=f"owner-{uuid4().hex}",
        email=f"owner-{uuid4().hex}@example.com",
        password_hash="unused",
    )
    second = User(
        username=f"other-{uuid4().hex}",
        email=f"other-{uuid4().hex}@example.com",
        password_hash="unused",
    )
    db_session.add_all([first, second])
    db_session.commit()
    return first, second


@pytest.fixture
def assert_no_cross_user_resource_mutation():
    def assert_unchanged(before, after):
        assert after == before

    return assert_unchanged
