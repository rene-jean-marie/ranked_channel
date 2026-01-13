#!/usr/bin/env bash
set -euo pipefail

if [[ -f .venv/bin/activate ]]; then
  # Use local venv if present.
  source .venv/bin/activate
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

exec uvicorn ranked_channel.api.app:app --reload --app-dir src --host "$HOST" --port "$PORT"
