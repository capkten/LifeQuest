from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

import mcp_server
from app.database import Base
from app.models.user import User
from app.models.finance_category import FinanceCategory, CategoryType
from app.timezone import today


@pytest.fixture
def mcp_crud_db(db_session, monkeypatch):
    Base.metadata.create_all(bind=db_session.bind)
    monkeypatch.setattr(mcp_server, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(mcp_server, "_db_initialized", True)
    user = User(
        username=f"mcp-crud-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
    )
    db_session.add(user)
    db_session.commit()
    auth_token = mcp_server._auth_user_id.set(user.id)
    try:
        yield db_session, user
    finally:
        mcp_server._auth_user_id.reset(auth_token)
        db_session.rollback()
        Base.metadata.drop_all(bind=db_session.bind)


def test_mcp_todo_tools_cover_lifecycle(mcp_crud_db):
    goal = mcp_server.create_goal("年度目标", difficulty="hard")
    assert mcp_server.complete_goal(goal["id"])["status"] == "completed"

    task = mcp_server.create_task("主任务", priority="high")
    subtask = mcp_server.create_subtask(task["id"], "子任务")
    assert mcp_server.complete_subtask(subtask["id"])["is_completed"] is True
    assert mcp_server.delete_subtask(subtask["id"])["status"] == "ok"

    habit = mcp_server.create_habit(
        "指定日期习惯", frequency="weekdays", weekdays=[0, 2, 4]
    )
    assert mcp_server.pause_habit(habit["id"])["is_active"] is False
    assert mcp_server.resume_habit(habit["id"])["is_active"] is True

    workbench = mcp_server.get_workbench()
    quick = mcp_server.create_quick_task(
        "快速任务", schedule="unscheduled", request_id=str(uuid4())
    )
    assert quick["title"] == "快速任务"
    assert mcp_server.update_daily_focus(
        workbench["date"], workbench["revision"], [task["id"]]
    )["focus_tasks"]


def test_mcp_adapters_preserve_extended_fields(mcp_crud_db):
    task = mcp_server.create_task(
        "计划任务",
        start_date="2026-09-14T08:00:00+08:00",
        priority="urgent",
    )
    assert task["priority"] == "urgent"
    assert task["start_date"].startswith("2026-09-14T00:00:00")

    habit = mcp_server.create_habit(
        "工作日习惯", frequency="weekdays", weekdays=[4, 0, 2]
    )
    assert habit["weekdays"] == [0, 2, 4]

    updated = mcp_server.update_habit(habit["id"], weekdays=[1, 3, 5])
    assert updated["weekdays"] == [1, 3, 5]

    daily_habit = mcp_server.create_habit("带备注习惯")
    mcp_server.complete_habit(daily_habit["id"], note="完成记录")
    history = mcp_server.get_habit_history(daily_habit["id"])
    assert any(day["note"] == "完成记录" for day in history["days"])


def test_mcp_adapters_reject_other_users_for_read_complete_and_delete(mcp_crud_db):
    db, owner = mcp_crud_db
    owner_id = owner.id
    task = mcp_server.create_task("私有任务")
    goal = mcp_server.create_goal("私有目标")
    habit = mcp_server.create_habit("私有习惯")
    other_user = User(
        username=f"mcp-other-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
    )
    db.add(other_user)
    db.commit()
    mcp_server._auth_user_id.set(other_user.id)

    with pytest.raises(HTTPException):
        mcp_server.list_subtasks(task["id"])
    with pytest.raises(HTTPException):
        mcp_server.complete_goal(goal["id"])
    with pytest.raises(HTTPException):
        mcp_server.delete_habit(habit["id"])

    mcp_server._auth_user_id.set(owner_id)
    assert mcp_server.list_tasks()[0]["id"] == task["id"]


def test_mcp_workbench_revision_and_quick_task_idempotency(mcp_crud_db):
    task = mcp_server.create_task("重点任务")
    workbench = mcp_server.get_workbench()
    updated = mcp_server.update_daily_focus(
        workbench["date"], workbench["revision"], [task["id"]]
    )
    assert updated["revision"] == workbench["revision"] + 1
    with pytest.raises(HTTPException, match="其他页面更新"):
        mcp_server.update_daily_focus(workbench["date"], workbench["revision"], [])

    request_id = str(uuid4())
    first = mcp_server.create_quick_task(
        "幂等任务", schedule="unscheduled", request_id=request_id
    )
    retry = mcp_server.create_quick_task(
        "幂等任务", schedule="unscheduled", request_id=request_id
    )
    assert retry["id"] == first["id"]
    with pytest.raises(HTTPException, match="其他内容"):
        mcp_server.create_quick_task(
            "不同任务", schedule="unscheduled", request_id=request_id
        )


def test_mcp_delete_habit_leave_returns_deletion_result(mcp_crud_db):
    habit = mcp_server.create_habit("请假习惯")
    leave_on = today() + timedelta(days=1)
    return_on = leave_on + timedelta(days=2)
    mcp_server.create_habit_leave(
        habit["id"], leave_on.isoformat(), return_on.isoformat(), reason="出差"
    )
    leave = mcp_server.get_habit_leave_intervals(habit["id"])[0]

    result = mcp_server.delete_habit_leave(habit["id"], leave["id"])

    assert result["status"] == "ok"
    assert result["id"] == leave["id"]
    assert result["message"] == "Habit leave deleted"


def test_mcp_finance_delete_reverses_balance_and_pays_debt(mcp_crud_db):
    account = mcp_server.create_account("现金", type="cash", balance=1000)
    category = mcp_server.create_category("餐饮", type="expense")
    transaction = mcp_server.create_transaction(
        account["id"], "expense", 120,
        category_id=category["id"], description="午餐",
    )
    assert next(
        item["balance"] for item in mcp_server.list_accounts()
        if item["id"] == account["id"]
    ) == 880
    assert mcp_server.delete_transaction(transaction["id"])["status"] == "ok"
    assert next(
        item["balance"] for item in mcp_server.list_accounts()
        if item["id"] == account["id"]
    ) == 1000

    debt = mcp_server.create_debt(
        creditor="银行", type="loan", amount=500, remaining=500,
    )
    payment = mcp_server.add_debt_payment(
        debt["id"], 100, description="首期", date_str="2026-09-14",
    )
    assert payment["amount"] == 100
    assert mcp_server.list_debts()[0]["remaining"] == 400


def test_mcp_finance_transaction_filters_and_pagination(mcp_crud_db):
    account = mcp_server.create_account("筛选账户", balance=100)
    other_account = mcp_server.create_account("另一个账户", balance=100)
    category = mcp_server.create_category("筛选支出", type="expense")
    mcp_server.create_transaction(
        account["id"], "expense", 10, category_id=category["id"], date_str="2026-09-12"
    )
    target = mcp_server.create_transaction(
        account["id"], "expense", 20, category_id=category["id"], date_str="2026-09-14"
    )
    mcp_server.create_transaction(other_account["id"], "expense", 30, date_str="2026-09-14")

    result = mcp_server.list_transactions(
        page=1, page_size=1, account_id=account["id"],
        category_id=category["id"], type="expense",
        start_date="2026-09-13", end_date="2026-09-14",
    )
    assert result["items"][0]["id"] == target["id"]
    assert result["total"] == 1
    assert result["page"] == 1
    assert result["page_size"] == 1
    assert result["has_more"] is False


def test_mcp_finance_resources_are_scoped_and_system_categories_are_protected(mcp_crud_db):
    db, owner = mcp_crud_db
    owner_id = owner.id
    account = mcp_server.create_account("所有者账户")
    budget = mcp_server.create_budget(100)
    debt = mcp_server.create_debt("朋友", type="lend", amount=50, remaining=50)
    other_user = User(
        username=f"mcp-finance-other-{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
        password_hash="hashed",
    )
    db.add(other_user)
    db.commit()
    mcp_server._auth_user_id.set(other_user.id)

    assert mcp_server.list_accounts() == []
    assert mcp_server.list_budgets() == []
    assert mcp_server.list_debts() == []
    with pytest.raises(HTTPException):
        mcp_server.delete_account(account["id"])
    with pytest.raises(ValueError):
        mcp_server.delete_budget(budget["id"])
    with pytest.raises(ValueError):
        mcp_server.delete_debt(debt["id"])

    system_category = FinanceCategory(
        name="系统分类", type=CategoryType.EXPENSE, is_system=True,
    )
    db.add(system_category)
    db.commit()
    mcp_server._auth_user_id.set(owner_id)
    with pytest.raises(HTTPException, match="Cannot delete system category"):
        mcp_server.delete_category(str(system_category.id))


def test_mcp_finance_omitted_transaction_date_uses_china_today(mcp_crud_db, monkeypatch):
    expected = today()
    monkeypatch.setattr(mcp_server.timezone, "today", lambda: expected)
    account = mcp_server.create_account("时区账户")
    transaction = mcp_server.create_transaction(account["id"], "income", 1)
    assert transaction["date"] == expected.isoformat()


def test_mcp_recurring_lifecycle_and_trigger_are_idempotent_for_same_date(mcp_crud_db):
    account = mcp_server.create_account("定期账户", balance=100)
    recurring = mcp_server.create_recurring_transaction(
        account["id"], "expense", 10, "monthly", "2026-09-14"
    )
    assert mcp_server.list_recurring_transactions()[0]["id"] == recurring["id"]
    first = mcp_server.trigger_recurring_transaction(recurring["id"])
    db, _ = mcp_crud_db
    recurring_row = db.query(mcp_server.RecurringTransaction).filter_by(
        id=UUID(recurring["id"])
    ).first()
    recurring_row.next_date = date.fromisoformat(first["date"])
    db.commit()
    retry = mcp_server.trigger_recurring_transaction(recurring["id"])
    assert retry["id"] == first["id"]
    assert mcp_server.delete_recurring_transaction(recurring["id"])["status"] == "ok"
