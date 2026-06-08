#!/bin/bash
# LifeQuest - 一键部署脚本 (无 nginx，前后端同端口)
# 用法: cd /root/LifeQuest && bash deploy/deploy-server.sh
set -e

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_PORT="${PORT:-8000}"
IP=$(hostname -I | awk '{print $1}')

echo "========================================="
echo "  LifeQuest 一键部署"
echo "  目录: $APP_DIR"
echo "  端口: $APP_PORT"
echo "========================================="

# 1. 系统依赖
echo "[1/5] 安装系统依赖..."
apt-get update -y -qq
apt-get install -y -qq python3-venv build-essential > /dev/null 2>&1
echo "  done"

# 2. 后端
echo "[2/5] 配置后端..."
cd "$APP_DIR/backend"

pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ -q

mkdir -p uploads/avatars uploads/notes notes_data

if [ ! -f ".env" ]; then
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > .env << EOF
SECRET_KEY=$SECRET_KEY
DATABASE_URL=sqlite:///./lifequest.db
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
EOF
  echo "  .env 已生成"
else
  echo "  .env 已存在，跳过"
fi

# 初始化数据库 + 种子数据（startup 事件也会做，这里提前确保）
python3 -c "
from app.database import engine, Base
from app.models import *
Base.metadata.create_all(bind=engine)
" 2>/dev/null
echo "  数据库已初始化"


# 3. 前端
echo "[3/5] 构建前端..."
cd "$APP_DIR/frontend"
npm install -q 2>/dev/null
npm run build
echo "  前端已构建到 dist/"

# 4. systemd 服务
echo "[4/5] 配置 systemd 服务..."
cat > /etc/systemd/system/lifequest.service << EOF
[Unit]
Description=LifeQuest
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$(command -v uvicorn) app.main:app --host 0.0.0.0 --port $APP_PORT --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable lifequest
systemctl restart lifequest

# 5. 验证
echo "[5/5] 验证部署..."
sleep 2
if systemctl is-active --quiet lifequest; then
  echo ""
  echo "========================================="
  echo "  部署成功!"
  echo "  访问: http://$IP:$APP_PORT"
  echo ""
  echo "  常用命令:"
  echo "    systemctl status lifequest"
  echo "    systemctl restart lifequest"
  echo "    journalctl -u lifequest -f"
  echo "========================================="
else
  echo "  服务启动失败，查看日志:"
  journalctl -u lifequest --no-pager -n 20
  exit 1
fi
