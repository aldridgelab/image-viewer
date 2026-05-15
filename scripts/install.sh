#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

need_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$name" >&2
    return 1
  fi
}

need_command uv
need_command npm

cd "$ROOT_DIR"
printf 'Installing Python dependencies with uv...\n'
uv sync

printf '\nInstalling frontend dependencies with npm...\n'
cd "$ROOT_DIR/frontend"
npm install

printf '\nInstall complete.\n'
printf 'Start the app with: %s/scripts/start_app.sh\n' "$ROOT_DIR"
