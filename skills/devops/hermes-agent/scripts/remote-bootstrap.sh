#!/bin/bash
# Hermes Remote Bootstrap — run ONCE on the GPU/cloud server
# Usage: ./remote-bootstrap.sh <wsl-host-or-ip>
set -euo pipefail
HOST="${1:?Usage: $0 <wsl-host-or-ip>}"

echo "=== 1. Install Hermes ==="
pip install hermes-agent
hermes setup

echo "=== 2. Clone brain ==="
if [ ! -d ~/brain/.git ]; then
  git clone https://github.com/tapway/tapway-brain.git ~/brain
else
  echo "~/brain already exists, pulling..."
  (cd ~/brain && git pull)
fi

echo "=== 3. Sync profiles + skills ==="
rsync -avz "$HOST:~/.hermes/profiles/" ~/.hermes/profiles/  2>/dev/null || echo "WARNING: profiles rsync failed — copy manually"
rsync -avz "$HOST:~/.hermes/skills/" ~/.hermes/skills/      2>/dev/null || echo "WARNING: skills rsync failed — copy manually"

echo "=== 4. Copy config + secrets ==="
scp "$HOST:~/.hermes/.env" ~/.hermes/              2>/dev/null || echo "WARNING: .env missing on host"
scp "$HOST:~/.hermes/config.yaml" ~/.hermes/       2>/dev/null || echo "WARNING: config.yaml missing on host"
scp "$HOST:~/.hermes/auth.json" ~/.hermes/         2>/dev/null || echo "WARNING: auth.json missing on host"
scp "$HOST:~/.hermes/supabase_key.txt" ~/.hermes/  2>/dev/null || echo "WARNING: supabase_key.txt missing on host"

echo "=== 5. Start gateway (tmux watchdog) ==="
if [ -f ~/.hermes/skills/devops/hermes-agent/scripts/hermes-gateway-watchdog.sh ]; then
  cp ~/.hermes/skills/devops/hermes-agent/scripts/hermes-gateway-watchdog.sh ~/.local/bin/
  chmod +x ~/.local/bin/hermes-gateway-watchdog.sh
  tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
  echo "Gateway started in tmux session 'hermes-gateway'"
else
  echo "WARNING: watchdog script not found — start gateway manually: tmux new-session -d -s hermes-gateway 'hermes gateway run'"
fi

echo ""
echo "=== Done ==="
echo "Check:  tmux capture-pane -t hermes-gateway -p | tail -10"
echo "Logs:   tail -f ~/.hermes/logs/gateway.log"