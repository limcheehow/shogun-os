#!/usr/bin/env bash
# Dashboard watchdog — checks and restarts each dashboard individually.
# v4 — added error capture from tmux, .env.local sourcing, better diagnostics
#
# Generic version — site URLs and ports come from a config file.
# CONFIG: Edit scripts/config.yaml.example or set SITES_CONFIG env var.
set -euo pipefail

# Default config path
SITES_CONFIG="${SITES_CONFIG:-$HOME/.hermes/sites-config.yaml}"

LOG="$HOME/.hermes/logs/dashboard-watchdog.log"
ERROR_LOG="$HOME/.hermes/logs/dashboard-watchdog-errors.log"
NODE_BIN="$HOME/.hermes/node/bin"
PORT_TIMEOUT=3

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }
err() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" | tee -a "$ERROR_LOG" "$LOG"; }

# ── Parse config file ──
# Config format (YAML):
#   sites:
#     - name: product-dashboard
#       port: 3002
#       dir: /path/to/product-dashboard
#       cmd: "${NODE_BIN}/npx next start -p 3002 -H 127.0.0.1"
#       needs_env: true
#       type: nohup
#     - name: project-app
#       port: 3001
#       dir: /path/to/project-app
#       cmd: "${NODE_BIN}/npx next start -p 3001 -H 127.0.0.1"
#       needs_env: true
#       type: tmux
#   cloudflare_tunnel:
#     name: pm-tunnel
#     config_path: "/path/to/.cloudflared/tunnel.yml"
#     tunnel_id: "your-tunnel-id"

# Default sites if no config file exists
declare -a SITES=()
declare -A SITE_PORT=()
declare -A SITE_DIR=()
declare -A SITE_CMD=()
declare -A SITE_ENV=()
declare -A SITE_TYPE=()

load_config() {
    if [ -f "$SITES_CONFIG" ]; then
        # Parse YAML with bash (simple key-value extract)
        local current_site=""
        local in_sites=false
        local in_tunnel=false
        while IFS= read -r line; do
            # Trim whitespace
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
                elif [[ "$line" =~ ^\ {4}type:\ *\"?([^\"]+)\"?$ ]]; then
                    SITE_TYPE["$current_site"]="${BASH_REMATCH[1]}"
                fi
            fi
        done < "$SITES_CONFIG"
    fi

    # If no config loaded, define defaults (edit these or create config file)
    if [ ${#SITES[@]} -eq 0 ]; then
        SITES=("product-dashboard" "project-app" "crm-dashboard" "brain-site" "https-proxy")
        SITE_PORT["product-dashboard"]="3002"
        SITE_DIR["product-dashboard"]="$HOME/projects/your-product-dashboard"
        SITE_CMD["product-dashboard"]="\$NODE_BIN/npx next start -p 3002 -H 127.0.0.1"
        SITE_ENV["product-dashboard"]="true"
        SITE_TYPE["product-dashboard"]="nohup"

        SITE_PORT["project-app"]="3001"
        SITE_DIR["project-app"]="$HOME/your-project-app"
        SITE_CMD["project-app"]="\$NODE_BIN/npx next start -p 3001 -H 127.0.0.1"
        SITE_ENV["project-app"]="true"
        SITE_TYPE["project-app"]="tmux"

        SITE_PORT["crm-dashboard"]="8770"
        SITE_DIR["crm-dashboard"]="$HOME/crm-dashboard"
        SITE_CMD["crm-dashboard"]="PORT=8770 HOSTNAME=127.0.0.1 \$NODE_BIN/node .next/standalone/server.js"
        SITE_ENV["crm-dashboard"]="true"
        SITE_TYPE["crm-dashboard"]="tmux"

        SITE_PORT["brain-site"]="8080"
        SITE_DIR["brain-site"]="$HOME/brain-site"
        SITE_CMD["brain-site"]="python3 brain-site-server.py"
        SITE_ENV["brain-site"]="false"
        SITE_TYPE["brain-site"]="tmux"

        SITE_PORT["https-proxy"]="8443"
        SITE_DIR["https-proxy"]="$HOME/.hermes/ssl"
        SITE_CMD["https-proxy"]="\$NODE_BIN/node \$HOME/.hermes/ssl/serve-https.js"
        SITE_ENV["https-proxy"]="false"
        SITE_TYPE["https-proxy"]="tmux"
    fi
}

# ── Helper: check if port is accepting connections ──────
port_up() {
    timeout "$PORT_TIMEOUT" bash -c "echo >/dev/tcp/127.0.0.1/$1" 2>/dev/null
}

# ── Helper: verify a restart actually worked ──────
verify_start() {
    local name="$1" port="$2" retries="${3:-10}" delay="${4:-3}"
    local i
    for i in $(seq 1 "$retries"); do
        if port_up "$port"; then
            log "  ✓ $name is UP on :$port (after $((i * delay))s)"
            return 0
        fi
        sleep "$delay"
    done
    log "  ✗ $name FAILED to start on :$port after $((retries * delay))s"
    # Capture tmux output for diagnosis
    if tmux has-session -t "$name" 2>/dev/null; then
        local pane_output
        pane_output=$(tmux capture-pane -t "$name" -p -S -50 2>/dev/null || true)
        if [ -n "$pane_output" ]; then
            err "$name tmux output:"$'\n'"$pane_output"
        else
            err "$name: tmux pane empty — process likely exited immediately"
        fi
    else
        err "$name: tmux session missing — startup command may have failed"
    fi
    return 1
}

# ── Helper: restart via tmux ──────
restart_in_tmux() {
    local name="$1" dir="$2" cmd="$3"
    if tmux has-session -t "$name" 2>/dev/null; then
        tmux kill-session -t "$name" 2>/dev/null || true
        sleep 1
    fi
    tmux new-session -d -s "$name" "cd $dir && $cmd" 2>/dev/null || true
    tmux set-option -t "$name" remain-on-exit on 2>/dev/null || true
}

# ── Check and restart a site ──
check_site() {
    local name="$1"
    local port="${SITE_PORT[$name]}"
    local dir="${SITE_DIR[$name]}"
    local cmd="${SITE_CMD[$name]}"
    local needs_env="${SITE_ENV[$name]:-false}"
    local type="${SITE_TYPE[$name]:-tmux}"

    if ! port_up "$port"; then
        log "⚠ $name :$port DOWN — restarting..."
        fuser -k "$port/tcp" 2>/dev/null || true
        # Wait for port to actually free up
        for i in $(seq 1 10); do
            if ! fuser "$port/tcp" 2>/dev/null; then break; fi
            sleep 1
        done

        if [ "$type" = "nohup" ]; then
            # Start with nohup + pidfile
            PIDFILE="/tmp/${name}.pid"
            cd "$dir" || { err "$name: cd failed"; return 1; }
            if [ "$needs_env" = "true" ]; then
                set -a && [ -f ./.env.local ] && . ./.env.local && set +a
            fi
            eval "nohup $cmd > /tmp/${name}.log 2>&1 &"
            echo $! > "$PIDFILE"
            log "  $name started (pid $(cat "$PIDFILE"))"
        else
            restart_in_tmux "$name" "$dir" "$cmd"
        fi
        verify_start "$name" "$port" || true
    fi
}

# ── Check Cloudflare tunnel ──
check_tunnel() {
    if ! pgrep -f "cloudflared.*tunnel.*run" > /dev/null 2>&1; then
        log "⚠ Cloudflare tunnel DOWN — restarting..."
        local tunnel_config="${CLOUDFLARE_TUNNEL_CONFIG:-$HOME/.cloudflared/tunnel.yml}"
        local tunnel_id="${CLOUDFLARE_TUNNEL_ID:-}"
        if [ -n "$tunnel_id" ]; then
            restart_in_tmux "pm-tunnel" \
                "$HOME" \
                "cloudflared tunnel --config $tunnel_config run $tunnel_id"
            sleep 5
            if pgrep -f "cloudflared.*tunnel.*run" > /dev/null 2>&1; then
                log "  ✓ Cloudflare tunnel is running"
            else
                err "Cloudflare tunnel: FAILED to start"
            fi
        fi
    fi
}

# ── Main ──
load_config

for site in "${SITES[@]}"; do
    check_site "$site"
done

# Check Cloudflare tunnel
check_tunnel