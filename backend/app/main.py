from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.database import engine, Base, SessionLocal
from app.services.note import NoteService
from app.api import auth, users, notes, todos, shop, backpack, achievements

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LifeQuest", version="1.0.0")


def _migrate_columns():
    """Add missing columns to existing tables without a full migration tool."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        # habits.last_completed_at
        habit_cols = {c["name"] for c in inspector.get_columns("habits")}
        if "last_completed_at" not in habit_cols:
            conn.execute(text("ALTER TABLE habits ADD COLUMN last_completed_at DATETIME"))

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


@app.on_event("startup")
def startup_event():
    """Seed default achievements on application startup."""
    _migrate_columns()
    # Migrate old notes/folders tables to note_nodes
    migrate_db = SessionLocal()
    try:
        NoteService.migrate_old_data(migrate_db)
    finally:
        migrate_db.close()
    db = SessionLocal()
    try:
        from app.services.achievement import AchievementService

        service = AchievementService(db)
        service.seed_achievements()
    finally:
        db.close()


# Mount static files directory for uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


@app.get("/")
def root():
    return {"message": "Welcome to LifeQuest API"}
