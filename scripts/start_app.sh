#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${IMAGE_VIEWER_BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${IMAGE_VIEWER_BACKEND_PORT:-8011}"
FRONTEND_HOST="${IMAGE_VIEWER_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${IMAGE_VIEWER_FRONTEND_PORT:-5175}"

cd "$ROOT_DIR"

uv run uvicorn image_viewer.backend.main:app \
  --host "$BACKEND_HOST" \
  --port "$BACKEND_PORT" \
  --reload &
BACKEND_PID=$!

cd "$ROOT_DIR/frontend"
npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

printf 'Backend:  http://%s:%s\n' "$BACKEND_HOST" "$BACKEND_PORT"
printf 'Frontend: http://%s:%s\n' "$FRONTEND_HOST" "$FRONTEND_PORT"

wait "$BACKEND_PID" "$FRONTEND_PID"
