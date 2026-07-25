#!/usr/bin/env bash
set -euo pipefail

# Resolve gbrain binary
GBRAIN_BIN="$(command -v gbrain || true)"
if [ -z "$GBRAIN_BIN" ]; then
  GBRAIN_BIN="$HOME/.bun/bin/gbrain"
fi

# Configurable port and host
PORT="${GBRAIN_HTTP_PORT:-3100}"
HOST="${GBRAIN_HTTP_HOST:-127.0.0.1}"

exec "$GBRAIN_BIN" serve --http --port "$PORT" --host "$HOST"