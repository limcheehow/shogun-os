# Service Watchdog Pattern

## Problem

Long-running services (Next.js, HTTPS proxies, voice agents, Cloudflare tunnels) die silently on WSL — OOM kills, WSL restarts, stale process accumulation, or just random crashes. The user discovers the outage hours later when they try to use the service.

## Pattern: `no_agent` cron watchdog

A cron job running every 2 minutes that checks each service and restarts any that are down. Uses `no_agent=true` so the script's stdout IS the message (empty = silent success, non-empty = notification).

### Template

```bash
#!/usr/bin/env bash
# Service watchdog — auto-restart dead services
set -euo pipefail

LOG="/home/user/.hermes/logs/watchdog.log"
RESTARTED=0

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

# ── Service 1: health check and restart ──
if ! curl -sf --max-time 5 http://127.0.0.1:3000/health > /dev/null 2>&1; then
    log "⚠ Service :3000 DOWN — restarting..."
    pkill -f "process-name-pattern" 2>/dev/null || true
    sleep 2
    cd /path/to/service
    nohup start-command >> /path/to/log 2>&1 &
    log "  → Service restarted (PID $!)"
    RESTARTED=1
fi

# ── Service 2: process-based check ──
if ! pgrep -f "process-name-pattern" > /dev/null 2>&1; then
    log "⚠ Service DOWN — restarting..."
    nohup start-command >> /path/to/log 2>&1 &
    log "  → Service restarted (PID $!)"
    RESTARTED=1
fi

# Only produce output (and notify) if something was restarted
if [ "$RESTARTED" -eq 1 ]; then
    echo "⚠ Watchdog restarted services — see $LOG for details"
fi
```

### Cron setup

```bash
# Install script
cp watchdog.sh ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/watchdog.sh

# Create cron job (no_agent — script output IS the delivery)
hermes cron create '*/2 * * * *' \
  --name 'Service Watchdog' \
  --script watchdog.sh \
  --no-agent \
  --deliver local
```

### What to guard

| Service type | Health check | Restart command |
|---|---|---|
| HTTP server | `curl -sf localhost:PORT/health` | `kill` stale + restart |
| Process | `pgrep -f "unique-pattern"` | `nohup start-cmd &` |
| Port listener | `curl -sf localhost:PORT` | Kill + restart |
| Tunnel | `pgrep -f "cloudflared tunnel"` | Kill + restart |

### Pitfalls

- **Check `pkill` patterns carefully** — `pkill -f "next start"` does NOT kill the `next-server` child. Kill by port instead: `fuser -k PORT/tcp`.
- **Kill stale before restart** — always `pkill` or `fuser -k` the old process before starting the new one. Otherwise port is in use and the restart fails silently.
- **Don't spam on every tick** — track `RESTARTED` flag and only emit output when something actually restarted. Silent success = system is healthy.
- **Don't use `set -e` without traps** — if a health checkcurl fails (non-zero exit), `set -e` kills the entire script before checking other services. Use `||` chains instead.
- **`@reboot` crontab is NOT a watchdog replacement** — `@reboot` starts services once on WSL boot. It doesn't catch crashes. The combination of `@reboot` + `*/2` watchdog is the complete solution.