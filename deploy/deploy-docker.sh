#!/bin/bash
# LifeQuest - Docker Deployment Script
# Builds and starts the application in Docker containers
#
# Usage:
#   ./deploy-docker.sh <server_ip> <username> [password]
#
# Or deploy locally:
#   ./deploy-docker.sh local

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ "$1" = "local" ]; then
    echo -e "${GREEN}[Local] Building and starting LifeQuest...${NC}"
    cd "$SCRIPT_DIR"
    mkdir -p data
    docker compose up -d --build
    echo ""
    echo -e "${GREEN}LifeQuest is running at http://localhost${NC}"
    echo ""
    echo "  Logs:    docker compose logs -f"
    echo "  Stop:    docker compose down"
    echo "  Restart: docker compose restart"
    echo ""
    echo "  Data directory: ./data/"
    echo "    data/lifequest.db    — database"
    echo "    data/uploads/        — uploaded files"
    echo "    data/notes_data/     — note files"
    echo "    data/.env            — configuration"
    echo ""
    exit 0
fi

SERVER_IP="${1}"
USERNAME="${2}"
PASSWORD="${3}"

if [ -z "$SERVER_IP" ] || [ -z "$USERNAME" ]; then
    echo -e "${RED}Usage:${NC}"
    echo "  ./deploy-docker.sh local                    # deploy locally"
    echo "  ./deploy-docker.sh <ip> <user> [password]   # deploy to server"
    exit 1
fi

# Check sshpass
if [ -n "$PASSWORD" ] && ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}sshpass not found. Installing...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install hudochenkov/sshpass/sshpass
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y sshpass
    fi
fi

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"
if [ -n "$PASSWORD" ]; then
    SSH_PREFIX="sshpass -p '${PASSWORD}'"
else
    SSH_PREFIX=""
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  LifeQuest Docker Deployment${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""

# Test connection
echo -e "${YELLOW}[1/4] Testing connection...${NC}"
eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" "echo '  OK'" || {
    echo -e "${RED}  Connection failed${NC}"; exit 1
}

# Install Docker if needed
echo -e "${YELLOW}[2/4] Ensuring Docker is installed...${NC}"
eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" "
    if ! command -v docker &>/dev/null; then
        echo '  Installing Docker...'
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker && systemctl start docker
    fi
    docker --version
    if ! docker compose version &>/dev/null; then
        echo '  Installing docker-compose-plugin...'
        apt-get update -y && apt-get install -y docker-compose-plugin
    fi
    docker compose version
"

# Package and upload
echo -e "${YELLOW}[3/4] Uploading project...${NC}"
TEMP_TAR="/tmp/lifequest-docker-$(date +%s).tar.gz"
cd "$SCRIPT_DIR"
tar -czf "$TEMP_TAR" \
    --exclude='backend/__pycache__' \
    --exclude='backend/venv' \
    --exclude='backend/*.db' \
    --exclude='backend/*.db-journal' \
    --exclude='backend/uploads' \
    --exclude='backend/notes_data' \
    --exclude='backend/.env' \
    --exclude='frontend/node_modules' \
    --exclude='frontend/dist' \
    --exclude='data' \
    --exclude='.git' \
    --exclude='.superpowers' \
    --exclude='design-system' \
    .
echo "  Archive: $(du -h "$TEMP_TAR" | cut -f1)"
eval $SSH_PREFIX scp $SSH_OPTS "$TEMP_TAR" "${USERNAME}@${SERVER_IP}:/tmp/lifequest.tar.gz"
rm -f "$TEMP_TAR"

eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" "
    mkdir -p /opt/lifequest
    cd /opt/lifequest
    tar -xzf /tmp/lifequest.tar.gz
    rm /tmp/lifequest.tar.gz
    mkdir -p data
"

# Build and start
echo -e "${YELLOW}[4/4] Building and starting containers...${NC}"
eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" "
    cd /opt/lifequest
    docker compose up -d --build
"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "  App: ${GREEN}http://${SERVER_IP}${NC}"
echo ""
echo "  Manage (SSH into server first):"
echo "    cd /opt/lifequest"
echo "    docker compose logs -f          # view logs"
echo "    docker compose restart           # restart"
echo "    docker compose down              # stop"
echo "    docker compose up -d --build     # rebuild"
echo ""
echo "  Persistent data:"
echo "    /opt/lifequest/data/lifequest.db"
echo "    /opt/lifequest/data/uploads/"
echo "    /opt/lifequest/data/notes_data/"
echo "    /opt/lifequest/data/.env"
echo ""
