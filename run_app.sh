#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f backend/.env ]]; then
  echo "Missing backend/.env. Add MONGO_URL and DB_NAME first."
  exit 1
fi

if command -v brew >/dev/null 2>&1; then
  brew services start mongodb-community >/dev/null 2>&1 || true
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

if [[ ! -d frontend/node_modules ]]; then
  (cd frontend && npm install)
fi

.venv/bin/python -m uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000 --env-file backend/.env &
BACKEND_PID=$!

cleanup() {
  if ps -p "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"

cd frontend
REACT_APP_BACKEND_URL="${REACT_APP_BACKEND_URL:-http://localhost:8000}" npm start
