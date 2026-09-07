#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${1:-/opt/lifequest}"
SERVICE_NAME="${LIFEQUEST_SERVICE_NAME:-lifequest}"
PIP_INDEX_URL="${LIFEQUEST_PIP_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple/}"
NPM_REGISTRY="${LIFEQUEST_NPM_REGISTRY:-https://registry.npmmirror.com}"

resolve_python() {
  local candidate

  if [[ -n "${LIFEQUEST_PYTHON:-}" ]]; then
    [[ -x "$LIFEQUEST_PYTHON" ]] || {
      echo "LIFEQUEST_PYTHON is not executable: $LIFEQUEST_PYTHON" >&2
      exit 1
    }
    printf '%s\n' "$LIFEQUEST_PYTHON"
    return
  fi

  if [[ -x "$APP_DIR/backend/venv/bin/python" ]]; then
    printf '%s\n' "$APP_DIR/backend/venv/bin/python"
    return
  fi

  if [[ -n "${LIFEQUEST_CONDA_PREFIX:-}" && -x "$LIFEQUEST_CONDA_PREFIX/bin/python" ]]; then
    printf '%s\n' "$LIFEQUEST_CONDA_PREFIX/bin/python"
    return
  fi

  for candidate in \
    "$HOME/miniforge3/envs/${LIFEQUEST_CONDA_ENV:-lifequest}/bin/python" \
    "$HOME/anaconda3/envs/${LIFEQUEST_CONDA_ENV:-lifequest}/bin/python" \
    "/home/capkin/miniforge3/envs/${LIFEQUEST_CONDA_ENV:-lifequest}/bin/python"; do
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  command -v python3 || {
    echo "No Python interpreter found for LifeQuest deployment." >&2
    exit 1
  }
}

resolve_npm() {
  local npm_bin

  if [[ -n "${LIFEQUEST_NPM_BIN:-}" ]]; then
    [[ -x "$LIFEQUEST_NPM_BIN" ]] || {
      echo "LIFEQUEST_NPM_BIN is not executable: $LIFEQUEST_NPM_BIN" >&2
      exit 1
    }
    printf '%s\n' "$LIFEQUEST_NPM_BIN"
    return
  fi

  npm_bin="$(command -v npm || true)"
  if [[ -n "$npm_bin" ]]; then
    printf '%s\n' "$npm_bin"
    return
  fi

  if [[ -d "$HOME/.nvm/versions/node" ]]; then
    npm_bin="$(find "$HOME/.nvm/versions/node" -regextype posix-extended -regex "$HOME/.nvm/versions/node/[^/]+/bin/npm" -perm -u+x -print 2>/dev/null | sort -V | tail -n 1)"
    if [[ -n "$npm_bin" ]]; then
      printf '%s\n' "$npm_bin"
      return
    fi
  fi

  echo "No npm executable found for LifeQuest deployment." >&2
  exit 1
}

configure_systemd_scope() {
  SYSTEMD_SCOPE="${LIFEQUEST_SYSTEMD_SCOPE:-}"
  if [[ "$SYSTEMD_SCOPE" == "user" ]]; then
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
    export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
    return
  fi

  if [[ "$SYSTEMD_SCOPE" == "system" ]]; then
    return
  fi

  local runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  if [[ -S "$runtime_dir/bus" ]]; then
    export XDG_RUNTIME_DIR="$runtime_dir"
    export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
    local user_working_directory
    user_working_directory="$(systemctl --user show "$SERVICE_NAME" -p WorkingDirectory --value 2>/dev/null || true)"
    if [[ "$user_working_directory" == "$APP_DIR/backend" ]] && \
       (systemctl --user is-enabled --quiet "$SERVICE_NAME" 2>/dev/null || \
        systemctl --user is-active --quiet "$SERVICE_NAME" 2>/dev/null); then
      SYSTEMD_SCOPE="user"
      return
    fi
  fi

  SYSTEMD_SCOPE="system"
}

restart_service() {
  if [[ "$SYSTEMD_SCOPE" == "user" ]]; then
    systemctl --user daemon-reload
    systemctl --user restart "$SERVICE_NAME"
    systemctl --user is-active --quiet "$SERVICE_NAME"
  else
    sudo systemctl restart "$SERVICE_NAME"
    sudo systemctl is-active --quiet "$SERVICE_NAME"
  fi
}

show_service_logs() {
  if [[ "$SYSTEMD_SCOPE" == "user" ]]; then
    journalctl --user -u "$SERVICE_NAME" --no-pager -n 80 >&2 || true
  else
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n 80 >&2 || true
  fi
}

cd "$APP_DIR"

configure_systemd_scope

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to deploy: $APP_DIR has uncommitted changes." >&2
  exit 1
fi

git fetch origin main
git checkout main
git pull --ff-only origin main

cd "$APP_DIR/backend"
PYTHON="$(resolve_python)"
"$PYTHON" -m pip install \
  --index-url "$PIP_INDEX_URL" \
  --disable-pip-version-check \
  --retries 5 \
  --timeout 120 \
  -r requirements.txt

cd "$APP_DIR/frontend"
NPM_BIN="$(resolve_npm)"
NPM_DIR="$(dirname "$NPM_BIN")"
export PATH="$NPM_DIR:$PATH"
"$NPM_BIN" ci --registry="$NPM_REGISTRY"
NPM_CONFIG_UPDATE_NOTIFIER=false "$NPM_BIN" run build

restart_service

for _ in {1..30}; do
  if curl --fail --silent "http://127.0.0.1:8000/api/health" >/dev/null; then
    curl --fail --silent --max-time 3 "http://127.0.0.1:3001/sse" >/dev/null || true
    echo "LifeQuest deployment is healthy."
    exit 0
  fi
  sleep 2
done

echo "LifeQuest health check failed." >&2
show_service_logs
exit 1
