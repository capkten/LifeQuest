"""
LifeQuest MCP Server — exposes LifeQuest as MCP tools for AI agents.

Usage:
    # stdio (Claude Desktop / Claude Code)
    python backend/mcp_server.py

    # SSE (remote / HTTP)
    python backend/mcp_server.py --transport sse --port 3001

Authentication:
    Call the `login` tool with username + password before using other tools.
    A service account may be explicitly configured with LIFEQUEST_MCP_SERVICE_USER_ID.
"""

import argparse
import contextvars
import logging
import os
import sys
import weakref
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from mcp.server.lowlevel.server import request_ctx

from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.account import AccountType
from app.models.budget import Budget, BudgetPeriod
from app.models.debt import Debt, DebtStatus, DebtType
from app.models.finance_transaction import FinanceTransaction, FinanceTransactionType
from app.models.project import ProjectPhase, ProjectMilestone
from app.schemas.finance import (
    AccountCreate,
    AccountUpdate,
    TransactionCreate,
    TransactionUpdate,
    BudgetUpdate,
    DebtUpdate,
)
from app.schemas.todo import (
    HabitCreate,
    HabitUpdate,
    TaskCreate,
    TaskUpdate,
    GoalUpdate,
    Difficulty,
    Frequency,
)
from app.schemas.project import ProjectUpdate, PhaseUpdate, MilestoneUpdate
from app.schemas.note import FolderCreate, NotebookCreate, NoteCreate, NoteUpdate
from app.models.todo import TaskStatus
from app.services.checkin import CheckinService
from app.services.finance import FinanceService
from app.services.note import NoteService
from app.services.project import ProjectService
from app.services.stats import StatsService
from app.services.todo import TodoService
from app.services.user import UserService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth context — set by `login` tool, read by all other tools
# ---------------------------------------------------------------------------

_auth_user_id: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "_auth_user_id", default=None
)
_auth_users_by_session: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _current_mcp_session():
    """Return the active MCP session, when called from an MCP request."""
    try:
        return request_ctx.get().session
    except LookupError:
        return None


def _set_authenticated_user(user_id: UUID) -> None:
    """Persist authentication for the whole MCP session, not one tool call."""
    session = _current_mcp_session()
    if session is not None:
        _auth_users_by_session[session] = user_id
    # Keep the context-local value for stdio and direct unit-test calls.
    _auth_user_id.set(user_id)

# ---------------------------------------------------------------------------
# DB init — run migrations on first use
# ---------------------------------------------------------------------------

_db_initialized = False


def _ensure_db():
    global _db_initialized
    if _db_initialized:
        return
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    # Run column migrations (same as FastAPI startup)
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        with engine.begin() as conn:
            habit_cols = {c["name"] for c in inspector.get_columns("habits")}
            if "last_completed_at" not in habit_cols:
                conn.execute(text("ALTER TABLE habits ADD COLUMN last_completed_at DATETIME"))
            user_cols = {c["name"] for c in inspector.get_columns("users")}
            if "total_coins_earned" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN total_coins_earned INTEGER NOT NULL DEFAULT 0"))
                conn.execute(text("UPDATE users SET total_coins_earned = coins WHERE total_coins_earned = 0"))
            task_cols = {c["name"] for c in inspector.get_columns("tasks")}
            for col_name, col_def in {
                "project_id": "VARCHAR(36)", "phase_id": "VARCHAR(36)",
                "milestone_id": "VARCHAR(36)", "start_date": "DATETIME",
                "priority": "VARCHAR(10) NOT NULL DEFAULT 'medium'",
                "sort_order": "INTEGER NOT NULL DEFAULT 0",
            }.items():
                if col_name not in task_cols:
                    conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}"))
            txn_cols = {c["name"] for c in inspector.get_columns("finance_transactions")}
            if "recurring_id" not in txn_cols:
                conn.execute(text("ALTER TABLE finance_transactions ADD COLUMN recurring_id VARCHAR(36)"))
    except Exception:
        logger.exception("MCP database column migration failed")
        raise
    _db_initialized = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_user_id(db) -> UUID:
    """Resolve user ID from the authenticated session or explicit service account."""
    _ensure_db()
    # 1. Check the authenticated MCP session.
    session = _current_mcp_session()
    if session is not None:
        uid = _auth_users_by_session.get(session)
        if uid:
            return uid

    # 2. Check the context-local value for stdio/direct calls.
    uid = _auth_user_id.get()
    if uid:
        return uid

    # 3. Check explicitly configured service account.
    env_id = os.environ.get("LIFEQUEST_MCP_SERVICE_USER_ID")
    if env_id:
        try:
            service_user_id = UUID(env_id)
        except ValueError as exc:
            raise RuntimeError("LIFEQUEST_MCP_SERVICE_USER_ID 无效") from exc
        if db.query(User).filter(User.id == service_user_id).first():
            return service_user_id
        raise RuntimeError("MCP service account 不存在")
    raise RuntimeError("请先调用 login 工具登录")


def _require_notebook_write(svc: NoteService, notebook_id: UUID, user_id: UUID) -> None:
    try:
        svc.require_notebook_access(notebook_id, user_id, write=True)
    except PermissionError as exc:
        raise ValueError("Not authorized") from exc


def _require_node_write(svc: NoteService, node_id: UUID, user_id: UUID):
    try:
        return svc.require_node_access(node_id, user_id, write=True)
    except (ValueError, PermissionError) as exc:
        raise ValueError("Node not found") from exc


def _serialize(obj):
    """Convert SQLAlchemy model / date / UUID to JSON-safe dict."""
    if obj is None:
        return None
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if hasattr(obj, "__table__"):
        # SQLAlchemy model
        return {
            col.name: _serialize(getattr(obj, col.name))
            for col in obj.__table__.columns
        }
    return obj


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="lifequest",
    instructions=(
        "LifeQuest 是一个个人成长 gamification 系统。"
        "你可以通过这些工具管理待办事项、记账、打卡、查看项目和统计数据。"
    ),
)


# ===================== 认证 =====================


@mcp.tool()
def login(username: str, password: str) -> Any:
    """登录 LifeQuest 账户。必须先调用此工具才能操作其他功能。返回用户信息。"""
    db = SessionLocal()
    try:
        _ensure_db()
        svc = UserService(db)
        user = svc.authenticate(username, password)
        if not user:
            return {"error": "用户名或密码错误"}
        _set_authenticated_user(user.id)
        return {
            "status": "ok",
            "message": f"已登录为 {user.username}",
            "user": _serialize(user),
        }
    finally:
        db.close()


# ===================== 待办 =====================


@mcp.tool()
def list_habits() -> Any:
    """列出所有习惯，包含标题、难度、频率、连续天数、金币/经验奖励。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        habits = svc.get_habits(uid)
        return [_serialize(h) for h in habits]
    finally:
        db.close()


@mcp.tool()
def list_tasks(project_id: Optional[str] = None) -> Any:
    """列出所有任务。可选按 project_id 筛选。返回标题、状态、难度、截止日期。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        if project_id:
            tasks = svc.get_tasks_by_project(UUID(project_id), uid)
        else:
            tasks = svc.get_tasks(uid)
        return [_serialize(t) for t in tasks]
    finally:
        db.close()


@mcp.tool()
def list_goals() -> Any:
    """列出所有目标，包含标题、状态、进度、截止日期。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        goals = svc.get_goals(uid)
        return [_serialize(g) for g in goals]
    finally:
        db.close()


@mcp.tool()
def update_goal(
    goal_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[str] = None,
    coins_reward: Optional[int] = None,
    exp_reward: Optional[int] = None,
    progress: Optional[float] = None,
    deadline: Optional[str] = None,
) -> Any:
    """更新目标。只传入需要修改的字段；deadline 使用 ISO 8601 格式。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        goal = svc.get_goal_for_user(UUID(goal_id), uid)
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if difficulty is not None:
            update_data["difficulty"] = Difficulty(difficulty)
        if status is not None:
            update_data["status"] = TaskStatus(status)
        if coins_reward is not None:
            update_data["coins_reward"] = coins_reward
        if exp_reward is not None:
            update_data["exp_reward"] = exp_reward
        if progress is not None:
            update_data["progress"] = progress
        if deadline is not None:
            update_data["deadline"] = datetime.fromisoformat(deadline)
        if not update_data:
            return _serialize(goal)
        return _serialize(svc.update_goal(goal, GoalUpdate(**update_data)))
    finally:
        db.close()


@mcp.tool()
def create_task(
    title: str,
    description: str = "",
    difficulty: str = "medium",
    coins_reward: int = 10,
    exp_reward: int = 5,
    deadline: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Any:
    """创建一个新任务。difficulty: easy/medium/hard。deadline 格式: ISO 8601。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        data = TaskCreate(
            title=title,
            description=description or None,
            difficulty=Difficulty(difficulty),
            coins_reward=coins_reward,
            exp_reward=exp_reward,
            deadline=datetime.fromisoformat(deadline) if deadline else None,
            project_id=UUID(project_id) if project_id else None,
        )
        task = svc.create_task(uid, data)
        return _serialize(task)
    finally:
        db.close()


@mcp.tool()
def complete_task(task_id: str) -> Any:
    """完成一个任务。返回更新后的任务信息（含金币/经验奖励）。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        task = svc.get_task_for_user(UUID(task_id), uid)
        result = svc.complete_task(task, uid)
        return _serialize(result)
    finally:
        db.close()


@mcp.tool()
def update_task(
    task_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[str] = None,
    coins_reward: Optional[int] = None,
    exp_reward: Optional[int] = None,
    deadline: Optional[str] = None,
    project_id: Optional[str] = None,
    phase_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
    start_date: Optional[str] = None,
    priority: Optional[str] = None,
) -> Any:
    """更新任务。只传入需要修改的字段；日期使用 ISO 8601 格式。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        task = svc.get_task_for_user(UUID(task_id), uid)
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if difficulty is not None:
            update_data["difficulty"] = Difficulty(difficulty)
        if status is not None:
            update_data["status"] = TaskStatus(status)
        if coins_reward is not None:
            update_data["coins_reward"] = coins_reward
        if exp_reward is not None:
            update_data["exp_reward"] = exp_reward
        if deadline is not None:
            update_data["deadline"] = datetime.fromisoformat(deadline)
        if project_id is not None:
            update_data["project_id"] = UUID(project_id)
        if phase_id is not None:
            update_data["phase_id"] = UUID(phase_id)
        if milestone_id is not None:
            update_data["milestone_id"] = UUID(milestone_id)
        if start_date is not None:
            update_data["start_date"] = datetime.fromisoformat(start_date)
        if priority is not None:
            update_data["priority"] = priority
        if not update_data:
            return _serialize(task)
        updated_task = svc.update_task(task, TaskUpdate(**update_data))
        return _serialize(updated_task)
    finally:
        db.close()


@mcp.tool()
def create_habit(
    title: str,
    description: str = "",
    difficulty: str = "medium",
    frequency: str = "daily",
    coins_reward: int = 10,
    exp_reward: int = 5,
) -> Any:
    """创建一个新习惯。frequency: daily/weekly/monthly。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        data = HabitCreate(
            title=title,
            description=description or None,
            difficulty=Difficulty(difficulty),
            frequency=Frequency(frequency),
            coins_reward=coins_reward,
            exp_reward=exp_reward,
        )
        habit = svc.create_habit(uid, data)
        return _serialize(habit)
    finally:
        db.close()


@mcp.tool()
def complete_habit(habit_id: str) -> Any:
    """完成一个习惯打卡。返回更新后的习惯信息（含连续天数、奖励）。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        habit = svc.get_habit_for_user(UUID(habit_id), uid)
        result = svc.complete_habit(habit, uid)
        return _serialize(result)
    finally:
        db.close()


@mcp.tool()
def update_habit(
    habit_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    difficulty: Optional[str] = None,
    frequency: Optional[str] = None,
    coins_reward: Optional[int] = None,
    exp_reward: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> Any:
    """更新习惯。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        habit = svc.get_habit_for_user(UUID(habit_id), uid)
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if difficulty is not None:
            update_data["difficulty"] = Difficulty(difficulty)
        if frequency is not None:
            update_data["frequency"] = Frequency(frequency)
        if coins_reward is not None:
            update_data["coins_reward"] = coins_reward
        if exp_reward is not None:
            update_data["exp_reward"] = exp_reward
        if is_active is not None:
            update_data["is_active"] = is_active
        if not update_data:
            return _serialize(habit)
        return _serialize(svc.update_habit(habit, HabitUpdate(**update_data)))
    finally:
        db.close()


@mcp.tool()
def get_daily_summary() -> Any:
    """获取今日摘要：今日习惯完成情况、到期任务、活跃目标。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        return _serialize(svc.get_daily_summary(uid))
    finally:
        db.close()


# ===================== 财务 =====================


@mcp.tool()
def finance_dashboard() -> Any:
    """获取财务概览：总余额、本月收支、预算使用情况、最近交易。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        return _serialize(svc.get_dashboard(uid))
    finally:
        db.close()


@mcp.tool()
def list_accounts() -> Any:
    """列出所有账户（银行卡、现金、支付宝等），含余额信息。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        accounts = svc.get_accounts(uid)
        return [_serialize(a) for a in accounts]
    finally:
        db.close()


@mcp.tool()
def update_account(
    account_id: str,
    name: Optional[str] = None,
    type: Optional[str] = None,
    icon: Optional[str] = None,
    balance: Optional[float] = None,
    credit_limit: Optional[float] = None,
    billing_day: Optional[int] = None,
    repayment_day: Optional[int] = None,
    interest_rate: Optional[float] = None,
    currency: Optional[str] = None,
    is_active: Optional[bool] = None,
    sort_order: Optional[int] = None,
) -> Any:
    """更新账户。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        account = svc._get_account_for_user(UUID(account_id), uid)
        update_data = {}
        for key, value in {
            "name": name, "icon": icon, "balance": balance,
            "credit_limit": credit_limit, "billing_day": billing_day,
            "repayment_day": repayment_day, "interest_rate": interest_rate,
            "currency": currency, "is_active": is_active, "sort_order": sort_order,
        }.items():
            if value is not None:
                update_data[key] = value
        if type is not None:
            update_data["type"] = AccountType(type)
        if not update_data:
            return _serialize(account)
        return _serialize(svc.update_account(account, AccountUpdate(**update_data)))
    finally:
        db.close()


@mcp.tool()
def create_transaction(
    account_id: str,
    type: str,
    amount: float,
    description: str = "",
    date_str: Optional[str] = None,
) -> Any:
    """记一笔账。type: income/expense。date_str 格式: YYYY-MM-DD，默认今天。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        txn_date = date.fromisoformat(date_str) if date_str else date.today()
        data = TransactionCreate(
            account_id=UUID(account_id),
            type=FinanceTransactionType(type),
            amount=amount,
            description=description,
            date=txn_date,
        )
        txn = svc.create_transaction(uid, data)
        return _serialize(txn)
    finally:
        db.close()


@mcp.tool()
def transfer(
    from_account_id: str,
    to_account_id: str,
    amount: float,
    description: str = "",
) -> Any:
    """在两个账户之间转账。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        result = svc.transfer(
            uid, UUID(from_account_id), UUID(to_account_id), amount, description
        )
        return _serialize(result)
    finally:
        db.close()


@mcp.tool()
def list_transactions(
    limit: int = 20,
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """查询交易记录。可按类型(income/expense/transfer)和日期范围筛选。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        filters = {"limit": limit}
        if type:
            filters["type"] = type
        if start_date:
            filters["start_date"] = date.fromisoformat(start_date)
        if end_date:
            filters["end_date"] = date.fromisoformat(end_date)
        result = svc.get_transactions(uid, **filters)
        return _serialize(result)
    finally:
        db.close()


@mcp.tool()
def update_transaction(
    transaction_id: str,
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    type: Optional[str] = None,
    amount: Optional[float] = None,
    description: Optional[str] = None,
    date_str: Optional[str] = None,
    to_account_id: Optional[str] = None,
) -> Any:
    """更新交易并同步账户余额。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        transaction = db.query(FinanceTransaction).filter(
            FinanceTransaction.id == UUID(transaction_id),
            FinanceTransaction.user_id == uid,
        ).first()
        if transaction is None:
            raise ValueError("Transaction not found")
        update_data = {}
        if account_id is not None:
            update_data["account_id"] = UUID(account_id)
        if category_id is not None:
            update_data["category_id"] = UUID(category_id)
        if type is not None:
            update_data["type"] = FinanceTransactionType(type)
        if amount is not None:
            update_data["amount"] = amount
        if description is not None:
            update_data["description"] = description
        if date_str is not None:
            update_data["date"] = date.fromisoformat(date_str)
        if to_account_id is not None:
            update_data["to_account_id"] = UUID(to_account_id)
        if not update_data:
            return _serialize(transaction)
        return _serialize(svc.update_transaction(
            transaction, TransactionUpdate(**update_data), uid
        ))
    finally:
        db.close()


@mcp.tool()
def update_budget(
    budget_id: str,
    category_id: Optional[str] = None,
    amount: Optional[float] = None,
    period: Optional[str] = None,
    start_date: Optional[str] = None,
) -> Any:
    """更新预算。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        budget = db.query(Budget).filter(
            Budget.id == UUID(budget_id), Budget.user_id == uid
        ).first()
        if budget is None:
            raise ValueError("Budget not found")
        update_data = {}
        if category_id is not None:
            update_data["category_id"] = UUID(category_id)
        if amount is not None:
            update_data["amount"] = amount
        if period is not None:
            update_data["period"] = BudgetPeriod(period)
        if start_date is not None:
            update_data["start_date"] = date.fromisoformat(start_date)
        if not update_data:
            return _serialize(budget)
        return _serialize(svc.update_budget(budget, BudgetUpdate(**update_data)))
    finally:
        db.close()


@mcp.tool()
def update_debt(
    debt_id: str,
    creditor: Optional[str] = None,
    type: Optional[str] = None,
    amount: Optional[float] = None,
    remaining: Optional[float] = None,
    interest_rate: Optional[float] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    status: Optional[str] = None,
) -> Any:
    """更新债务。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        debt = db.query(Debt).filter(
            Debt.id == UUID(debt_id), Debt.user_id == uid
        ).first()
        if debt is None:
            raise ValueError("Debt not found")
        update_data = {}
        for key, value in {
            "creditor": creditor, "amount": amount, "remaining": remaining,
            "interest_rate": interest_rate, "description": description,
        }.items():
            if value is not None:
                update_data[key] = value
        if type is not None:
            update_data["type"] = DebtType(type)
        if due_date is not None:
            update_data["due_date"] = date.fromisoformat(due_date)
        if status is not None:
            update_data["status"] = DebtStatus(status)
        if not update_data:
            return _serialize(debt)
        return _serialize(svc.update_debt(debt, DebtUpdate(**update_data)))
    finally:
        db.close()


# ===================== 项目 =====================


@mcp.tool()
def list_projects() -> Any:
    """列出所有项目，含名称、状态、进度百分比、任务统计。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        results = svc.get_projects(uid)
        projects = []
        for r in results:
            p = r["project"]
            projects.append({
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "status": p.status,
                "color": p.color,
                "total_tasks": r["total_tasks"],
                "completed_tasks": r["completed_tasks"],
                "progress": r["progress"],
            })
        return projects
    finally:
        db.close()


@mcp.tool()
def get_project_detail(project_id: str) -> Any:
    """获取项目详情，含阶段、里程碑、任务列表。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        detail = svc.get_project_detail(UUID(project_id), uid)
        p = detail["project"]
        return {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "status": p.status,
            "total_tasks": detail["total_tasks"],
            "completed_tasks": detail["completed_tasks"],
            "progress": detail["progress"],
            "phases": _serialize(detail["phases"]),
            "milestones": _serialize(detail["milestones"]),
        }
    finally:
        db.close()


@mcp.tool()
def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """更新项目。只传入需要修改的字段；日期使用 YYYY-MM-DD。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        project = svc.get_project_for_user(UUID(project_id), uid)
        update_data = {}
        for key, value in {
            "name": name, "description": description, "color": color,
            "icon": icon, "status": status,
        }.items():
            if value is not None:
                update_data[key] = value
        if start_date is not None:
            update_data["start_date"] = date.fromisoformat(start_date)
        if end_date is not None:
            update_data["end_date"] = date.fromisoformat(end_date)
        if not update_data:
            return _serialize(project)
        return _serialize(svc.update_project(project, ProjectUpdate(**update_data)))
    finally:
        db.close()


@mcp.tool()
def update_project_phase(
    phase_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Any:
    """更新项目阶段。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        phase = svc.phase_repo.get_by_id(UUID(phase_id))
        if phase is None:
            raise ValueError("Phase not found")
        svc.get_project_for_user(phase.project_id, uid)
        update_data = {}
        for key, value in {
            "name": name, "description": description, "status": status,
            "sort_order": sort_order,
        }.items():
            if value is not None:
                update_data[key] = value
        if not update_data:
            return _serialize(phase)
        return _serialize(svc.update_phase(phase, PhaseUpdate(**update_data)))
    finally:
        db.close()


@mcp.tool()
def update_project_milestone(
    milestone_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Any:
    """更新项目里程碑。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        milestone = svc.milestone_repo.get_by_id(UUID(milestone_id))
        if milestone is None:
            raise ValueError("Milestone not found")
        svc.get_project_for_user(milestone.project_id, uid)
        update_data = {}
        for key, value in {
            "name": name, "description": description, "sort_order": sort_order,
        }.items():
            if value is not None:
                update_data[key] = value
        if due_date is not None:
            update_data["due_date"] = date.fromisoformat(due_date)
        if not update_data:
            return _serialize(milestone)
        return _serialize(svc.update_milestone(
            milestone, MilestoneUpdate(**update_data)
        ))
    finally:
        db.close()


@mcp.tool()
def create_project_task(
    project_id: str,
    title: str,
    description: str = "",
    difficulty: str = "medium",
    coins_reward: int = 10,
    exp_reward: int = 5,
) -> Any:
    """在指定项目下创建一个任务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        svc.get_project_for_user(UUID(project_id), uid)
        data = TaskCreate(
            title=title,
            description=description or None,
            difficulty=Difficulty(difficulty),
            coins_reward=coins_reward,
            exp_reward=exp_reward,
        )
        task = svc.create_project_task(uid, UUID(project_id), data)
        return _serialize(task)
    finally:
        db.close()


# ===================== 打卡 =====================


@mcp.tool()
def daily_checkin() -> Any:
    """每日打卡。返回打卡结果（连续天数、金币、经验奖励）。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = CheckinService(db)
        result = svc.checkin(uid)
        return _serialize(result)
    finally:
        db.close()


# ===================== 统计 =====================


@mcp.tool()
def get_stats() -> Any:
    """获取数据概览：已完成任务数、习惯数、连续打卡、金币、经验、等级。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = StatsService(db)
        return _serialize(svc.get_overview(uid))
    finally:
        db.close()


# ===================== 用户 =====================


@mcp.tool()
def get_profile() -> Any:
    """获取用户资料：等级、经验、金币、称号。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = UserService(db)
        user = svc.get_by_id(uid)
        if not user:
            return {"error": "User not found"}
        return _serialize(user)
    finally:
        db.close()


# ===================== 笔记 =====================


def _build_note_tree(nodes: list) -> list:
    """Build the nested tree shape used by the notes REST endpoint."""
    children_map = {}
    for node in nodes:
        children_map.setdefault(node.parent_id, []).append(node)

    def build(parent_id):
        result = []
        for node in children_map.get(parent_id, []):
            result.append({
                "id": _serialize(node.id),
                "name": node.name,
                "type": node.type,
                "parent_id": _serialize(node.parent_id),
                "children": build(node.id),
            })
        return result

    return build(None)


@mcp.tool()
def list_notebooks() -> Any:
    """列出当前用户的所有笔记本。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        return [_serialize(notebook) for notebook in NoteService(db).get_notebooks(uid)]
    finally:
        db.close()


@mcp.tool()
def create_notebook(
    name: str,
    description: Optional[str] = None,
    icon: Optional[str] = None,
) -> Any:
    """创建笔记本。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        notebook = NoteService(db).create_notebook(
            uid, NotebookCreate(name=name, description=description, icon=icon)
        )
        return _serialize(notebook)
    finally:
        db.close()


@mcp.tool()
def delete_notebook(notebook_id: str) -> Any:
    """删除当前用户的笔记本。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        notebook_uuid = UUID(notebook_id)
        if not svc.verify_notebook_owner(notebook_uuid, uid):
            raise ValueError("Notebook not found")
        svc.delete_notebook(notebook_uuid)
        return {"status": "ok", "message": "Notebook deleted"}
    finally:
        db.close()


@mcp.tool()
def get_notebook_tree(notebook_id: str) -> Any:
    """获取当前用户笔记本的完整目录树。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        notebook_uuid = UUID(notebook_id)
        if not svc.verify_notebook_ownership(notebook_uuid, uid):
            raise ValueError("Notebook not found")
        return _build_note_tree(svc.get_tree(notebook_uuid))
    finally:
        db.close()


@mcp.tool()
def list_note_children(notebook_id: str, parent_id: Optional[str] = None) -> Any:
    """列出笔记本根目录或指定文件夹下的直接子节点。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        notebook_uuid = UUID(notebook_id)
        if not svc.verify_notebook_ownership(notebook_uuid, uid):
            raise ValueError("Notebook not found")
        parent_uuid = UUID(parent_id) if parent_id else None
        if parent_uuid:
            parent = svc.node_repo.get_by_id(parent_uuid)
            if not parent or parent.notebook_id != notebook_uuid or parent.type != "folder":
                raise ValueError("Folder not found")
        return [_serialize(node) for node in svc.get_children(notebook_uuid, parent_uuid)]
    finally:
        db.close()


@mcp.tool()
def create_folder(
    notebook_id: str,
    name: str,
    parent_id: Optional[str] = None,
) -> Any:
    """在笔记本根目录或指定文件夹下创建文件夹。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        notebook_uuid = UUID(notebook_id)
        if not svc.verify_notebook_ownership(notebook_uuid, uid):
            raise ValueError("Notebook not found")
        _require_notebook_write(svc, notebook_uuid, uid)
        folder = svc.create_folder(
            notebook_uuid,
            uid,
            FolderCreate(name=name, parent_id=UUID(parent_id) if parent_id else None),
        )
        return _serialize(folder)
    finally:
        db.close()


@mcp.tool()
def create_note(
    notebook_id: str,
    title: str,
    content: Optional[str] = None,
    parent_id: Optional[str] = None,
    summary: Optional[str] = None,
    tags: Optional[str] = None,
) -> Any:
    """创建笔记并返回笔记元数据和正文。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        notebook_uuid = UUID(notebook_id)
        if not svc.verify_notebook_ownership(notebook_uuid, uid):
            raise ValueError("Notebook not found")
        _require_notebook_write(svc, notebook_uuid, uid)
        note = svc.create_note(
            notebook_uuid,
            uid,
            NoteCreate(
                title=title,
                content=content,
                parent_id=UUID(parent_id) if parent_id else None,
                summary=summary,
                tags=tags,
            ),
        )
        result = _serialize(note)
        result["content"] = content or ""
        return result
    finally:
        db.close()


@mcp.tool()
def rename_or_move_node(
    node_id: str,
    name: Optional[str] = None,
    parent_id: Optional[str] = None,
    move_to_root: bool = False,
) -> Any:
    """重命名或移动笔记/文件夹；使用 move_to_root=true 将节点移到根目录。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        node_uuid = UUID(node_id)
        if not svc.verify_node_ownership(node_uuid, uid):
            raise ValueError("Node not found")
        _require_node_write(svc, node_uuid, uid)
        node = svc.node_repo.get_by_id(node_uuid)
        if name is not None:
            svc.rename_node(node_uuid, name, commit=False)
        if move_to_root or parent_id is not None:
            svc.move_node(node_uuid, UUID(parent_id) if parent_id else None)
        if name is not None and not (move_to_root or parent_id is not None):
            db.commit()
            db.refresh(node)
        return _serialize(svc.node_repo.get_by_id(node_uuid))
    finally:
        db.close()


@mcp.tool()
def delete_node(node_id: str) -> Any:
    """删除笔记或文件夹；删除文件夹会递归删除其内容。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        node_uuid = UUID(node_id)
        if not svc.verify_node_ownership(node_uuid, uid):
            raise ValueError("Node not found")
        _require_node_write(svc, node_uuid, uid)
        svc.delete_node(node_uuid)
        return {"status": "ok", "message": "Node deleted"}
    finally:
        db.close()


@mcp.tool()
def list_recent_notes(limit: int = 8) -> Any:
    """列出当前用户最近打开的笔记。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        return [_serialize(node) for node in NoteService(db).get_recent_notes(uid, limit)]
    finally:
        db.close()


@mcp.tool()
def discover_notes(
    sort: str = "last_opened",
    notebook_id: Optional[str] = None,
    tag: Optional[str] = None,
    pinned: Optional[bool] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None,
    limit: int = 50,
) -> Any:
    """按排序、笔记本、标签、置顶和更新时间筛选笔记。时间使用 ISO 8601。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        return [
            _serialize(node)
            for node in NoteService(db).discover_notes(
                user_id=uid,
                sort=sort,
                notebook_id=UUID(notebook_id) if notebook_id else None,
                tag=tag,
                pinned=pinned,
                updated_after=datetime.fromisoformat(updated_after) if updated_after else None,
                updated_before=datetime.fromisoformat(updated_before) if updated_before else None,
                limit=limit,
            )
        ]
    finally:
        db.close()


@mcp.tool()
def mark_note_opened(note_id: str) -> Any:
    """记录当前用户打开笔记的时间并返回更新后的笔记元数据。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        return _serialize(NoteService(db).mark_note_opened(UUID(note_id), uid))
    finally:
        db.close()


@mcp.tool()
def search_notes(query: str) -> Any:
    """搜索笔记标题。返回匹配的笔记列表（id、名称、路径）。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        results = svc.search_notes(uid, query)
        return [_serialize(n) for n in results]
    finally:
        db.close()


@mcp.tool()
def get_note(note_id: str) -> Any:
    """读取笔记详情和正文。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        if not svc.verify_node_ownership(UUID(note_id), uid):
            raise ValueError("Note not found")
        note = svc.node_repo.get_by_id(UUID(note_id))
        if not note or note.type != "note":
            raise ValueError("Note not found")
        result = _serialize(note)
        result["content"] = svc.get_note_content(note.id)
        return result
    finally:
        db.close()


@mcp.tool()
def update_note(
    note_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    summary: Optional[str] = None,
    tags: Optional[str] = None,
    is_pinned: Optional[bool] = None,
) -> Any:
    """更新笔记标题、正文或元数据。只传入需要修改的字段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = NoteService(db)
        note_id_uuid = UUID(note_id)
        if not svc.verify_node_ownership(note_id_uuid, uid):
            raise ValueError("Note not found")
        _require_node_write(svc, note_id_uuid, uid)
        note = svc.node_repo.get_by_id(note_id_uuid)
        if not note or note.type != "note":
            raise ValueError("Note not found")
        update_data = {}
        for key, value in {
            "title": title, "content": content, "summary": summary,
            "tags": tags, "is_pinned": is_pinned,
        }.items():
            if value is not None:
                update_data[key] = value
        if not update_data:
            result = _serialize(note)
            result["content"] = svc.get_note_content(note.id)
            return result
        updated = svc.update_note(note.id, NoteUpdate(**update_data))
        result = _serialize(updated)
        result["content"] = svc.get_note_content(updated.id)
        return result
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LifeQuest MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3001)
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
