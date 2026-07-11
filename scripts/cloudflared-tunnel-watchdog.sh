#!/usr/bin/env bash
# Auto-recovery for Cloudflare tunnels after server restart
# Generic version — tunnel config comes from env vars or config file.
#
# Environment variables:
#   CLOUDFLARE_TUNNEL_CONFIGS — JSON array of tunnel configurations
#     Example: '[{"name":"my-tunnel","config":"/path/to/tunnel.yml","id":"tunnel-id","port":3000}]'
#   Or set individual:
#     CLOUDFLARE_TUNNEL_NAMES — space-separated names
#     CLOUDFLARE_TUNNEL_CONFIG_<NAME> — per-tunnel config path
#     CLOUDFLARE_TUNNEL_ID_<NAME> — per-tunnel ID
#     CLOUDFLARE_TUNNEL_PORT_<NAME> — per-tunnel backend port

set -e
LOCKFILE="/tmp/cloudflared-watchdog.lock"

# Prevent overlapping runs
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE" 2>/dev/null || echo "")
    [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null && exit 0
    rm -f "$LOCKFILE"
fi
echo "$$" > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"; exit 0' EXIT

LOG="$HOME/.cloudflared/watchdog.log"
NODE_BIN="$HOME/.hermes/node/bin"
export PATH="$NODE_BIN:$PATH"
CLOUDFLARED="$HOME/.local/bin/cloudflared"

mkdir -p "$(dirname "$LOG")"

# ── Load tunnel configs ──
# Default: one tunnel named "default" with config from env or defaults
# Override all by setting CLOUDFLARE_TUNNEL_CONFIGS as JSON array
TUNNEL_NAMES=()

if [ -n "${CLOUDFLARE_TUNNEL_CONFIGS:-}" ]; then
    # Parse JSON config
    TUNNEL_NAMES=($(echo "$CLOUDFLARE_TUNNEL_CONFIGS" | python3 -c "import sys,json; [print(t['name']) for t in json.load(sys.stdin)]" 2>/dev/null))
else
    # Individual env vars or defaults
    TUNNEL_NAMES=(${CLOUDFLARE_TUNNEL_NAMES:-default})
fi

get_tunnel_config() {
    local name="$1"
    if [ -n "${CLOUDFLARE_TUNNEL_CONFIGS:-}" ]; then
        python3 -c "
import sys, json
configs = json.load(sys.stdin)
for t in configs:
    if t['name'] == '$name':
        print(json.dumps(t))
" <<< "$CLOUDFLARE_TUNNEL_CONFIGS" 2>/dev/null
    else
        local config_var="CLOUDFLARE_TUNNEL_CONFIG_${name^^}"
        local id_var="CLOUDFLARE_TUNNEL_ID_${name^^}"
        local port_var="CLOUDFLARE_TUNNEL_PORT_${name^^}"
        local dir_var="CLOUDFLARE_TUNNEL_DIR_${name^^}"
        cat <<EOF
{"name":"$name","config":"${!config_var:-$HOME/.cloudflared/${name}.yml}","id":"${!id_var:-}","port":${!port_var:-3000},"dir":"${!dir_var:-$HOME/projects/dashboard}"}
EOF
    fi
}

# ── Start a backend if needed ──
ensure_backend() {
    local name="$1" port="$2" dir="$3" cmd="$4"
    if ! curl -sf --max-time 3 "http://localhost:$port" > /dev/null 2>&1; then
        echo "[$(date)] $name backend not responding on :$port — starting" >> "$LOG"
        pkill -f "$cmd" 2>/dev/null || true
        sleep 1
        cd "$dir"
        eval "nohup $cmd >> server.log 2>&1 &"
        echo "[$(date)] $name backend started (PID $!)" >> "$LOG"
        for i in $(seq 1 15); do
            sleep 2
            curl -sf --max-time 3 "http://localhost:$port" > /dev/null 2>&1 && break
            echo "[$(date)] Waiting for $name... attempt $i" >> "$LOG"
        done
    fi
}

# ── Start a tunnel ──
start_tunnel() {
    local name="$1"
    local config_json=$(get_tunnel_config "$name")
    local config_path=$(echo "$config_json" | python3 -c "import sys,json; print(json.load(sys.stdin)['config'])" 2>/dev/null)
    local tunnel_id=$(echo "$config_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
    local port=$(echo "$config_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('port',3000))" 2>/dev/null)
    local dir=$(echo "$config_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('dir','$HOME'))" 2>/dev/null)
    local cmd=$(echo "$config_json" | python3 -c "import sys,json; print(json.load(sys.stdin).get('cmd','${NODE_BIN}/npx next start -p $port -H 127.0.0.1'))" 2>/dev/null)

    # Start backend if needed
    ensure_backend "$name" "$port" "$dir" "$cmd"

    # Start tunnel
    local pidfile="/tmp/cloudflared-${name}.pid"
    if [ -f "$pidfile" ]; then
        OLD_PID=$(cat "$pidfile" 2>/dev/null || echo "")
        if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
            # Check if tunnel is actually serving
            if curl -sf --max-time 3 "http://localhost:$port" > /dev/null 2>&1; then
                echo "[$(date)] ✓ $name tunnel PID $OLD_PID is alive" >> "$LOG"
                return
            else
                echo "[$(date)] ✗ $name tunnel PID $OLD_PID is zombie — killing" >> "$LOG"
                kill "$OLD_PID" 2>/dev/null; sleep 1; kill -9 "$OLD_PID" 2>/dev/null
                rm -f "$pidfile"
            fi
        else
            rm -f "$pidfile"
        fi
    fi

    if [ ! -f "$pidfile" ] && [ -n "$tunnel_id" ]; then
        echo "[$(date)] Starting Cloudflare tunnel for $name" >> "$LOG"
        nohup "$CLOUDFLARED" tunnel --config "$config_path" run \
            >> "$HOME/.cloudflared/${name}.log" 2>&1 &
        NEW_PID=$!
        echo "$NEW_PID" > "$pidfile"
        echo "[$(date)] $name tunnel started (PID $NEW_PID)" >> "$LOG"
    fi
}

# ── Verify public URLs ──
verify_urls() {
    sleep 3
    local domains="${CLOUDFLARE_TUNNEL_DOMAINS:-}"
    if [ -n "$domains" ]; then
        for domain in $domains; do
            if curl -sf --max-time 10 "https://$domain" > /dev/null 2>&1; then
                echo "[$(date)] ✓ $domain reachable" >> "$LOG"
            else
                echo "[$(date)] ⚠ $domain still unreachable" >> "$LOG"
            fi
        done
    fi
}

# ── Main ──
for tunnel_name in "${TUNNEL_NAMES[@]}"; do
    start_tunnel "$tunnel_name"
done

verify_urls