import logging
import os

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
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


@app.get("/api/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Health check database probe failed")
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


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
        raise
    # Migrate old notes/folders tables to note_nodes
    migrate_db = SessionLocal()
    try:
        NoteService.migrate_old_data(migrate_db)
    except Exception:
        logger.exception("Note data migration failed")
        migrate_db.rollback()
        raise
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
        raise
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

# MCP SSE server — subprocess on internal port, proxied through explicit routes.
_mcp_process = None

@app.on_event("startup")
def start_mcp_server():
    """Start the MCP SSE server as a subprocess on an internal port."""
    global _mcp_process
    if os.environ.get("MCP_AUTOSTART", "false").lower() != "true":
        logger.info("MCP autostart disabled; use supervisor to run the MCP service")
        return
    import subprocess, sys
    mcp_port = int(os.environ.get("MCP_PORT", "3001"))
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"),
           "--transport", "sse", "--host", "127.0.0.1", "--port", str(mcp_port)]
    try:
        _mcp_process = subprocess.Popen(cmd)
        logger.info("MCP server started on port %d (pid=%d)", mcp_port, _mcp_process.pid)
    except Exception:
        logger.exception("Failed to start MCP server")

@app.on_event("shutdown")
def stop_mcp_server():
    if _mcp_process and _mcp_process.poll() is None:
        _mcp_process.terminate()
        logger.info("MCP server stopped")


# MCP proxy routes — explicit paths that match before SPA catch-all
import httpx

@app.api_route("/mcp/sse", methods=["GET"])
async def mcp_sse_proxy(request: Request):
    """Proxy SSE stream to MCP subprocess."""
    mcp_port = int(os.environ.get("MCP_PORT", "3001"))
    url = f"http://127.0.0.1:{mcp_port}/sse"
    client = httpx.AsyncClient()
    try:
        req = client.build_request("GET", url, headers=dict(request.headers))
        response = await client.send(req, stream=True)
    except httpx.HTTPError:
        await client.aclose()
        return Response(content='{"detail":"MCP service unavailable"}', status_code=503, media_type="application/json")

    async def stream():
        async for chunk in response.aiter_bytes():
            yield chunk
        await response.aclose()
        await client.aclose()

    return StreamingResponse(
        stream(),
        status_code=response.status_code,
        media_type="text/event-stream",
        headers=dict(response.headers),
    )

@app.api_route("/mcp/messages", methods=["POST"])
@app.api_route("/mcp/messages/", methods=["POST"])
async def mcp_messages_proxy(request: Request):
    """Proxy JSON-RPC messages to MCP subprocess."""
    mcp_port = int(os.environ.get("MCP_PORT", "3001"))
    path = "/messages/" if request.url.path.endswith("/") else "/messages"
    qs = f"?{request.url.query}" if request.url.query else ""
    url = f"http://127.0.0.1:{mcp_port}{path}{qs}"
    body = await request.body()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, content=body, headers=dict(request.headers))
    except httpx.HTTPError:
        return Response(content='{"detail":"MCP service unavailable"}', status_code=503, media_type="application/json")
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

logger.info("MCP proxy registered at /mcp/sse and /mcp/messages")


# Serve frontend static files (production mode)
_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "dist")
_frontend_dist = os.path.abspath(_frontend_dist)
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="frontend-assets")

    from fastapi.responses import FileResponse, JSONResponse

    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        """Serve index.html for unmatched GET requests (SPA client-side routing)."""
        path = request.url.path
        if request.method == "GET" and not path.startswith(("/api/", "/mcp/", "/uploads/")):
            return FileResponse(os.path.join(_frontend_dist, "index.html"))
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
