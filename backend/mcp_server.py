"""
LifeQuest MCP Server — exposes LifeQuest as MCP tools for AI agents.

Usage:
    # stdio (Claude Desktop / Claude Code)
    python backend/mcp_server.py

    # SSE (remote / HTTP)
    python backend/mcp_server.py --transport sse --port 3001

Environment:
    LIFEQUEST_USER_ID  — default user UUID (optional; falls back to first user)
"""

import argparse
import os
import sys
from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

# Ensure backend package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.schemas.finance import (
    AccountCreate,
    TransactionCreate,
    FinanceTransactionType,
)
from app.schemas.todo import (
    HabitCreate,
    TaskCreate,
    Difficulty,
    Frequency,
)
from app.services.checkin import CheckinService
from app.services.finance import FinanceService
from app.services.note import NoteService
from app.services.project import ProjectService
from app.services.stats import StatsService
from app.services.todo import TodoService
from app.services.user import UserService

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
        pass  # best-effort; tables may not exist yet
    _db_initialized = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_user_id(db) -> UUID:
    """Resolve the active user ID from env or first user in DB."""
    _ensure_db()
    env_id = os.environ.get("LIFEQUEST_USER_ID")
    if env_id:
        return UUID(env_id)
    user = db.query(User).first()
    if not user:
        raise RuntimeError("No users found in database. Register a user first.")
    return user.id


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
