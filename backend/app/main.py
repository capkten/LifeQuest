import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.services.note import NoteService
from app.api import auth, users, notes, todos, shop, backpack, achievements, checkin, titles, coins, calendar, stats, finance, projects

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LifeQuest", version="1.0.0")


logger = logging.getLogger(__name__)


def _migrate_columns():
    """Add missing columns to existing tables without a full migration tool."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        # habits.last_completed_at
        habit_cols = {c["name"] for c in inspector.get_columns("habits")}
        if "last_completed_at" not in habit_cols:
            conn.execute(text("ALTER TABLE habits ADD COLUMN last_completed_at DATETIME"))
            logger.info("Migration: added habits.last_completed_at")

        # users.total_coins_earned
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "total_coins_earned" not in user_cols:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN total_coins_earned INTEGER NOT NULL DEFAULT 0"
            ))
            # Backfill from current coins balance for existing users
            conn.execute(text(
                "UPDATE users SET total_coins_earned = coins WHERE total_coins_earned = 0"
            ))
            logger.info("Migration: added users.total_coins_earned")

        # project management columns on tasks table
        task_cols = {c["name"] for c in inspector.get_columns("tasks")}
        new_task_cols = {
            "project_id": "VARCHAR(36)",
            "phase_id": "VARCHAR(36)",
            "milestone_id": "VARCHAR(36)",
            "start_date": "DATETIME",
            "priority": "VARCHAR(10) NOT NULL DEFAULT 'medium'",
            "sort_order": "INTEGER NOT NULL DEFAULT 0",
        }
        for col_name, col_def in new_task_cols.items():
            if col_name not in task_cols:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}"))
                logger.info("Migration: added tasks.%s", col_name)

        # finance_transactions.recurring_id
        txn_cols = {c["name"] for c in inspector.get_columns("finance_transactions")}
        if "recurring_id" not in txn_cols:
            conn.execute(text(
                "ALTER TABLE finance_transactions ADD COLUMN recurring_id VARCHAR(36)"
            ))
            logger.info("Migration: added finance_transactions.recurring_id")


@app.on_event("startup")
def startup_event():
    """Seed default achievements on application startup."""
    try:
        _migrate_columns()
    except Exception:
        logger.exception("Column migration failed")
    # Migrate old notes/folders tables to note_nodes
    migrate_db = SessionLocal()
    try:
        NoteService.migrate_old_data(migrate_db)
    except Exception:
        logger.exception("Note data migration failed")
        migrate_db.rollback()
    finally:
        migrate_db.close()
    db = SessionLocal()
    try:
        from app.services.achievement import AchievementService

        service = AchievementService(db)
        service.seed_achievements()
        # Seed default titles
        from app.services.title import TitleService
        title_service = TitleService(db)
        title_service.seed_titles()
        # Seed default finance categories
        from app.services.finance import FinanceService
        FinanceService.seed_categories(db)
    except Exception:
        logger.exception("Seed data failed")
    finally:
        db.close()


# Mount static files directory for uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware
_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(notes.router)
app.include_router(todos.router)
app.include_router(shop.router)
app.include_router(backpack.router)
app.include_router(achievements.router)
app.include_router(checkin.router)
app.include_router(titles.router)
app.include_router(coins.router)
app.include_router(calendar.router)
app.include_router(stats.router)
app.include_router(finance.router)
app.include_router(projects.router)

# MCP server runs as a separate process (see mcp_server.py).
# Start both with: python start_all.py


# Serve frontend static files (production mode)
_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "dist")
_frontend_dist = os.path.abspath(_frontend_dist)
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="frontend-assets")

    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback — serves index.html for client-side routes."""
        file_path = os.path.join(_frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_frontend_dist, "index.html"))
