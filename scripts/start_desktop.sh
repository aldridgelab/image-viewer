#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if [[ ! -f "$ROOT_DIR/frontend/dist/index.html" ]]; then
  (cd "$ROOT_DIR/frontend" && npm run build)
fi

uv run python -m image_viewer.desktop "$@"
