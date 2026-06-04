#!/bin/bash
# LifeQuest - One-Click Remote Deployment
# Uploads code to server and runs installation
#
# Usage:
#   ./deploy.sh <server_ip> <username> [password]
#
# Examples:
#   ./deploy.sh 192.168.1.100 root mypassword
#   ./deploy.sh 192.168.1.100 root              # will prompt for password
#
# Prerequisites:
#   - sshpass installed (brew install sshpass / apt install sshpass)
#   - Server: Ubuntu/Debian with SSH enabled

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVER_IP="${1}"
USERNAME="${2}"
PASSWORD="${3}"

if [ -z "$SERVER_IP" ] || [ -z "$USERNAME" ]; then
    echo -e "${RED}Usage: ./deploy.sh <server_ip> <username> [password]${NC}"
    echo ""
    echo "  ./deploy.sh 192.168.1.100 root mypassword"
    echo "  ./deploy.sh 192.168.1.100 root"
    exit 1
fi

# Check sshpass
if [ -n "$PASSWORD" ] && ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}sshpass not found. Installing...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install hudochenkov/sshpass/sshpass
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y sshpass
    else
        echo -e "${RED}Please install sshpass manually${NC}"
        exit 1
    fi
fi

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"
if [ -n "$PASSWORD" ]; then
    SSH_PREFIX="sshpass -p '${PASSWORD}'"
else
    SSH_PREFIX=""
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  LifeQuest Remote Deployment${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "  Server: ${USERNAME}@${SERVER_IP}"
echo ""

# Test connection
echo -e "${YELLOW}[1/5] Testing SSH connection...${NC}"
eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" "echo '  Connection OK'" || {
    echo -e "${RED}  Failed to connect. Check credentials and SSH access.${NC}"
    exit 1
}

# Create temp archive (exclude heavy/unnecessary dirs)
echo -e "${YELLOW}[2/5] Packaging project...${NC}"
TEMP_TAR="/tmp/lifequest-deploy-$(date +%s).tar.gz"
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
    --exclude='.git' \
    --exclude='.superpowers' \
    --exclude='design-system' \
    .
echo "  Archive: $(du -h "$TEMP_TAR" | cut -f1)"

# Upload
echo -e "${YELLOW}[3/5] Uploading to server...${NC}"
eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" "mkdir -p /opt/lifequest"
eval $SSH_PREFIX scp $SSH_OPTS "$TEMP_TAR" "${USERNAME}@${SERVER_IP}:/tmp/lifequest.tar.gz"
rm -f "$TEMP_TAR"
echo "  Upload complete"

# Extract on server
echo -e "${YELLOW}[4/5] Extracting on server...${NC}"
eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" \
    "cd /opt/lifequest && tar -xzf /tmp/lifequest.tar.gz && rm /tmp/lifequest.tar.gz"
echo "  Extracted to /opt/lifequest"

# Run installation
echo -e "${YELLOW}[5/5] Installing on server (may take 3-5 minutes)...${NC}"
echo ""
eval $SSH_PREFIX ssh $SSH_OPTS "${USERNAME}@${SERVER_IP}" \
    "chmod +x /opt/lifequest/deploy/install.sh && bash /opt/lifequest/deploy/install.sh"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "  App: ${GREEN}http://${SERVER_IP}${NC}"
echo ""
echo "  Commands:"
echo "    ssh ${USERNAME}@${SERVER_IP} 'systemctl status lifequest'"
echo "    ssh ${USERNAME}@${SERVER_IP} 'journalctl -u lifequest -f'"
echo "    ssh ${USERNAME}@${SERVER_IP} 'systemctl restart lifequest'"
echo ""
