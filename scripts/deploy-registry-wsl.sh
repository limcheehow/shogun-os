#!/usr/bin/env bash
# Deploy Shogun central registry (Docker) — intended for WSL2 / Linux operator hosts.
# Secrets MUST come from the environment (never hardcode).
#
# Required env:
#   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ZONE_ID
# Optional:
#   REGISTRY_DOMAIN (default shogun-os.ai)
#   REGISTRY_PORT (default 9000)
#   INSTALL_ROOT (default $HOME/shogun-os)
#   ADMIN_API_KEY / REGISTRATION_TOKEN (auto-generated if unset)
#   SKIP_TUNNEL=1  — only run compose, skip cloudflared setup
#   REPO_URL / REPO_BRANCH
set -euo pipefail

log() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

: "${CLOUDFLARE_API_TOKEN:?CLOUDFLARE_API_TOKEN required}"
: "${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID required}"
: "${CLOUDFLARE_ZONE_ID:?CLOUDFLARE_ZONE_ID required}"

REGISTRY_DOMAIN="${REGISTRY_DOMAIN:-shogun-os.ai}"
REGISTRY_PORT="${REGISTRY_PORT:-9000}"
PUBLIC_HOSTNAME="${PUBLIC_HOSTNAME:-registry.${REGISTRY_DOMAIN}}"
INSTALL_ROOT="${INSTALL_ROOT:-$HOME/shogun-os}"
REPO_URL="${REPO_URL:-https://github.com/limcheehow/shogun-os.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
ADMIN_API_KEY="${ADMIN_API_KEY:-$(openssl rand -hex 32)}"
REGISTRATION_TOKEN="${REGISTRATION_TOKEN:-$(openssl rand -hex 32)}"
SKIP_TUNNEL="${SKIP_TUNNEL:-0}"

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

log "Installing base packages if needed"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl git jq openssl ca-certificates
fi

if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
sudo apt-get install -y docker-compose-plugin 2>/dev/null || true

if ! docker info >/dev/null 2>&1; then
  log "Starting dockerd"
  sudo service docker start 2>/dev/null || true
  if ! docker info >/dev/null 2>&1; then
    sudo dockerd >/tmp/dockerd.log 2>&1 &
    sleep 4
  fi
fi
docker info >/dev/null || die "docker not usable"

if [[ -d "$INSTALL_ROOT/.git" ]]; then
  log "Updating repo $INSTALL_ROOT"
  git -C "$INSTALL_ROOT" fetch origin
  git -C "$INSTALL_ROOT" checkout "$REPO_BRANCH"
  git -C "$INSTALL_ROOT" pull --ff-only origin "$REPO_BRANCH" || true
else
  log "Cloning $REPO_URL → $INSTALL_ROOT"
  git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_ROOT"
fi

REG_DIR="$INSTALL_ROOT/shogun-web/registry"
cd "$REG_DIR"
[[ -f docker-compose.yml ]] || die "registry compose missing"

umask 077
cat > .env <<EOF
HOST=0.0.0.0
PORT=9000
LOG_LEVEL=info
REGISTRY_DOMAIN=${REGISTRY_DOMAIN}
ADMIN_API_KEY=${ADMIN_API_KEY}
REGISTRATION_TOKEN=${REGISTRATION_TOKEN}
DATABASE_PATH=/var/lib/shogun-registry/registry.db
HEALTH_CHECK_INTERVAL_SECONDS=30
HEARTBEAT_STALE_SECONDS=120
CLOUDFLARE_API_TOKEN=${CLOUDFLARE_API_TOKEN}
CLOUDFLARE_ACCOUNT_ID=${CLOUDFLARE_ACCOUNT_ID}
CLOUDFLARE_ZONE_ID=${CLOUDFLARE_ZONE_ID}
ENABLE_TUNNEL_PROVISIONING=true
ALLOW_PREFERRED_SUBDOMAIN=false
DEFAULT_CREATE_TUNNEL=true
REGISTRY_PORT=${REGISTRY_PORT}
EOF
chmod 600 .env
log "Wrote $REG_DIR/.env"

log "Verifying Cloudflare token"
curl -fsS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/user/tokens/verify" | jq -e '.success==true' >/dev/null
curl -fsS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}" | jq -e '.success==true' >/dev/null

log "docker compose up"
docker compose up -d --build
sleep 2
curl -fsS "http://127.0.0.1:${REGISTRY_PORT}/api/health" | jq .

if [[ "$SKIP_TUNNEL" != "1" ]]; then
  if ! command -v cloudflared >/dev/null 2>&1; then
    log "Installing cloudflared"
    curl -fsSL -o /tmp/cloudflared.deb \
      https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    sudo dpkg -i /tmp/cloudflared.deb || sudo apt-get install -f -y
  fi

  TUNNEL_NAME="${TUNNEL_NAME:-shogun-registry-wsl}"
  SECRET=$(openssl rand -base64 32 | tr -d '\n')
  CREATE_T=$(curl -sS -X POST \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel" \
    --data "{\"name\":\"${TUNNEL_NAME}\",\"tunnel_secret\":\"${SECRET}\",\"config_src\":\"cloudflare\"}")
  TUNNEL_ID=$(echo "$CREATE_T" | jq -r '.result.id // empty')
  if [[ -z "$TUNNEL_ID" ]]; then
    TUNNEL_ID=$(curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel?is_deleted=false" \
      | jq -r --arg n "$TUNNEL_NAME" '.result[] | select(.name==$n) | .id' | head -1)
  fi
  [[ -n "$TUNNEL_ID" ]] || die "could not create/find tunnel: $CREATE_T"

  TOKEN_JSON=$(curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/token")
  TUNNEL_TOKEN=$(echo "$TOKEN_JSON" | jq -r 'if (.result|type)=="string" then .result else .result.token // empty end')
  [[ -n "$TUNNEL_TOKEN" && "$TUNNEL_TOKEN" != "null" ]] || die "no tunnel token: $TOKEN_JSON"

  mkdir -p "$HOME/.shogun-os"
  printf '%s\n' "$TUNNEL_TOKEN" >"$HOME/.shogun-os/registry-tunnel.token"
  chmod 600 "$HOME/.shogun-os/registry-tunnel.token"

  curl -fsS -X PUT \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/configurations" \
    --data "{\"config\":{\"ingress\":[{\"hostname\":\"${PUBLIC_HOSTNAME}\",\"service\":\"http://127.0.0.1:${REGISTRY_PORT}\"},{\"service\":\"http_status:404\"}]}}" \
    | jq -e '.success==true' >/dev/null

  CNAME_CONTENT="${TUNNEL_ID}.cfargotunnel.com"
  EXIST=$(curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=CNAME&name=${PUBLIC_HOSTNAME}")
  EXIST_ID=$(echo "$EXIST" | jq -r '.result[0].id // empty')
  BODY=$(jq -n --arg name "$PUBLIC_HOSTNAME" --arg content "$CNAME_CONTENT" \
    '{type:"CNAME",name:$name,content:$content,ttl:1,proxied:true}')
  if [[ -n "$EXIST_ID" ]]; then
    curl -fsS -X PUT -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${EXIST_ID}" \
      --data "$BODY" | jq -e '.success==true' >/dev/null
  else
    curl -fsS -X POST -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records" \
      --data "$BODY" | jq -e '.success==true' >/dev/null
  fi

  pkill -f "cloudflared tunnel run" 2>/dev/null || true
  nohup cloudflared tunnel run --token "$TUNNEL_TOKEN" \
    >"$HOME/.shogun-os/registry-tunnel.log" 2>&1 &
  log "cloudflared started pid $!"
  sleep 3
fi

log "Local health"
curl -fsS "http://127.0.0.1:${REGISTRY_PORT}/api/health" | jq .

log "Public health (best-effort)"
curl -fsS "https://${PUBLIC_HOSTNAME}/api/health" | jq . || log "public health not ready yet — wait for DNS/tunnel"

cat <<EOF

======== DEPLOY SUMMARY ========
Registry dir:     $REG_DIR
Public hostname:  https://${PUBLIC_HOSTNAME}
Local health:     http://127.0.0.1:${REGISTRY_PORT}/api/health
ADMIN_API_KEY:    ${ADMIN_API_KEY:0:6}… (full value in .env)
REGISTRATION_TOKEN: ${REGISTRATION_TOKEN:0:6}… (full value in .env)
Tunnel skipped:   $SKIP_TUNNEL
================================
EOF
