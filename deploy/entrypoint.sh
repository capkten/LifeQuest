#!/bin/bash
set -e

DATA_DIR="/app/data"

# Generate .env if not exists
if [ ! -f "$DATA_DIR/.env" ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > "$DATA_DIR/.env" << EOF
SECRET_KEY=$SECRET_KEY
DATABASE_URL=sqlite:////app/data/lifequest.db
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ORIGINS=http://localhost,http://127.0.0.1
EOF
    echo "[entrypoint] Generated .env in $DATA_DIR"
fi

# Link .env into backend working dir
ln -sf "$DATA_DIR/.env" /app/backend/.env

# Ensure data directories exist
mkdir -p "$DATA_DIR/uploads/avatars" \
         "$DATA_DIR/uploads/notes" \
         "$DATA_DIR/notes_data"

# Touch database file if not exists
touch "$DATA_DIR/lifequest.db"

# Initialize database tables
echo "[entrypoint] Initializing database..."
cd /app/backend
python3 -c "
from app.database import engine, Base
from app.models import *
Base.metadata.create_all(bind=engine)
print('[entrypoint] Database tables ready.')
"

# Seed data
echo "[entrypoint] Seeding data..."
python3 -c "
from app.database import SessionLocal
from app.services.achievement import AchievementService
from app.services.title import TitleService
from app.services.finance import FinanceService
from app.services.note import NoteService

db = SessionLocal()
try:
    NoteService.migrate_old_data(db)
except: pass
try:
    AchievementService(db).seed_achievements()
    TitleService(db).seed_titles()
    FinanceService.seed_categories(db)
    print('[entrypoint] Seed data loaded.')
except Exception as e:
    print(f'[entrypoint] Seed warning: {e}')
finally:
    db.close()
"

echo "[entrypoint] Starting services..."
exec supervisord -c /etc/supervisor/conf.d/lifequest.conf
