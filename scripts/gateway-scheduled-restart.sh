#!/usr/bin/env bash
set -euo pipefail

echo "=== Gateway restart scheduled for $(date) ==="

# Find the gateway child process (hermes gateway run), NOT the watchdog bash process
GATEWAY_PID=$(ps aux | grep "hermes gateway run" | grep -v grep | grep -v watchdog | awk '{print $2}' | head -1)

if [ -z "$GATEWAY_PID" ]; then
    echo "ERROR: No gateway process found. Is the gateway running?"
    echo "Checking tmux..."
    if tmux has-session -t hermes-gateway 2>/dev/null; then
        echo "Tmux session exists but no gateway process. Starting gateway..."
        tmux send-keys -t hermes-gateway "hermes gateway run" Enter
    else
        echo "No tmux session either. Starting fresh..."
        if [ -x "$HOME/.local/bin/hermes-gateway-watchdog" ]; then
            tmux new-session -d -s hermes-gateway "$HOME/.local/bin/hermes-gateway-watchdog"
        else
            echo "ERROR: Watchdog not found."
            exit 1
        fi
    fi
    exit 0
fi

echo "Found gateway PID: $GATEWAY_PID"
echo "Sending SIGTERM to gateway (watchdog will auto-restart in 3s)..."

kill -TERM "$GATEWAY_PID"

# Wait for the watchdog to restart it
sleep 5

# Verify
NEW_PID=$(ps aux | grep "hermes gateway run" | grep -v grep | grep -v watchdog | awk '{print $2}' | head -1)
if [ -n "$NEW_PID" ] && [ "$NEW_PID" != "$GATEWAY_PID" ]; then
    echo "✅ Gateway restarted successfully. Old PID: $GATEWAY_PID → New PID: $NEW_PID"
else
    echo "⚠️  Gateway may not have restarted yet. Checking tmux..."
    tmux capture-pane -t hermes-gateway -p | tail -5
fi