"""
LifeQuest MCP Server — exposes LifeQuest as MCP tools for AI agents.

Usage:
    # stdio (Claude Desktop / Claude Code)
    python backend/mcp_server.py

    # SSE (remote / HTTP)
    python backend/mcp_server.py --transport sse --port 3001

Authentication:
    Use Authorization: Bearer <token> for SSE, LIFEQUEST_MCP_TOKEN for stdio,
    or call `login_with_token`; password `login` remains available for compatibility.
"""

import argparse
import contextvars
import logging
import os
import re
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
from app import timezone
from app.schemas.user import UserResponse
from app.models.account import AccountType
from app.models.budget import Budget, BudgetPeriod
from app.models.finance_category import FinanceCategory, CategoryType
from app.models.debt import Debt, DebtStatus, DebtType
from app.models.finance_transaction import FinanceTransaction, FinanceTransactionType
from app.models.recurring_transaction import RecurringTransaction, RecurFrequency
from app.models.project import ProjectPhase, ProjectMilestone
from app.schemas.finance import (
    AccountCreate,
    AccountUpdate,
    TransactionCreate,
    TransactionUpdate,
    CategoryCreate,
    BudgetCreate,
    BudgetUpdate,
    RecurringCreate,
    DebtCreate,
    DebtUpdate,
    DebtPaymentCreate,
)
from app.schemas.todo import (
    HabitCreate,
    HabitUpdate,
    HabitCompletionCreate,
    HabitBackfillCreate,
    HabitLeaveCreate,
    TaskCreate,
    TaskUpdate,
    GoalUpdate,
    GoalCreate,
    SubtaskCreate,
    SubtaskUpdate,
    Difficulty,
    Frequency,
)
from app.schemas.daily_workbench import DailyFocusUpdate, QuickTaskCreate
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    PhaseCreate,
    PhaseUpdate,
    MilestoneCreate,
    MilestoneUpdate,
)
from app.schemas.note import FolderCreate, NotebookCreate, NoteCreate, NoteUpdate
from app.models.todo import TaskStatus
from app.services.checkin import CheckinService
from app.services.finance import FinanceService
from app.services.note import NoteService
from app.services.project import ProjectService
from app.services.stats import StatsService
from app.services.todo import TodoService
from app.services.daily_workbench import DailyWorkbenchService
from app.services.user import UserService
from app.services.mcp_access_token import MCPAccessTokenService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Auth context — set by `login` tool, read by all other tools
# ---------------------------------------------------------------------------

_auth_user_id: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "_auth_user_id", default=None
)
_auth_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "_auth_token", default=None
)
_auth_token_authenticated: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "_auth_token_authenticated", default=False
)
_auth_users_by_session: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_token_sessions: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _current_mcp_session():
    """Return the active MCP session, when called from an MCP request."""
    try:
        return request_ctx.get().session
    except LookupError:
        return None


def _set_authenticated_user(user_id: UUID, *, token_authenticated: bool = False) -> None:
    """Persist authentication for the whole MCP session, not one tool call."""
    current_user_id = _auth_user_id.get()
    if current_user_id is not None and current_user_id != user_id:
        raise RuntimeError("MCP session user switch is not allowed")
    session = _current_mcp_session()
    if session is not None:
        bound_user_id = _auth_users_by_session.get(session)
        if bound_user_id is not None and bound_user_id != user_id:
            raise RuntimeError("MCP session user switch is not allowed")
        _auth_users_by_session[session] = user_id
        if token_authenticated or _token_sessions.get(session, False):
            _token_sessions[session] = True
    # Keep the context-local value for stdio and direct unit-test calls.
    _auth_user_id.set(user_id)
    if token_authenticated:
        _auth_token_authenticated.set(True)


def _validate_service_user_id(user_id: UUID) -> None:
    configured_id = os.environ.get("LIFEQUEST_MCP_SERVICE_USER_ID")
    if not configured_id:
        return
    try:
        service_user_id = UUID(configured_id)
    except ValueError as exc:
        raise RuntimeError("LIFEQUEST_MCP_SERVICE_USER_ID 无效") from exc
    if service_user_id != user_id:
        raise RuntimeError("MCP service account 与 Token 用户不一致")

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
    """Resolve user ID from session, context authentication, or MCP token."""
    _ensure_db()
    # 1. Check the authenticated MCP session.
    session = _current_mcp_session()
    if session is not None:
        uid = _auth_users_by_session.get(session)
        if uid:
            if os.environ.get("LIFEQUEST_MCP_SERVICE_USER_ID") and not _token_sessions.get(session, False):
                raise RuntimeError("LIFEQUEST_MCP_SERVICE_USER_ID 必须与有效 MCP Token 一起使用")
            _validate_service_user_id(uid)
            return uid

    # 2. Check the context-local value for stdio/direct calls.
    uid = _auth_user_id.get()
    if uid and (
        not os.environ.get("LIFEQUEST_MCP_SERVICE_USER_ID")
        or _auth_token_authenticated.get()
    ):
        _validate_service_user_id(uid)
        return uid

    # 3. Check the context-local or stdio environment token.
    raw_token = _auth_token.get() or os.environ.get("LIFEQUEST_MCP_TOKEN")
    if raw_token:
        uid = MCPAccessTokenService(db).authenticate(raw_token)
        if uid is None:
            raise RuntimeError("MCP Token 无效或已过期")
        _validate_service_user_id(uid)
        _set_authenticated_user(uid, token_authenticated=True)
        return uid

    if os.environ.get("LIFEQUEST_MCP_SERVICE_USER_ID"):
        raise RuntimeError("LIFEQUEST_MCP_SERVICE_USER_ID 必须与有效 MCP Token 一起使用")
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
    """Convert ORM, Pydantic, date, UUID, and nested values to JSON-safe data."""
    if obj is None:
        return None
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k if isinstance(k, str) else str(_serialize(k)): _serialize(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        return _serialize(obj.model_dump(mode="json"))
    if hasattr(obj, "__table__"):
        # SQLAlchemy model
        return {
            col.name: _serialize(getattr(obj, col.name))
            for col in obj.__table__.columns
        }
    return obj


def _serialize_public_user(user) -> dict:
    return UserResponse.model_validate(user).model_dump(mode="json")


class MCPTokenAuthMiddleware:
    """Authenticate optional SSE Bearer headers while keeping login compatible."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        raw_header = next(
            (value for name, value in scope.get("headers", []) if name.lower() == b"authorization"),
            None,
        )
        if raw_header is None:
            await self.app(scope, receive, send)
            return

        try:
            authorization = raw_header.decode("ascii")
        except UnicodeDecodeError:
            authorization = ""
        match = re.fullmatch(r"Bearer ([^\s]+)", authorization)
        if not match:
            await self._unauthorized(send)
            return

        db = SessionLocal()
        user_token = _auth_token.set(match.group(1))
        user_context = _auth_user_id.set(_auth_user_id.get())
        token_context = _auth_token_authenticated.set(True)
        try:
            user_id = MCPAccessTokenService(db).authenticate(match.group(1))
            if user_id is None:
                await self._unauthorized(send)
                return
            _validate_service_user_id(user_id)
            _set_authenticated_user(user_id, token_authenticated=True)
            await self.app(scope, receive, send)
        finally:
            _auth_user_id.reset(user_context)
            _auth_token_authenticated.reset(token_context)
            _auth_token.reset(user_token)
            db.close()

    @staticmethod
    async def _unauthorized(send):
        body = b'{"detail":"MCP authentication required"}'
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [(b"content-type", b"application/json"), (b"www-authenticate", b"Bearer")],
        })
        await send({"type": "http.response.body", "body": body})


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
            "user": _serialize_public_user(user),
        }
    finally:
        db.close()


@mcp.tool()
def login_with_token(token: str) -> Any:
    """使用 MCP 访问令牌登录当前会话。"""
    db = SessionLocal()
    try:
        _ensure_db()
        user_id = MCPAccessTokenService(db).authenticate(token)
        if user_id is None:
            return {"error": "MCP Token 无效或已过期"}
        user = UserService(db).get_by_id(user_id)
        if not user:
            return {"error": "MCP Token 无效或已过期"}
        _validate_service_user_id(user_id)
        _set_authenticated_user(user_id, token_authenticated=True)
        _auth_token.set(token)
        return {
            "status": "ok",
            "message": f"已登录为 {user.username}",
            "user": _serialize_public_user(user),
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
def create_goal(
    title: str,
    description: str = "",
    difficulty: str = "medium",
    coins_reward: int = 50,
    exp_reward: int = 25,
    deadline: Optional[str] = None,
) -> Any:
    """创建目标。deadline 使用 ISO 8601 格式。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        goal = TodoService(db).create_goal(uid, GoalCreate(
            title=title,
            description=description or None,
            difficulty=Difficulty(difficulty),
            coins_reward=coins_reward,
            exp_reward=exp_reward,
            deadline=datetime.fromisoformat(deadline) if deadline else None,
        ))
        return _serialize(goal)
    finally:
        db.close()


@mcp.tool()
def complete_goal(goal_id: str) -> Any:
    """完成目标并返回领域服务结算结果。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        return _serialize(svc.complete_goal(svc.get_goal_for_user(UUID(goal_id), uid), uid))
    finally:
        db.close()


@mcp.tool()
def delete_goal(goal_id: str) -> Any:
    """删除目标。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        goal = svc.get_goal_for_user(UUID(goal_id), uid)
        svc.delete_goal(goal.id)
        return {"status": "ok", "id": str(goal.id), "message": "Goal deleted"}
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
    phase_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
    start_date: Optional[str] = None,
    priority: str = "medium",
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
            phase_id=UUID(phase_id) if phase_id else None,
            milestone_id=UUID(milestone_id) if milestone_id else None,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            priority=priority,
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
def delete_task(task_id: str) -> Any:
    """删除任务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        task = svc.get_task_for_user(UUID(task_id), uid)
        svc.delete_task(task.id)
        return {"status": "ok", "id": str(task.id), "message": "Task deleted"}
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
    weekdays: Optional[list[int]] = None,
    weekly_target: Optional[int] = None,
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
            weekdays=weekdays,
            weekly_target=weekly_target,
        )
        habit = svc.create_habit(uid, data)
        return _serialize(habit)
    finally:
        db.close()


@mcp.tool()
def complete_habit(habit_id: str, note: Optional[str] = None) -> Any:
    """完成一个习惯打卡。返回更新后的习惯信息（含连续天数、奖励）。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        habit = svc.get_habit_for_user(UUID(habit_id), uid)
        result = svc.complete_habit(habit, uid, HabitCompletionCreate(note=note))
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
    weekdays: Optional[list[int]] = None,
    weekly_target: Optional[int] = None,
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
        if weekdays is not None:
            update_data["weekdays"] = weekdays
        if weekly_target is not None:
            update_data["weekly_target"] = weekly_target
        if not update_data:
            return _serialize(habit)
        return _serialize(svc.update_habit(habit, HabitUpdate(**update_data)))
    finally:
        db.close()


def _get_habit_for_mcp(db, habit_id: str, uid: UUID):
    svc = TodoService(db)
    return svc, svc.get_habit_for_user(UUID(habit_id), uid)


@mcp.tool()
def delete_habit(habit_id: str) -> Any:
    """删除习惯。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc, habit = _get_habit_for_mcp(db, habit_id, uid)
        svc.delete_habit(habit.id)
        return {"status": "ok", "id": str(habit.id), "message": "Habit deleted"}
    finally:
        db.close()


@mcp.tool()
def get_habit_history(
    habit_id: str, start_on: Optional[str] = None, end_on: Optional[str] = None
) -> Any:
    """获取习惯历史。日期使用 ISO 8601 格式。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        return _serialize(svc.get_habit_history(
            UUID(habit_id), uid,
            date.fromisoformat(start_on) if start_on else None,
            date.fromisoformat(end_on) if end_on else None,
        ))
    finally:
        db.close()


@mcp.tool()
def get_habit_pause_intervals(habit_id: str) -> Any:
    """获取习惯暂停区间。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        return _serialize(svc.get_pause_intervals(UUID(habit_id), uid))
    finally:
        db.close()


@mcp.tool()
def get_habit_leave_intervals(habit_id: str) -> Any:
    """获取习惯请假区间。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        return _serialize(svc.get_leave_intervals(UUID(habit_id), uid))
    finally:
        db.close()


@mcp.tool()
def pause_habit(habit_id: str) -> Any:
    """暂停习惯。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc, habit = _get_habit_for_mcp(db, habit_id, uid)
        return _serialize(svc.pause_habit(habit, uid))
    finally:
        db.close()


@mcp.tool()
def resume_habit(habit_id: str) -> Any:
    """恢复习惯。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc, habit = _get_habit_for_mcp(db, habit_id, uid)
        return _serialize(svc.resume_habit(habit, uid))
    finally:
        db.close()


@mcp.tool()
def create_habit_leave(
    habit_id: str, leave_on: str, return_on: str, reason: Optional[str] = None
) -> Any:
    """创建习惯请假区间，日期使用 ISO 8601 格式。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc, habit = _get_habit_for_mcp(db, habit_id, uid)
        return _serialize(svc.create_habit_leave(habit, uid, HabitLeaveCreate(
            leave_on=date.fromisoformat(leave_on),
            return_on=date.fromisoformat(return_on),
            reason=reason,
        )))
    finally:
        db.close()


@mcp.tool()
def delete_habit_leave(habit_id: str, leave_id: str) -> Any:
    """删除习惯请假区间。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc, habit = _get_habit_for_mcp(db, habit_id, uid)
        svc.delete_habit_leave(habit, UUID(leave_id), uid)
        return {"status": "ok", "id": leave_id, "message": "Habit leave deleted"}
    finally:
        db.close()


@mcp.tool()
def backfill_habit(habit_id: str, completed_on: str, note: Optional[str] = None) -> Any:
    """补记习惯，日期使用 ISO 8601 格式。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc, habit = _get_habit_for_mcp(db, habit_id, uid)
        return _serialize(svc.backfill_habit(habit, uid, HabitBackfillCreate(
            completed_on=date.fromisoformat(completed_on), note=note
        )))
    finally:
        db.close()


@mcp.tool()
def create_subtask(task_id: str, title: str) -> Any:
    """创建子任务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        svc.get_task_for_user(UUID(task_id), uid)
        return _serialize(svc.create_subtask(SubtaskCreate(task_id=UUID(task_id), title=title)))
    finally:
        db.close()


@mcp.tool()
def list_subtasks(task_id: str) -> Any:
    """列出任务的子任务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        svc.get_task_for_user(UUID(task_id), uid)
        return _serialize(svc.get_subtasks(UUID(task_id)))
    finally:
        db.close()


@mcp.tool()
def update_subtask(
    subtask_id: str, title: Optional[str] = None, is_completed: Optional[bool] = None
) -> Any:
    """更新子任务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        subtask = svc.get_subtask_for_user(UUID(subtask_id), uid)
        data = SubtaskUpdate(title=title, is_completed=is_completed)
        if is_completed is True:
            return _serialize(svc.complete_subtask(subtask, uid))
        return _serialize(svc.update_subtask(subtask, data))
    finally:
        db.close()


@mcp.tool()
def complete_subtask(subtask_id: str) -> Any:
    """完成子任务并返回领域服务结算结果。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        return _serialize(svc.complete_subtask(svc.get_subtask_for_user(UUID(subtask_id), uid), uid))
    finally:
        db.close()


@mcp.tool()
def delete_subtask(subtask_id: str) -> Any:
    """删除子任务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = TodoService(db)
        subtask = svc.get_subtask_for_user(UUID(subtask_id), uid)
        svc.delete_subtask(subtask.id)
        return {"status": "ok", "id": str(subtask.id), "message": "Subtask deleted"}
    finally:
        db.close()


@mcp.tool()
def get_workbench() -> Any:
    """获取今日工作台。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        return _serialize(DailyWorkbenchService(db).get_workbench(uid))
    finally:
        db.close()


@mcp.tool()
def update_daily_focus(workbench_date: str, revision: int, task_ids: list[str]) -> Any:
    """更新今日重点任务，使用 revision 防止并发覆盖。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = DailyFocusUpdate(
            date=date.fromisoformat(workbench_date),
            revision=revision,
            task_ids=[UUID(task_id) for task_id in task_ids],
        )
        return _serialize(DailyWorkbenchService(db).update_focus(uid, data))
    finally:
        db.close()


@mcp.tool()
def create_quick_task(
    title: str,
    schedule: str = "today",
    due_date: Optional[str] = None,
    request_id: str = "",
) -> Any:
    """创建工作台快速任务，request_id 遵循现有幂等规则。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = QuickTaskCreate(
            title=title,
            schedule=schedule,
            due_date=date.fromisoformat(due_date) if due_date else None,
            request_id=UUID(request_id),
        )
        return _serialize(DailyWorkbenchService(db).create_quick_task(uid, data))
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


def _mcp_debt_type(value: str) -> DebtType:
    """Accept the MCP compatibility alias while preserving schema validation."""
    return DebtType.BORROW if value == "loan" else DebtType(value)


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
def create_account(
    name: str,
    type: str = "cash",
    icon: str = "💰",
    balance: float = 0.0,
    credit_limit: Optional[float] = None,
    billing_day: Optional[int] = None,
    repayment_day: Optional[int] = None,
    interest_rate: Optional[float] = None,
    currency: str = "CNY",
    sort_order: int = 0,
) -> Any:
    """创建账户。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = AccountCreate(
            name=name, type=AccountType(type), icon=icon, balance=balance,
            credit_limit=credit_limit, billing_day=billing_day,
            repayment_day=repayment_day, interest_rate=interest_rate,
            currency=currency, sort_order=sort_order,
        )
        return _serialize(FinanceService(db).create_account(uid, data))
    finally:
        db.close()


@mcp.tool()
def delete_account(account_id: str) -> Any:
    """停用账户。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        account = svc._get_account_for_user(UUID(account_id), uid)
        svc.delete_account(account)
        return {"status": "ok", "id": str(account.id), "message": "Account deleted"}
    finally:
        db.close()


@mcp.tool()
def list_categories() -> Any:
    """列出系统分类和当前用户分类。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        return _serialize(FinanceService(db).get_categories(uid))
    finally:
        db.close()


@mcp.tool()
def create_category(
    name: str,
    type: str,
    icon: str = "📦",
    parent_id: Optional[str] = None,
    sort_order: int = 0,
) -> Any:
    """创建收入或支出分类。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = CategoryCreate(
            name=name, type=CategoryType(type), icon=icon,
            parent_id=UUID(parent_id) if parent_id else None,
            sort_order=sort_order,
        )
        return _serialize(FinanceService(db).create_category(uid, data))
    finally:
        db.close()


@mcp.tool()
def delete_category(category_id: str) -> Any:
    """删除用户分类；系统分类不可删除。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        category = svc.category_repo.get_by_id(UUID(category_id))
        if category is None or (not category.is_system and category.user_id != uid):
            raise ValueError("Category not found")
        svc.delete_category(category, uid)
        return {"status": "ok", "id": str(category.id), "message": "Category deleted"}
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
    category_id: Optional[str] = None,
    to_account_id: Optional[str] = None,
) -> Any:
    """记一笔账。日期使用 ISO 8601，省略时使用中国当天。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        txn_date = date.fromisoformat(date_str) if date_str else timezone.today()
        data = TransactionCreate(
            account_id=UUID(account_id),
            category_id=UUID(category_id) if category_id else None,
            type=FinanceTransactionType(type),
            amount=amount,
            description=description,
            date=txn_date,
            to_account_id=UUID(to_account_id) if to_account_id else None,
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
    page: int = 1,
    page_size: int = 50,
    account_id: Optional[str] = None,
    category_id: Optional[str] = None,
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """查询交易记录，支持分页、账户、分类、类型和日期范围筛选。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        filters = {"page": page, "page_size": page_size}
        if account_id:
            filters["account_id"] = UUID(account_id)
        if category_id:
            filters["category_id"] = UUID(category_id)
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
    clear_to_account_id: bool = False,
) -> Any:
    """更新交易并同步账户余额。只传入需要修改的字段；用 clear_to_account_id 清空转入账户。"""
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
        if clear_to_account_id and to_account_id is not None:
            raise ValueError("to_account_id and clear_to_account_id cannot be used together")
        if clear_to_account_id:
            update_data["to_account_id"] = None
        elif to_account_id is not None:
            update_data["to_account_id"] = UUID(to_account_id)
        if not update_data:
            return _serialize(transaction)
        return _serialize(svc.update_transaction(
            transaction, TransactionUpdate(**update_data), uid
        ))
    finally:
        db.close()


@mcp.tool()
def delete_transaction(transaction_id: str) -> Any:
    """删除交易并由服务层反向结算账户余额。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        transaction = svc.transaction_repo.get_by_id(UUID(transaction_id))
        if transaction is None or transaction.user_id != uid:
            raise ValueError("Transaction not found")
        svc.delete_transaction(transaction)
        return {"status": "ok", "id": str(transaction.id), "message": "Transaction deleted"}
    finally:
        db.close()


@mcp.tool()
def list_budgets() -> Any:
    """列出当前用户预算及其使用情况。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        return _serialize(FinanceService(db).get_budgets(uid))
    finally:
        db.close()


@mcp.tool()
def create_budget(
    amount: float,
    category_id: Optional[str] = None,
    period: str = "monthly",
    start_date: Optional[str] = None,
) -> Any:
    """创建预算。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = BudgetCreate(
            amount=amount,
            category_id=UUID(category_id) if category_id else None,
            period=BudgetPeriod(period),
            start_date=date.fromisoformat(start_date) if start_date else None,
        )
        return _serialize(FinanceService(db).create_budget(uid, data))
    finally:
        db.close()


@mcp.tool()
def delete_budget(budget_id: str) -> Any:
    """删除预算。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        budget = svc.budget_repo.get_by_id(UUID(budget_id))
        if budget is None or budget.user_id != uid:
            raise ValueError("Budget not found")
        svc.delete_budget(budget)
        return {"status": "ok", "id": str(budget.id), "message": "Budget deleted"}
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
def list_recurring_transactions() -> Any:
    """列出当前用户的定期流水。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        return _serialize(FinanceService(db).get_recurring(uid))
    finally:
        db.close()


@mcp.tool()
def create_recurring_transaction(
    account_id: str,
    type: str,
    amount: float,
    frequency: str,
    next_date: str,
    category_id: Optional[str] = None,
    description: str = "",
) -> Any:
    """创建定期流水。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = RecurringCreate(
            account_id=UUID(account_id),
            category_id=UUID(category_id) if category_id else None,
            type=FinanceTransactionType(type), amount=amount,
            description=description, frequency=RecurFrequency(frequency),
            next_date=date.fromisoformat(next_date),
        )
        return _serialize(FinanceService(db).create_recurring(uid, data))
    finally:
        db.close()


@mcp.tool()
def trigger_recurring_transaction(recurring_id: str) -> Any:
    """触发定期流水；重复触发同一日期由服务层幂等处理。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        recurring = svc.recurring_repo.get_by_id(UUID(recurring_id))
        if recurring is None or recurring.user_id != uid:
            raise ValueError("Recurring transaction not found")
        return _serialize(svc.trigger_recurring(recurring))
    finally:
        db.close()


@mcp.tool()
def delete_recurring_transaction(recurring_id: str) -> Any:
    """删除定期流水。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        recurring = svc.recurring_repo.get_by_id(UUID(recurring_id))
        if recurring is None or recurring.user_id != uid:
            raise ValueError("Recurring transaction not found")
        svc.delete_recurring(recurring)
        return {"status": "ok", "id": str(recurring.id), "message": "Recurring transaction deleted"}
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
            update_data["type"] = _mcp_debt_type(type)
        if due_date is not None:
            update_data["due_date"] = date.fromisoformat(due_date)
        if status is not None:
            update_data["status"] = DebtStatus(status)
        if not update_data:
            return _serialize(debt)
        return _serialize(svc.update_debt(debt, DebtUpdate(**update_data)))
    finally:
        db.close()


@mcp.tool()
def list_debts(status: Optional[str] = None) -> Any:
    """列出当前用户债务，可按状态筛选。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        return _serialize(FinanceService(db).get_debts(uid, status=status))
    finally:
        db.close()


@mcp.tool()
def create_debt(
    creditor: str,
    type: str,
    amount: float,
    remaining: float,
    interest_rate: float = 0.0,
    description: str = "",
    due_date: Optional[str] = None,
) -> Any:
    """创建债务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = DebtCreate(
            creditor=creditor, type=_mcp_debt_type(type), amount=amount,
            remaining=remaining, interest_rate=interest_rate,
            description=description,
            due_date=date.fromisoformat(due_date) if due_date else None,
        )
        return _serialize(FinanceService(db).create_debt(uid, data))
    finally:
        db.close()


@mcp.tool()
def delete_debt(debt_id: str) -> Any:
    """删除债务。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = FinanceService(db)
        debt = svc.debt_repo.get_by_id(UUID(debt_id))
        if debt is None or debt.user_id != uid:
            raise ValueError("Debt not found")
        svc.delete_debt(debt)
        return {"status": "ok", "id": str(debt.id), "message": "Debt deleted"}
    finally:
        db.close()


@mcp.tool()
def add_debt_payment(
    debt_id: str,
    amount: float,
    description: str = "",
    date_str: Optional[str] = None,
) -> Any:
    """为债务添加还款；金额和剩余债务由服务层校验和更新。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = DebtPaymentCreate(
            amount=amount, description=description,
            date=date.fromisoformat(date_str) if date_str else timezone.today(),
        )
        return _serialize(FinanceService(db).add_payment(UUID(debt_id), uid, data))
    finally:
        db.close()


# ===================== 项目 =====================


def _serialize_project_stats(stats: dict) -> dict:
    """Flatten project service stats into a stable MCP response."""
    project = stats["project"]
    return {
        "id": _serialize(project.id),
        "user_id": _serialize(project.user_id),
        "name": project.name,
        "description": project.description,
        "color": project.color,
        "icon": project.icon,
        "status": _serialize(project.status),
        "start_date": _serialize(project.start_date),
        "end_date": _serialize(project.end_date),
        "created_at": _serialize(project.created_at),
        "updated_at": _serialize(project.updated_at),
        "total_tasks": stats["total_tasks"],
        "completed_tasks": stats["completed_tasks"],
        "progress": stats["progress"],
    }


@mcp.tool()
def create_project(
    name: str,
    description: str = "",
    color: str = "#0EA5E9",
    icon: str = "folder",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """创建项目。日期使用 YYYY-MM-DD。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        data = ProjectCreate(
            name=name,
            description=description or None,
            color=color,
            icon=icon,
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
        )
        return _serialize_project_stats(ProjectService(db).create_project(uid, data))
    finally:
        db.close()


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
def delete_project(project_id: str) -> Any:
    """删除项目并解除当前用户任务的项目层级关联。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        project = svc.get_project_for_user(UUID(project_id), uid)
        svc.delete_project(project)
        return {"status": "ok", "id": str(project.id), "message": "Project deleted"}
    finally:
        db.close()


@mcp.tool()
def complete_project(project_id: str) -> Any:
    """完成项目并返回更新后的统计信息。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        project = svc.get_project_for_user(UUID(project_id), uid)
        completed = svc.complete_project(project)
        return _serialize_project_stats(svc._compute_project_stats(completed))
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
def create_project_phase(
    project_id: str,
    name: str,
    description: str = "",
    sort_order: int = 0,
) -> Any:
    """在项目下创建阶段。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        project_uuid = UUID(project_id)
        svc.get_project_for_user(project_uuid, uid)
        phase = svc.create_phase(
            project_uuid,
            PhaseCreate(
                name=name,
                description=description or None,
                sort_order=sort_order,
            ),
        )
        return _serialize(phase)
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
def delete_project_phase(phase_id: str) -> Any:
    """删除项目阶段；阶段仍有任务时由服务层拒绝。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        phase = svc.phase_repo.get_by_id(UUID(phase_id))
        if phase is None:
            raise ValueError("Phase not found")
        svc.get_project_for_user(phase.project_id, uid)
        svc.delete_phase(phase)
        return {"status": "ok", "id": str(phase.id), "message": "Phase deleted"}
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
def create_project_milestone(
    project_id: str,
    name: str,
    description: str = "",
    due_date: Optional[str] = None,
    sort_order: int = 0,
) -> Any:
    """在项目下创建里程碑；due_date 使用 YYYY-MM-DD。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        project_uuid = UUID(project_id)
        svc.get_project_for_user(project_uuid, uid)
        milestone = svc.create_milestone(
            project_uuid,
            MilestoneCreate(
                name=name,
                description=description or None,
                due_date=date.fromisoformat(due_date) if due_date else None,
                sort_order=sort_order,
            ),
        )
        return _serialize(milestone)
    finally:
        db.close()


@mcp.tool()
def delete_project_milestone(milestone_id: str) -> Any:
    """删除项目里程碑并解除当前用户任务的里程碑关联。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        milestone = svc.milestone_repo.get_by_id(UUID(milestone_id))
        if milestone is None:
            raise ValueError("Milestone not found")
        svc.get_project_for_user(milestone.project_id, uid)
        svc.delete_milestone(milestone)
        return {"status": "ok", "id": str(milestone.id), "message": "Milestone deleted"}
    finally:
        db.close()


@mcp.tool()
def reach_project_milestone(milestone_id: str) -> Any:
    """达成项目里程碑。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        milestone = svc.milestone_repo.get_by_id(UUID(milestone_id))
        if milestone is None:
            raise ValueError("Milestone not found")
        svc.get_project_for_user(milestone.project_id, uid)
        return _serialize(svc.reach_milestone(milestone))
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
    deadline: Optional[str] = None,
    phase_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
    start_date: Optional[str] = None,
    priority: str = "medium",
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
            deadline=datetime.fromisoformat(deadline) if deadline else None,
            phase_id=UUID(phase_id) if phase_id else None,
            milestone_id=UUID(milestone_id) if milestone_id else None,
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            priority=priority,
        )
        task = svc.create_project_task(uid, UUID(project_id), data)
        return _serialize(task)
    finally:
        db.close()


@mcp.tool()
def list_project_tasks(
    project_id: str,
    phase_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
) -> Any:
    """列出项目任务，可按阶段或里程碑筛选。"""
    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        project_uuid = UUID(project_id)
        svc.get_project_for_user(project_uuid, uid)
        phase_uuid = UUID(phase_id) if phase_id else None
        milestone_uuid = UUID(milestone_id) if milestone_id else None
        if phase_uuid:
            svc.get_phase_for_project(phase_uuid, project_uuid)
        if milestone_uuid:
            svc.get_milestone_for_project(milestone_uuid, project_uuid)
        tasks = svc.get_project_tasks(project_uuid, uid, phase_uuid, milestone_uuid)
        return [_serialize(task) for task in tasks]
    finally:
        db.close()


@mcp.tool()
def move_project_task(
    task_id: str,
    project_id: Optional[str] = None,
    phase_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
    status: Optional[str] = None,
    clear_project: bool = False,
    clear_phase: bool = False,
    clear_milestone: bool = False,
) -> Any:
    """移动项目任务；clear_* 用于显式清空关联，省略字段保持不变。"""
    if clear_project and project_id is not None:
        raise ValueError("project_id 与 clear_project 不能同时使用")
    if clear_phase and phase_id is not None:
        raise ValueError("phase_id 与 clear_phase 不能同时使用")
    if clear_milestone and milestone_id is not None:
        raise ValueError("milestone_id 与 clear_milestone 不能同时使用")

    db = SessionLocal()
    try:
        uid = _resolve_user_id(db)
        svc = ProjectService(db)
        task = TodoService(db).get_task_for_user(UUID(task_id), uid)
        changes = {}
        if project_id is not None:
            changes["project_id"] = UUID(project_id)
        elif clear_project:
            changes["project_id"] = None
        if phase_id is not None:
            changes["phase_id"] = UUID(phase_id)
        elif clear_phase:
            changes["phase_id"] = None
        if milestone_id is not None:
            changes["milestone_id"] = UUID(milestone_id)
        elif clear_milestone:
            changes["milestone_id"] = None
        if status is not None:
            changes["status"] = TaskStatus(status)
        moved = svc.move_task(task, uid, **changes)
        return _serialize(moved)
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
        return _serialize_public_user(user)
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
        import uvicorn

        app = mcp.sse_app()
        app.add_middleware(MCPTokenAuthMiddleware)
        config = uvicorn.Config(app, host=args.host, port=args.port)
        uvicorn.Server(config).run()
    else:
        mcp.run(transport="stdio")
