from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Event, get_ident
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.account import Account, AccountType
from app.models.budget import Budget, BudgetPeriod
from app.models.finance_transaction import FinanceTransaction
from app.models.todo import Habit
from app.models.coin_transaction import CoinSource, CoinTransaction, CoinType
from app.models.finance_category import CategoryType, FinanceCategory
from app.models.recurring_transaction import RecurringTransaction
from app.models.backpack import BackpackItem, UsageAction, UsageHistory
from app.models.project import ProjectPhase
from app.models.shop import ExchangeHistory, ShopItem
from app.services.finance import FinanceService
from app.models.user import User
from app.services.note import NoteService
from app.database import Base
from app.repositories.shop import ShopItemRepository
from app.repositories.user import UserRepository
from app.schemas.note import FolderCreate, NoteCreate, NoteUpdate
from app.schemas.shop import ExchangeHistoryCreate
from app.services.shop import ShopService
import mcp_server
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


def test_project_status_reads_normalize_legacy_values_and_unknowns(
    client, auth_headers, project, db_session,
):
    project.status = "legacy_status"
    phase = ProjectPhase(project_id=project.id, name="历史阶段", status="in_progress")
    db_session.add(phase)
    db_session.commit()

    response = client.get(f"/api/projects/{project.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "unknown"
    assert response.json()["phases"][0]["status"] == "active"
    assert response.json()["status"] not in {"planning", "active", "completed", "archived"}


def test_mcp_tree_move_restores_files_when_combined_move_fails(client, auth_headers, user, db_session, monkeypatch):
    notebook = client.post(
        "/api/notes/notebooks",
        json={"name": "MCP notes"},
        headers=auth_headers,
    ).json()
    root = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "旧目录"},
        headers=auth_headers,
    ).json()
    child = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "子目录", "parent_id": root["id"]},
        headers=auth_headers,
    ).json()
    notes = [
        client.post(
            f"/api/notes/notebooks/{notebook['id']}/notes",
            json={"title": title, "content": content, "parent_id": child["id"]},
            headers=auth_headers,
        ).json()
        for title, content in (("第一篇", "first"), ("第二篇", "second"))
    ]
    destination = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "目标目录"},
        headers=auth_headers,
    ).json()
    before = [client.get(f"/api/notes/{note['id']}", headers=auth_headers).json() for note in notes]
    old_files = [Path(note["content_path"]) for note in before]

    original_rename = Path.rename

    def fail_on_destination_rename(path, target):
        if "目标目录" in str(target):
            raise OSError("destination rename failed")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_on_destination_rename)
    factory = sessionmaker(bind=db_session.get_bind(), autoflush=False, autocommit=False)
    monkeypatch.setattr(mcp_server, "SessionLocal", factory)
    monkeypatch.setattr(mcp_server, "_ensure_db", lambda: None)
    user_token = mcp_server._auth_user_id.set(user.id)
    auth_token = mcp_server._auth_token_authenticated.set(False)
    try:
        with pytest.raises(OSError):
            mcp_server.rename_or_move_node(
                root["id"],
                name="新目录",
                parent_id=destination["id"],
            )
    finally:
        mcp_server._auth_user_id.reset(user_token)
        mcp_server._auth_token_authenticated.reset(auth_token)

    after = [client.get(f"/api/notes/{note['id']}", headers=auth_headers).json() for note in notes]
    assert [(item["id"], item["path"], item["content"]) for item in after] == [
        (item["id"], item["path"], item["content"]) for item in before
    ]
    assert all(path.exists() for path in old_files)


def test_note_tree_move_serializes_planning_and_application(database, monkeypatch):
    from app.models.note import Notebook
    from app.models.note_node import NoteNode

    local_user = User(
        username=f"concurrent-{uuid4().hex}",
        email=f"concurrent-{uuid4().hex}@example.com",
        password_hash="unused",
    )
    database.add(local_user)
    database.commit()
    notebook = Notebook(user_id=local_user.id, name="Concurrent notes")
    database.add(notebook)
    database.commit()
    service = NoteService(database)
    root = service.create_folder(notebook.id, local_user.id, FolderCreate(name="Root"))
    target_a = service.create_folder(notebook.id, local_user.id, FolderCreate(name="A"))
    target_b = service.create_folder(notebook.id, local_user.id, FolderCreate(name="B"))
    note = service.create_note(notebook.id, local_user.id, NoteCreate(title="Note", content="stable", parent_id=root.id))
    factory = sessionmaker(bind=database.get_bind(), autoflush=False, autocommit=False)
    first_plan_started = Event()
    allow_first_plan = Event()
    second_plan_started = Event()
    original_plan = NoteService._plan_tree_move
    calls = []

    def observe_plan(instance, *args, **kwargs):
        calls.append(get_ident())
        if len(calls) == 1:
            first_plan_started.set()
            assert allow_first_plan.wait(timeout=10)
        else:
            second_plan_started.set()
        return original_plan(instance, *args, **kwargs)

    monkeypatch.setattr(NoteService, "_plan_tree_move", observe_plan)

    def move(parent_id):
        session = factory()
        try:
            return NoteService(session).move_tree(note.id, parent_id, note.name)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(move, target_a.id)
        assert first_plan_started.wait(timeout=10)
        second = executor.submit(move, target_b.id)
        assert not second_plan_started.wait(timeout=0.25)
        allow_first_plan.set()
        first.result(timeout=20)
        second.result(timeout=20)

    database.expire_all()
    refreshed = database.query(NoteNode).filter(NoteNode.id == note.id).one()
    assert refreshed.parent_id == target_b.id
    assert refreshed.path == "/B/Note.md"
    assert refreshed.name == "Note"
    assert Path(refreshed.content_path).read_text(encoding="utf-8") == "stable"


def test_update_note_uses_current_parent_after_concurrent_move(database):
    from app.models.note import Notebook
    from app.models.note_node import NoteNode

    local_user = User(
        username=f"stale-{uuid4().hex}",
        email=f"stale-{uuid4().hex}@example.com",
        password_hash="unused",
    )
    database.add(local_user)
    database.commit()
    notebook = Notebook(user_id=local_user.id, name="Stale note update")
    database.add(notebook)
    database.commit()
    service = NoteService(database)
    source = service.create_folder(notebook.id, local_user.id, FolderCreate(name="Source"))
    destination = service.create_folder(notebook.id, local_user.id, FolderCreate(name="Destination"))
    note = service.create_note(
        notebook.id,
        local_user.id,
        NoteCreate(title="Note", content="stable", parent_id=source.id),
    )

    factory = sessionmaker(bind=database.get_bind(), autoflush=False, autocommit=False)
    stale_session = factory()
    mover_session = factory()
    try:
        stale_service = NoteService(stale_session)
        stale_node = stale_service.node_repo.get_by_id(note.id)
        assert stale_node.parent_id == source.id

        NoteService(mover_session).move_tree(note.id, new_parent_id=destination.id)

        updated = stale_service.update_note(
            note.id,
            NoteUpdate(title="Renamed"),
            user_id=local_user.id,
        )

        assert updated.parent_id == destination.id
        assert updated.path == "/Destination/Renamed.md"
        assert Path(updated.content_path).read_text(encoding="utf-8") == "stable"
        stale_session.expire_all()
        refreshed = stale_session.query(NoteNode).filter(NoteNode.id == note.id).one()
        assert refreshed.parent_id == destination.id
        assert refreshed.path == "/Destination/Renamed.md"
    finally:
        stale_session.close()
        mover_session.close()


def test_purchase_idempotency_key_returns_one_exchange(client, auth_headers, shop_item, db_session):
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
    assert first.json()["item_name_snapshot"] == shop_item.name
    assert first.json()["unit_price_snapshot"] == shop_item.coin_price

    assert db_session.query(ExchangeHistory).filter_by(user_id=shop_item.created_by).count() == 1
    backpack_item = db_session.query(BackpackItem).filter_by(
        user_id=shop_item.created_by, shop_item_id=shop_item.id,
    ).one()
    assert backpack_item.quantity == 1
    db_session.refresh(shop_item)
    assert shop_item.stock == 9
    assert db_session.query(CoinTransaction).filter_by(
        user_id=shop_item.created_by,
        source=CoinSource.SHOP.value,
        type=CoinType.SPEND,
    ).count() == 1


def test_purchase_same_key_concurrently_reloads_the_unique_winner(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        f"sqlite:///{tmp_path / 'purchase-idempotency-race.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = factory()
    user = User(
        username=f"concurrent-{uuid4().hex}",
        email=f"concurrent-{uuid4().hex}@example.com",
        password_hash="unused",
        coins=100,
    )
    item = ShopItem(
        created_by=None,
        name="并发商品",
        coin_price=10,
        stock=5,
        is_active=True,
    )
    session.add_all([user, item])
    session.commit()
    session.refresh(user)
    session.refresh(item)

    loser_reached_item_read = Event()
    allow_loser_to_continue = Event()
    loser_thread_id = []
    original_get_for_update = ShopItemRepository.get_for_update

    def skip_sqlite_user_serialization(_repository, _user_id):
        return None

    def synchronize_item_read(repository, item_id):
        locked_item = original_get_for_update(repository, item_id)
        if loser_thread_id and loser_thread_id[0] == get_ident():
            loser_reached_item_read.set()
            assert allow_loser_to_continue.wait(timeout=10)
        return locked_item

    monkeypatch.setattr(UserRepository, "lock", skip_sqlite_user_serialization)
    monkeypatch.setattr(ShopItemRepository, "get_for_update", synchronize_item_read)

    exchange_in = ExchangeHistoryCreate(item_id=item.id, quantity=1)

    def purchase_loser():
        worker_session = factory()
        try:
            loser_thread_id.append(get_ident())
            exchange = ShopService(worker_session).purchase_item(
                user.id,
                exchange_in,
                idempotency_key="concurrent-same-key",
            )
            return exchange.id
        finally:
            worker_session.close()

    def purchase_winner():
        worker_session = factory()
        try:
            return ShopService(worker_session).purchase_item(
                user.id,
                exchange_in,
                idempotency_key="concurrent-same-key",
            ).id
        finally:
            worker_session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            try:
                loser = executor.submit(purchase_loser)
                assert loser_reached_item_read.wait(timeout=10)
                winner = executor.submit(purchase_winner)
                winner_id = winner.result(timeout=20)
                allow_loser_to_continue.set()
                loser_id = loser.result(timeout=20)
            finally:
                allow_loser_to_continue.set()

        verify = factory()
        try:
            stored_user = verify.get(User, user.id)
            stored_item = verify.get(ShopItem, item.id)
            backpack_item = verify.query(BackpackItem).filter_by(
                user_id=user.id,
                shop_item_id=item.id,
            ).one()

            assert loser_id == winner_id
            assert verify.query(ExchangeHistory).filter_by(user_id=user.id).count() == 1
            assert stored_user.coins == 90
            assert stored_item.stock == 4
            assert backpack_item.quantity == 1
            assert verify.query(CoinTransaction).filter_by(
                user_id=user.id,
                source=CoinSource.SHOP.value,
                type=CoinType.SPEND,
            ).count() == 1
        finally:
            verify.close()
    finally:
        session.close()
        engine.dispose()


def test_unequip_item_records_history(client, auth_headers, equipped_item, latest_history_action, db_session):
    response = client.post(
        f"/api/backpack/items/{equipped_item.id}/unequip",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    db_session.refresh(equipped_item)
    assert latest_history_action(equipped_item.user_id, equipped_item.id) == "unequip"


def test_refund_equipped_item_is_rejected_without_mutation(
    client, auth_headers, exchange, equipped_item, snapshot_shop_user_state,
):
    before = snapshot_shop_user_state(exchange.user_id)

    response = client.post(
        f"/api/shop/exchange/{exchange.id}/refund",
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ITEM_EQUIPPED"
    assert snapshot_shop_user_state(exchange.user_id) == before


def test_delete_referenced_item_archives_it(
    client, auth_headers, referenced_item, exchange, db_session, exchange_history_name,
):
    response = client.delete(
        f"/api/shop/items/{referenced_item.shop_item_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    item = db_session.query(ShopItem).filter_by(id=referenced_item.shop_item_id).one()
    assert item.is_active is False
    assert exchange_history_name(exchange) == item.name
    history = client.get("/api/shop/exchange/history", headers=auth_headers)
    assert history.status_code == 200
    assert history.json()[0]["item_name_snapshot"] == item.name
    assert history.json()[0]["unit_price_snapshot"] == item.coin_price


def test_backpack_history_returns_canonical_action_type(client, auth_headers, equipped_item, db_session):
    db_session.add(UsageHistory(
        user_id=equipped_item.user_id,
        item_id=equipped_item.id,
        shop_item_id=equipped_item.shop_item_id,
        action=UsageAction.ADD,
    ))
    db_session.commit()
    response = client.get("/api/backpack/history", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()[0]["action_type"] == "add"


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


def _add_budget_expense(db_session, user, category, expense_date, amount):
    account = Account(
        user_id=user.id,
        name=f"预算账户-{expense_date}",
        type=AccountType.CASH,
        balance=0,
    )
    db_session.add(account)
    db_session.flush()
    db_session.add(FinanceTransaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id,
        type="expense",
        amount=Decimal(str(amount)),
        date=expense_date,
    ))


def _add_budget_transaction(
    db_session, user, category, transaction_date, amount, transaction_type="expense",
):
    account = Account(
        user_id=user.id,
        name=f"预算账户-{transaction_date}-{transaction_type}",
        type=AccountType.CASH,
        balance=0,
    )
    db_session.add(account)
    db_session.flush()
    db_session.add(FinanceTransaction(
        user_id=user.id,
        account_id=account.id,
        category_id=category.id,
        type=transaction_type,
        amount=Decimal(str(amount)),
        date=transaction_date,
    ))


def test_weekly_budget_uses_week_period_and_start_date(
    client, db_session, user, monkeypatch,
):
    category = FinanceCategory(
        user_id=user.id,
        name="每周预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget = Budget(
        user_id=user.id,
        category=category,
        amount=Decimal("100.00"),
        period=BudgetPeriod.WEEKLY,
        start_date=date(2026, 9, 8),
    )
    db_session.add(budget)
    db_session.flush()
    _add_budget_expense(db_session, user, category, date(2026, 9, 7), 10)
    _add_budget_expense(db_session, user, category, date(2026, 9, 9), 20)
    _add_budget_expense(db_session, user, category, date(2026, 9, 16), 30)
    db_session.commit()
    monkeypatch.setattr("app.services.finance.china_today", lambda: date(2026, 9, 10))

    payload = FinanceService(db_session).get_budgets(user.id)[0]

    assert payload["spent_amount"] == Decimal("20.00")


def test_budget_monthly_period_excludes_transactions_outside_current_month(
    client, db_session, user, monkeypatch,
):
    category = FinanceCategory(
        user_id=user.id,
        name="月度预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget = Budget(
        user_id=user.id,
        category=category,
        amount=Decimal("100.00"),
        period=BudgetPeriod.MONTHLY,
    )
    db_session.add(budget)
    db_session.flush()
    _add_budget_expense(db_session, user, category, date(2026, 8, 31), 10)
    _add_budget_expense(db_session, user, category, date(2026, 9, 1), 20)
    _add_budget_expense(db_session, user, category, date(2026, 9, 30), 30)
    _add_budget_expense(db_session, user, category, date(2026, 10, 1), 40)
    db_session.commit()
    monkeypatch.setattr("app.services.finance.china_today", lambda: date(2026, 9, 15))

    payload = FinanceService(db_session).get_budgets(user.id)[0]

    assert payload["spent_amount"] == Decimal("50.00")


def test_budget_period_end_is_an_exclusive_upper_bound(
    client, db_session, user, monkeypatch,
):
    category = FinanceCategory(
        user_id=user.id,
        name="边界预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget = Budget(
        user_id=user.id,
        category=category,
        amount=Decimal("100.00"),
        period=BudgetPeriod.WEEKLY,
    )
    db_session.add(budget)
    db_session.flush()
    _add_budget_expense(db_session, user, category, date(2026, 9, 13), 20)
    _add_budget_expense(db_session, user, category, date(2026, 9, 14), 30)
    db_session.commit()
    monkeypatch.setattr("app.services.finance.china_today", lambda: date(2026, 9, 10))

    payload = FinanceService(db_session).get_budgets(user.id)[0]

    assert payload["spent_amount"] == Decimal("20.00")


def test_budget_spending_excludes_transfers(
    client, db_session, user, monkeypatch,
):
    category = FinanceCategory(
        user_id=user.id,
        name="转账预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget = Budget(
        user_id=user.id,
        category=category,
        amount=Decimal("100.00"),
        period=BudgetPeriod.MONTHLY,
    )
    db_session.add(budget)
    db_session.flush()
    _add_budget_transaction(db_session, user, category, date(2026, 9, 10), 20)
    _add_budget_transaction(
        db_session, user, category, date(2026, 9, 11), 30, transaction_type="transfer",
    )
    db_session.commit()
    monkeypatch.setattr("app.services.finance.china_today", lambda: date(2026, 9, 15))

    payload = FinanceService(db_session).get_budgets(user.id)[0]

    assert payload["spent_amount"] == Decimal("20.00")


def test_budget_spending_isolated_from_other_users(
    client, db_session, user, monkeypatch,
):
    category = FinanceCategory(
        user_id=user.id,
        name="隔离预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget = Budget(
        user_id=user.id,
        category=category,
        amount=Decimal("100.00"),
        period=BudgetPeriod.MONTHLY,
    )
    foreign_user = User(
        username=f"budget-foreign-{uuid4().hex}",
        email=f"budget-foreign-{uuid4().hex}@example.com",
        password_hash="test-password-hash",
    )
    db_session.add_all([budget, foreign_user])
    db_session.flush()
    _add_budget_expense(db_session, user, category, date(2026, 9, 10), 20)
    _add_budget_expense(db_session, foreign_user, category, date(2026, 9, 11), 80)
    db_session.commit()
    monkeypatch.setattr("app.services.finance.china_today", lambda: date(2026, 9, 15))

    payload = FinanceService(db_session).get_budgets(user.id)[0]

    assert payload["spent_amount"] == Decimal("20.00")


def test_budget_payload_keeps_decimal_calculations_until_response_boundary(
    client, db_session, user, monkeypatch,
):
    category = FinanceCategory(
        user_id=user.id,
        name="精确预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget = Budget(
        user_id=user.id,
        category=category,
        amount=Decimal("100.01"),
        period=BudgetPeriod.MONTHLY,
    )
    db_session.add(budget)
    db_session.flush()
    _add_budget_expense(db_session, user, category, date(2026, 9, 10), "33.34")
    db_session.commit()
    monkeypatch.setattr("app.services.finance.china_today", lambda: date(2026, 9, 15))

    payload = FinanceService(db_session)._budget_payload(
        budget, date(2026, 9, 15),
    )

    assert isinstance(payload["amount"], Decimal)
    assert isinstance(payload["spent_amount"], Decimal)
    assert isinstance(payload["remaining_amount"], Decimal)
    assert isinstance(payload["progress"], Decimal)
    assert payload["remaining_amount"] == Decimal("66.67")


def test_budget_response_has_names_and_computed_values(
    client, auth_headers, budget, db_session, user,
):
    category = FinanceCategory(
        user_id=user.id,
        name="预算响应分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget.category = category
    db_session.add(category)
    db_session.commit()

    response = client.get("/api/finance/budgets", headers=auth_headers)

    assert response.status_code == 200
    row = response.json()[0]
    assert row["category_name"]
    assert row["spent_amount"] == 0
    assert row["remaining_amount"] == row["amount"]
    assert row["progress"] == 0


def test_budget_mutations_return_computed_payload(
    client, auth_headers, db_session, user,
):
    category = FinanceCategory(
        user_id=user.id,
        name="保存响应分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    db_session.add(category)
    db_session.commit()

    create_response = client.post(
        "/api/finance/budgets",
        headers=auth_headers,
        json={"category_id": str(category.id), "amount": 100, "period": "monthly"},
    )

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["category_name"] == "保存响应分类"
    assert created["spent_amount"] == 0
    assert created["remaining_amount"] == 100
    assert created["progress"] == 0

    update_response = client.put(
        f"/api/finance/budgets/{created['id']}",
        headers=auth_headers,
        json={"amount": 50},
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["category_name"] == "保存响应分类"
    assert updated["spent_amount"] == 0
    assert updated["remaining_amount"] == 50
    assert updated["progress"] == 0


def test_budget_category_update_rejects_foreign_category_without_mutation(
    client, auth_headers, budget, db_session, user,
):
    own_category = FinanceCategory(
        user_id=user.id,
        name="原预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    foreign_user = User(
        username=f"foreign-{uuid4().hex}",
        email=f"foreign-{uuid4().hex}@example.com",
        password_hash="test-password-hash",
    )
    foreign_category = FinanceCategory(
        user=foreign_user,
        name="他人预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    budget.category = own_category
    db_session.add_all([own_category, foreign_user, foreign_category])
    db_session.commit()

    response = client.put(
        f"/api/finance/budgets/{budget.id}",
        headers=auth_headers,
        json={"category_id": str(foreign_category.id)},
    )

    assert response.status_code in (403, 404)
    db_session.refresh(budget)
    assert budget.category_id == own_category.id


def test_budget_category_update_rejects_income_category_without_mutation(
    client, auth_headers, budget, db_session, user,
):
    own_category = FinanceCategory(
        user_id=user.id,
        name="支出预算分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    income_category = FinanceCategory(
        user_id=user.id,
        name="收入分类",
        type=CategoryType.INCOME,
        is_system=False,
    )
    budget.category = own_category
    db_session.add_all([own_category, income_category])
    db_session.commit()

    response = client.put(
        f"/api/finance/budgets/{budget.id}",
        headers=auth_headers,
        json={"category_id": str(income_category.id)},
    )

    assert response.status_code == 422
    db_session.refresh(budget)
    assert budget.category_id == own_category.id


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


def test_avatar_rejects_fake_image_content(client, auth_headers):
    response = client.post(
        "/api/users/me/avatar",
        headers=auth_headers,
        files={"file": ("avatar.png", b"not-an-image", "image/png")},
    )

    assert response.status_code == 400


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


def test_recurring_update_rejects_invalid_targets_without_mutation(
    client, auth_headers, active_account, inactive_account, db_session, user,
):
    from app.models.finance_category import CategoryType

    active_account.balance = 100
    inactive_account.balance = 60
    own_income = FinanceCategory(
        user_id=user.id,
        name="更新收入分类",
        type=CategoryType.INCOME,
        is_system=False,
    )
    foreign_user = User(
        username="recurring-update-foreign",
        email="recurring-update-foreign@example.com",
        password_hash="not-used",
    )
    db_session.add(foreign_user)
    db_session.flush()
    foreign_account = Account(
        user_id=foreign_user.id,
        name="他人账户",
        type=AccountType.CASH,
        balance=20,
    )
    foreign_category = FinanceCategory(
        user_id=foreign_user.id,
        name="他人支出分类",
        type=CategoryType.EXPENSE,
        is_system=False,
    )
    foreign_recurring = RecurringTransaction(
        user=foreign_user,
        account=foreign_account,
        category=foreign_category,
        type="expense",
        amount=10,
        description="他人周期流水",
        frequency="monthly",
        next_date=date(2026, 9, 15),
    )
    db_session.add_all([own_income, foreign_account, foreign_category, foreign_recurring])
    db_session.flush()
    recurring = RecurringTransaction(
        user_id=user.id,
        account_id=active_account.id,
        type="expense",
        amount=10,
        description="原始周期流水",
        frequency="monthly",
        next_date=date(2026, 9, 15),
        is_active=True,
    )
    db_session.add(recurring)
    db_session.commit()
    db_session.refresh(recurring)
    original = {
        "account_id": recurring.account_id,
        "category_id": recurring.category_id,
        "type": recurring.type,
        "amount": recurring.amount,
        "description": recurring.description,
        "frequency": recurring.frequency,
        "next_date": recurring.next_date,
        "is_active": recurring.is_active,
    }

    rejected_updates = [
        (f"/api/finance/recurring/{foreign_recurring.id}", {"description": "越权"}, 404),
        (f"/api/finance/recurring/{recurring.id}", {"account_id": str(inactive_account.id)}, 409),
        (f"/api/finance/recurring/{recurring.id}", {"category_id": str(foreign_category.id)}, 404),
        (f"/api/finance/recurring/{recurring.id}", {"category_id": str(own_income.id)}, 422),
        (f"/api/finance/recurring/{recurring.id}", {"type": "transfer"}, 400),
        (f"/api/finance/recurring/{recurring.id}", {"amount": 0}, 422),
        (f"/api/finance/recurring/{recurring.id}", {"frequency": "quarterly"}, 422),
        (f"/api/finance/recurring/{recurring.id}", {"account_id": None}, 422),
    ]
    for url, payload, expected_status in rejected_updates:
        response = client.put(url, headers=auth_headers, json=payload)
        assert response.status_code == expected_status, (payload, response.text)
        db_session.refresh(recurring)
        assert {
            "account_id": recurring.account_id,
            "category_id": recurring.category_id,
            "type": recurring.type,
            "amount": recurring.amount,
            "description": recurring.description,
            "frequency": recurring.frequency,
            "next_date": recurring.next_date,
            "is_active": recurring.is_active,
        } == original
        db_session.refresh(active_account)
        db_session.refresh(inactive_account)
        assert active_account.balance == 100
        assert inactive_account.balance == 60

    db_session.refresh(foreign_recurring)
    assert foreign_recurring.description == "他人周期流水"
