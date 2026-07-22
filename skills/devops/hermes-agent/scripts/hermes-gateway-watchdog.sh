#!/usr/bin/env bash
# ─── Hermes Gateway Watchdog ──────────────────────────────────────────
# Runs `hermes gateway run` in a restart loop so the gateway
# auto-recovers after SIGTERM (e.g. `hermes gateway restart`) or crash.
#
# v2 — Smart exponential backoff: if the gateway crashes within 10s of
# starting, next restart waits longer (3s → 10s → 30s → 60s → 120s max).
# After a stable run (>60s), backoff resets to minimum.
#
# MUTUAL EXCLUSION: Only ONE watchdog may run at any time.
# On startup, checks for an existing watchdog via PID file + process
# validation. Kills stale PID files from dead watchdogs automatically.
#
# SIGNAL DESIGN:
#   SIGTERM — IGNORED (trap ''). Sent by `hermes gateway restart` and
#     `kill <gateway_pid>`. Only the gateway child receives it; the
#     watchdog while-loop catches the exit status and restarts.
#   SIGHUP — IGNORED (trap ''). Sent by the tmux server when it restarts
#     or crashes. Without this, a tmux server restart kills the watchdog.
#   SIGINT — Caught for clean shutdown (Ctrl+C / tmux kill-session).
#
# Usage:
#   tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
# ───────────────────────────────────────────────────────────────────────

PIDFILE="/tmp/hermes-gateway.pid"
GATEWAY_LOG="$HOME/.hermes/logs/gateway.log"

# ── Backoff parameters ─────────────────────────────────────────────────
MIN_BACKOFF=3          # seconds — initial wait after clean exit
MAX_BACKOFF=120        # seconds — max wait after repeated crashes
CRASH_WINDOW=10        # seconds — gateway must survive this long to be "stable"
STABLE_RUN=60          # seconds — if gateway ran this long, reset backoff

# ── Mutual exclusion: only ONE watchdog allowed ──────────────────────
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    if ps -p "$OLD_PID" -o comm= 2>/dev/null | grep -qE "bash|hermes-gateway"; then
      echo "[watchdog $$] Another watchdog is already running (PID $OLD_PID). Exiting."
      exit 0
    fi
  fi
  echo "[watchdog $$] Removing stale PID file (PID $OLD_PID is dead)"
  rm -f "$PIDFILE"
fi
echo "$$" > "$PIDFILE"
# ──────────────────────────────────────────────────────────────────────

cleanup() {
  echo "[watchdog] SIGINT received — shutting down gateway..."
  rm -f "$PIDFILE"
  exit 0
}
trap cleanup SIGINT
trap '' SIGTERM SIGHUP

echo "[watchdog] Hermes Gateway Watchdog v2 (PID $$)"
echo "[watchdog] Log: $GATEWAY_LOG"
echo "[watchdog] Backoff: ${MIN_BACKOFF}s min / ${MAX_BACKOFF}s max"

BACKOFF=$MIN_BACKOFF
GATEWAY_START_TS=0

while true; do
  echo "[watchdog] Launching gateway (backoff=${BACKOFF}s)..."
  GATEWAY_START_TS=$(date +%s)
  START_TS=$GATEWAY_START_TS
  hermes gateway run
  EXIT_CODE=$?
  END_TS=$(date +%s)
  RUNTIME=$(( END_TS - START_TS ))
  echo "[watchdog] Gateway exited with code $EXIT_CODE after ${RUNTIME}s at $(date)"

  if [ "$RUNTIME" -ge "$STABLE_RUN" ]; then
    # Stable run — reset backoff to minimum
    BACKOFF=$MIN_BACKOFF
    echo "[watchdog] Gateway ran ${RUNTIME}s (stable ≥${STABLE_RUN}s) — backoff reset to ${BACKOFF}s"
  elif [ "$RUNTIME" -lt "$CRASH_WINDOW" ]; then
    # Quick crash — increase backoff
    BACKOFF=$(( BACKOFF * 3 / 2 ))
    # Round up to nearest multiple of 5 for clean numbers
    BACKOFF=$(( ((BACKOFF + 4) / 5) * 5 ))
    if [ "$BACKOFF" -gt "$MAX_BACKOFF" ]; then
      BACKOFF=$MAX_BACKOFF
    fi
    echo "[watchdog] Gateway crashed in ${RUNTIME}s (<${CRASH_WINDOW}s) — backoff increased to ${BACKOFF}s"
  else
    # Moderate run — keep current backoff
    echo "[watchdog] Gateway ran ${RUNTIME}s — backoff stays at ${BACKOFF}s"
  fi

  echo "[watchdog] Sleeping ${BACKOFF}s before next launch..."
  sleep "$BACKOFF"
done