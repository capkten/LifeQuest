#!/bin/bash
# LifeQuest - Server Installation Script
# For Ubuntu/Debian (clean server, no pre-installed environment)
# Usage: Run this script on the server as root or with sudo

set -e

echo "========================================="
echo "  LifeQuest Server Installation"
echo "========================================="

# Configuration
APP_DIR="/opt/lifequest"
APP_USER="lifequest"
DOMAIN_OR_IP=$(hostname -I | awk '{print $1}')

# Step 1: System update and base packages
echo "[1/8] Installing system packages..."
apt-get update -y
apt-get install -y curl wget git nginx software-properties-common build-essential

# Step 2: Install Python 3.11+
echo "[2/8] Installing Python..."
if ! command -v python3 &> /dev/null; then
    apt-get install -y python3 python3-pip python3-venv
fi
python3 --version

# Step 3: Install Node.js 20 LTS
echo "[3/8] Installing Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
node --version
npm --version

# Step 4: Create app user and directory
echo "[4/8] Setting up application directory..."
if ! id "$APP_USER" &>/dev/null; then
    useradd --system --shell /bin/false --home "$APP_DIR" "$APP_USER"
fi
mkdir -p "$APP_DIR"
mkdir -p "$APP_DIR/backend/uploads/avatars"
mkdir -p "$APP_DIR/backend/uploads/notes"
mkdir -p "$APP_DIR/backend/notes_data"

# Step 5: Setup Python virtual environment and install backend dependencies
echo "[5/8] Setting up backend..."
cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install fastapi uvicorn[standard] sqlalchemy python-jose[cryptography] passlib[bcrypt] \
        python-multipart pydantic[email] pydantic-settings
fi

# Generate .env file if it doesn't exist
if [ ! -f ".env" ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > .env << EOF
SECRET_KEY=$SECRET_KEY
DATABASE_URL=sqlite:///./lifequest.db
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ORIGINS=http://${DOMAIN_OR_IP},http://localhost
EOF
    echo "  Generated .env with random SECRET_KEY"
fi

# Initialize database
echo "  Initializing database..."
python3 -c "
from app.database import engine, Base
from app.models import *
Base.metadata.create_all(bind=engine)
print('  Database tables created.')
"

# Seed data
echo "  Seeding initial data..."
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
    print('  Seed data loaded.')
except Exception as e:
    print(f'  Seed warning: {e}')
finally:
    db.close()
"

deactivate

# Step 6: Build frontend
echo "[6/8] Building frontend..."
cd "$APP_DIR/frontend"

# Update frontend API proxy target for production
# In production, nginx handles routing, so no proxy needed

npm install
npm run build
echo "  Frontend built to dist/"

# Step 7: Configure Nginx
echo "[7/8] Configuring Nginx..."
cat > /etc/nginx/sites-available/lifequest << 'NGINX'
server {
    listen 80;
    server_name _;

    # Frontend (static files)
    root /opt/lifequest/frontend/dist;
    index index.html;

    # API reverse proxy to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Uploads reverse proxy
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # Vue Router history mode - fallback to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
    gzip_min_length 256;
}
NGINX

ln -sf /etc/nginx/sites-available/lifequest /etc/nginx/sites-enabled/lifequest
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Step 8: Configure Systemd service for backend
echo "[8/8] Configuring backend service..."
cat > /etc/systemd/system/lifequest.service << EOF
[Unit]
Description=LifeQuest Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/lifequest/backend
Environment="PATH=/opt/lifequest/backend/venv/bin"
EnvironmentFile=/opt/lifequest/backend/.env
ExecStart=/opt/lifequest/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Set permissions
chown -R $APP_USER:$APP_USER "$APP_DIR" 2>/dev/null || true
chmod -R 755 "$APP_DIR/backend/uploads" 2>/dev/null || true

systemctl daemon-reload
systemctl enable lifequest
systemctl start lifequest
systemctl enable nginx
systemctl start nginx

echo ""
echo "========================================="
echo "  LifeQuest deployed successfully!"
echo "========================================="
echo ""
echo "  Access: http://${DOMAIN_OR_IP}"
echo "  Backend API: http://${DOMAIN_OR_IP}:8000"
echo ""
echo "  Service management:"
echo "    systemctl status lifequest"
echo "    systemctl restart lifequest"
echo "    journalctl -u lifequest -f"
echo ""
echo "  App directory: $APP_DIR"
echo "  Database: $APP_DIR/backend/lifequest.db"
echo "  Logs: journalctl -u lifequest"
echo ""
