#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${1:-/root/LifeQuest}"
SERVICE_NAME="${LIFEQUEST_SERVICE_NAME:-lifequest}"
PIP_INDEX_URL="${LIFEQUEST_PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
NPM_REGISTRY="${LIFEQUEST_NPM_REGISTRY:-https://registry.npmmirror.com}"

cd "$APP_DIR"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to deploy: $APP_DIR has uncommitted changes." >&2
  exit 1
fi

git fetch origin main
git checkout main
git pull --ff-only origin main

cd "$APP_DIR/backend"
if [[ -x "$APP_DIR/backend/venv/bin/python" ]]; then
  PYTHON="$APP_DIR/backend/venv/bin/python"
else
  PYTHON="$(command -v python3)"
fi
"$PYTHON" -m pip install \
  --index-url "$PIP_INDEX_URL" \
  --disable-pip-version-check \
  --retries 5 \
  --timeout 120 \
  -r requirements.txt

cd "$APP_DIR/frontend"
npm ci --registry="$NPM_REGISTRY"
npm run build

sudo systemctl restart "$SERVICE_NAME"
sudo systemctl is-active --quiet "$SERVICE_NAME"

for _ in {1..30}; do
  if curl --fail --silent "http://127.0.0.1:8000/api/health" >/dev/null; then
    curl --fail --silent --max-time 3 "http://127.0.0.1:3001/sse" >/dev/null || true
    echo "LifeQuest deployment is healthy."
    exit 0
  fi
  sleep 2
done

echo "LifeQuest health check failed." >&2
sudo journalctl -u "$SERVICE_NAME" --no-pager -n 80 >&2
exit 1
