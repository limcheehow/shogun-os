#!/usr/bin/env bash
# ── Sites Startup — starts all sites + Cloudflare tunnel in tmux ──
# Runs at @reboot and whenever sites need recovery.
# v4 — adds post-start verification, error capture, .env.local sourcing, retry logic
#
# Generic version — site list comes from config file (SITES_CONFIG env var).
set -euo pipefail

NODE_BIN="$HOME/.hermes/node/bin"
LOG_DIR="$HOME/.hermes/logs"
ERROR_LOG="$LOG_DIR/sites-startup-errors.log"
mkdir -p "$LOG_DIR"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_DIR/sites-startup.log"; }
err()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$ERROR_LOG" "$LOG_DIR/sites-startup.log"; }

# Default config path — override with SITES_CONFIG env var
SITES_CONFIG="${SITES_CONFIG:-$HOME/.hermes/sites-config.yaml}"

# ── Wait for a port to accept connections ──────────────────────────
port_up() {
    timeout 3 bash -c "echo >/dev/tcp/127.0.0.1/$1" 2>/dev/null
}

# ── Verify a site actually came up, capture errors if not ──────────
verify_start() {
    local name="$1" port="$2" max_wait="${3:-30}"
    local waited=0 delay=2
    while [ "$waited" -lt "$max_wait" ]; do
        if port_up "$port"; then
            log "  ✓ $name is UP on :$port (after ${waited}s)"
            return 0
        fi
        sleep "$delay"
        waited=$((waited + delay))
    done
    # Capture tmux output for diagnosis
    log "  ✗ $name FAILED to bind :$port after ${max_wait}s"
    if tmux has-session -t "$name" 2>/dev/null; then
        local pane_output
        pane_output=$(tmux capture-pane -t "$name" -p -S -50 2>/dev/null || true)
        if [ -n "$pane_output" ]; then
            err "$name tmux output:"$'\n'"$pane_output"
        else
            err "$name: tmux session exists but pane is empty (process likely exited immediately)"
        fi
    else
        err "$name: tmux session does not exist (session creation failed)"
    fi
    return 1
}

# ── Source .env.local if it exists ─────────────────────────────────
source_env() {
    local dir="$1"
    if [ -f "$dir/.env.local" ]; then
        while IFS= read -r line; do
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            [[ -z "$line" ]] && continue
            if [[ "$line" =~ ^[A-Z_][A-Z0-9_]*= ]]; then
                export "$line"
            fi
        done < "$dir/.env.local"
    fi
}

# ── Start a site with verification and one retry ───────────────────
start_site() {
    local name="$1" port="$2" dir="$3" cmd="$4"
    local needs_env="${5:-false}"

    # Already up?
    if port_up "$port"; then
        log "✓ ${name} :${port} already up"
        return 0
    fi

    log "⚡ starting ${name} on :${port}..."

    # Kill stale processes
    fuser -k "${port}/tcp" 2>/dev/null || true
    sleep 1

    # Kill any old tmux session with this name
    tmux kill-session -t "$name" 2>/dev/null || true
    sleep 1

    # Build the full command (POSIX-compatible — tmux uses /bin/sh, not bash)
    local full_cmd
    if [ "$needs_env" = "true" ] && [ -f "$dir/.env.local" ]; then
        full_cmd="set -a && . ./.env.local && set +a && $cmd"
    else
        full_cmd="$cmd"
    fi

    # First attempt
    tmux new-session -d -s "$name" "cd $dir && $full_cmd" 2>/dev/null || true
    tmux set-option -t "$name" remain-on-exit on 2>/dev/null || true
    log "  → ${name} tmux created (attempt 1)"

    if verify_start "$name" "$port" 30; then
        return 0
    fi

    # Retry once
    log "  ↻ retrying ${name} (attempt 2)..."
    tmux kill-session -t "$name" 2>/dev/null || true
    fuser -k "${port}/tcp" 2>/dev/null || true
    sleep 2
    tmux new-session -d -s "$name" "cd $dir && $full_cmd" 2>/dev/null || true
    tmux set-option -t "$name" remain-on-exit on 2>/dev/null || true

    if verify_start "$name" "$port" 45; then
        log "  ✓ ${name} recovered on retry"
        return 0
    fi

    err "${name}: FAILED after 2 attempts. Manual intervention required."
    return 1
}

# ── Load sites from config ──
# Config format (YAML):
#   sites:
#     - name: product-dashboard
#       port: 3002
#       dir: /path/to/product-dashboard
#       cmd: "${NODE_BIN}/npx next start -p 3002 -H 127.0.0.1"
#       needs_env: true
#   cloudflare_tunnel:
#     name: pm-tunnel
#     config_path: "/path/to/.cloudflared/tunnel.yml"
#     tunnel_id: "your-tunnel-id"

declare -a SITES=()
declare -A SITE_PORT=()
declare -A SITE_DIR=()
declare -A SITE_CMD=()
declare -A SITE_ENV=()

load_config() {
    if [ -f "$SITES_CONFIG" ]; then
        local current_site=""
        local in_sites=false
        local in_tunnel=false
        while IFS= read -r line; do
            line="${line#"${line%%[![:space:]]*}"}"
            [ -z "$line" ] && continue
            [[ "$line" == \#* ]] && continue

            if [[ "$line" == "sites:" ]]; then
                in_sites=true
                continue
            fi
            if [[ "$line" == "cloudflare_tunnel:" ]]; then
                in_sites=false
                in_tunnel=true
                continue
            fi
            if [[ "$line" == [a-z]*: ]] && [[ ! "$line" =~ ^\  ]]; then
                in_sites=false
                in_tunnel=false
            fi

            if $in_sites && [[ "$line" =~ ^-\ *name:\ *\"?([^\"]+)\"?$ ]]; then
                current_site="${BASH_REMATCH[1]}"
                SITES+=("$current_site")
            elif $in_sites && [[ "$current_site" != "" ]]; then
                if [[ "$line" =~ ^\ {4}port:\ *([0-9]+) ]]; then
                    SITE_PORT["$current_site"]="${BASH_REMATCH[1]}"
                elif [[ "$line" =~ ^\ {4}dir:\ *\"?([^\"]+)\"?$ ]]; then
                    SITE_DIR["$current_site"]="${BASH_REMATCH[1]}"
                elif [[ "$line" =~ ^\ {4}cmd:\ *\"?([^\"]+)\"?$ ]]; then
                    SITE_CMD["$current_site"]="${BASH_REMATCH[1]}"
                elif [[ "$line" =~ ^\ {4}needs_env:\ *(true|false) ]]; then
                    SITE_ENV["$current_site"]="${BASH_REMATCH[1]}"
                fi
            fi
            if $in_tunnel && [[ "$line" =~ ^\ {4}name:\ *\"?([^\"]+)\"?$ ]]; then
                CLOUDFLARE_TUNNEL_NAME="${BASH_REMATCH[1]}"
            elif $in_tunnel && [[ "$line" =~ ^\ {4}config_path:\ *\"?([^\"]+)\"?$ ]]; then
                CLOUDFLARE_TUNNEL_CONFIG="${BASH_REMATCH[1]}"
            elif $in_tunnel && [[ "$line" =~ ^\ {4}tunnel_id:\ *\"?([^\"]+)\"?$ ]]; then
                CLOUDFLARE_TUNNEL_ID="${BASH_REMATCH[1]}"
            fi
        done < "$SITES_CONFIG"
    fi

    # If no config loaded, define defaults (edit these or create config file)
    if [ ${#SITES[@]} -eq 0 ]; then
        SITES=("product-dashboard" "project-app" "crm-dashboard" "brain-site")
        SITE_PORT["product-dashboard"]="3002"
        SITE_DIR["product-dashboard"]="$HOME/projects/your-product-dashboard"
        SITE_CMD["product-dashboard"]="\$NODE_BIN/npx next start -p 3002 -H 127.0.0.1"
        SITE_ENV["product-dashboard"]="true"

        SITE_PORT["project-app"]="3001"
        SITE_DIR["project-app"]="$HOME/your-project-app"
        SITE_CMD["project-app"]="\$NODE_BIN/npx next start -p 3001 -H 127.0.0.1"
        SITE_ENV["project-app"]="true"

        SITE_PORT["crm-dashboard"]="8770"
        SITE_DIR["crm-dashboard"]="$HOME/crm-dashboard"
        SITE_CMD["crm-dashboard"]="PORT=8770 HOSTNAME=127.0.0.1 \$NODE_BIN/node .next/standalone/server.js"
        SITE_ENV["crm-dashboard"]="true"

        SITE_PORT["brain-site"]="8080"
        SITE_DIR["brain-site"]="$HOME/brain-site"
        SITE_CMD["brain-site"]="python3 brain-site-server.py"
        SITE_ENV["brain-site"]="false"
    fi
}

# ── Start Cloudflare tunnel ──
start_tunnel() {
    local tunnel_name="${CLOUDFLARE_TUNEL_NAME:-pm-tunnel}"
    local tunnel_config="${CLOUDFLARE_TUNNEL_CONFIG:-$HOME/.cloudflared/tunnel.yml}"
    local tunnel_id="${CLOUDFLARE_TUNNEL_ID:-}"

    if [ -z "$tunnel_id" ]; then
        log "⚠ No tunnel_id configured — skipping Cloudflare tunnel"
        return
    fi

    if ! pgrep -f "cloudflared.*${tunnel_name}" > /dev/null 2>&1; then
        log "⚡ starting ${tunnel_name} tunnel..."
        tmux kill-session -t "${tunnel_name}" 2>/dev/null || true
        sleep 1
        tmux new-session -d -s "${tunnel_name}" \
            "cloudflared tunnel --config $tunnel_config run $tunnel_id 2>&1" 2>/dev/null || true
        log "  → ${tunnel_name} tmux created"
        sleep 3
        if pgrep -f "cloudflared.*tunnel.*run" > /dev/null 2>&1; then
            log "  ✓ ${tunnel_name} tunnel is running"
        else
            err "${tunnel_name} tunnel: FAILED to start"
        fi
    else
        log "✓ ${tunnel_name} tunnel already up"
    fi
}

# ── Main ──
log "=== Sites startup @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

load_config

for site in "${SITES[@]}"; do
    start_site "$site" "${SITE_PORT[$site]}" "${SITE_DIR[$site]}" "${SITE_CMD[$site]}" "${SITE_ENV[$site]:-false}"
    sleep 2  # brief gap to avoid resource contention
done

# Cloudflare Tunnel
start_tunnel

log "=== Sites startup complete ==="

# ── Final health summary ──
echo "" >> "$LOG_DIR/sites-startup.log"
log "Health check:"
for site in "${SITES[@]}"; do
    local port="${SITE_PORT[$site]}"
    if port_up "$port"; then
        log "  :$port ✓ UP"
    else
        log "  :$port ✗ DOWN"
    fi
done
log "---"