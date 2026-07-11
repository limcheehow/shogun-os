#!/usr/bin/env bash
# gateway-signal-monitor.sh — ONE-SHOT check (not a daemon)
# Monitors gateway process state and log for SIGTERM/restart events.
# Designed to run as a cron job every 2 minutes.
# Silently exits 0 when all is well (no output = no delivery).
# Outputs diagnostics on gateway death/restart.
#
# Generic version — no hardcoded profile names. Works with any Hermes gateway.

set -euo pipefail

LOG="$HOME/.hermes/logs/gateway-signal-monitor.log"
GATEWAY_LOG="$HOME/.hermes/logs/gateway.log"
STATE_FILE="/tmp/gateway-signal-monitor.state"

CURRENT_PID=$(pgrep -f "hermes.*gateway run" 2>/dev/null | grep -v pgrep | head -1 || echo "")

# Load previous state
LAST_PID=""
LAST_KNOWN_DEATH=""
if [ -f "$STATE_FILE" ]; then
  source "$STATE_FILE"
fi

# Compare current vs last PID
if [ -z "$CURRENT_PID" ] && [ -n "$LAST_PID" ]; then
  # Gateway died
  echo "⚠️ Gateway PID $LAST_PID has died since last check ($(date))"
  echo "--- dmesg ---"
  dmesg -T 2>/dev/null | tail -5 || echo "(no dmesg access)"
  echo "--- loadavg ---"
  cat /proc/loadavg
  echo "--- Gateway log tail (last 10) ---"
  tail -10 "$GATEWAY_LOG" 2>/dev/null || true
  echo "[$(date)] ⚠ Gateway PID $LAST_PID died" >> "$LOG"
elif [ -n "$CURRENT_PID" ] && [ "$CURRENT_PID" != "${LAST_PID:-}" ]; then
  # Gateway restarted — note it silently
  echo "[$(date)] Gateway PID changed: ${LAST_PID:-none} → $CURRENT_PID" >> "$LOG"
  # Check if we just recovered from a death (there's a recent death log entry)
  RECENT_DEATH=$(tail -20 "$GATEWAY_LOG" 2>/dev/null | grep -c "SIGTERM\|initiating shutdown" || true)
  if [ "$RECENT_DEATH" -gt 0 ]; then
    echo "🔄 Gateway restarted: ${LAST_PID:-none} → $CURRENT_PID at $(date)"
    echo "Gateway log shows recent shutdown events"
    tail -5 "$GATEWAY_LOG" 2>/dev/null
  fi
elif [ -z "$CURRENT_PID" ] && [ -z "${LAST_PID:-}" ]; then
  # First run or gateway never started
  if [ -f "$GATEWAY_LOG" ]; then
    echo "ℹ️ No gateway process found. Last gateway log activity:"
    tail -3 "$GATEWAY_LOG" 2>/dev/null || true
  fi
  echo "[$(date)] No gateway process" >> "$LOG"
fi

# Save current state
echo "LAST_PID=${CURRENT_PID:-}" > "$STATE_FILE"
echo "LAST_CHECK=$(date +%s)" >> "$STATE_FILE"