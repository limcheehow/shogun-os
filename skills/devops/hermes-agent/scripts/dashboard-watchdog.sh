#!/usr/bin/env bash
# Dashboard watchdog — auto-restart Next.js (3000) and HTTPS proxy (8443) if down
set -euo pipefail

LOG="/home/tapway/.hermes/logs/dashboard-watchdog.log"
RESTARTED=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# ── Check Next.js on port 3000 ──────────────────────────
if ! curl -sf --max-time 5 http://127.0.0.1:3000/login > /dev/null 2>&1; then
    log "⚠ Next.js :3000 DOWN — restarting..."
    # Kill any stale next processes holding the port
    fuser -k 3000/tcp 2>/dev/null || true
    sleep 2
    cd /home/tapway/projects/tapway-product-dashboard
    nohup /home/tapway/.nvm/versions/node/v22.14.0/bin/npx next start -p 3000 >> /home/tapway/projects/tapway-product-dashboard/server.log 2>&1 &
    log "  → Next.js restarted (PID $!)"
    RESTARTED=1
fi

# ── Check HTTPS proxy on port 8443 ──────────────────────
if ! curl -sk --max-time 5 https://127.0.0.1:8443/login > /dev/null 2>&1; then
    log "⚠ HTTPS proxy :8443 DOWN — restarting..."
    # Kill any stale proxy processes
    fuser -k 8443/tcp 2>/dev/null || true
    sleep 1
    nohup /home/tapway/.nvm/versions/node/v22.14.0/bin/node /home/tapway/.hermes/ssl/serve-https.js >> /home/tapway/.hermes/ssl/proxy.log 2>&1 &
    log "  → HTTPS proxy restarted (PID $!)"
    RESTARTED=1
fi

# ── Check Cloudflare tunnel (voice agent) ───────────────
if ! pgrep -f "cloudflared tunnel.*cheehow-voice" > /dev/null 2>&1; then
    log "⚠ Cloudflare tunnel DOWN — restarting..."
    nohup /home/tapway/.local/bin/cloudflared tunnel --config /home/tapway/.cloudflared/cheehow-voice.yml run cheehow-voice >> /home/tapway/.cloudflared/cheehow-voice.log 2>&1 &
    log "  → Cloudflare tunnel restarted (PID $!)"
    RESTARTED=1
fi

# Only produce output (and notify) if something was restarted
if [ "$RESTARTED" -eq 1 ]; then
    echo "⚠ Watchdog restarted services — see $LOG for details"
fi