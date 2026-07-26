# Deploy Shogun Registry on Windows Azure + WSL2

> **Audience:** Hermes Agent (or human) running **inside WSL2** on a Windows Azure VM.  
> **Goal:** Run the central tenant registry so customers get random `*.shogun-os.ai` URLs.  
> **Product rules:** Our Cloudflare only · customers never need CF · one dashboard per company.

This guide is **self-contained**. Execute steps in order. Do not skip verification.

---

## 0. Preconditions (operator must provide)

The human must paste these into the agent task (or a local file the agent can read).  
**Never commit secrets to git.**

| Variable | Example / notes |
|----------|-----------------|
| `CLOUDFLARE_API_TOKEN` | User API token (`cfut_…`), **not** Account `cfat_…` |
| `CLOUDFLARE_ACCOUNT_ID` | 32-char hex |
| `CLOUDFLARE_ZONE_ID` | 32-char hex |
| `REGISTRY_DOMAIN` | `shogun-os.ai` |
| `ADMIN_API_KEY` | Optional; generate if missing |
| `REGISTRATION_TOKEN` | Optional; generate if missing |
| `REPO_URL` | `https://github.com/limcheehow/shogun-os.git` |
| `REPO_BRANCH` | `main` |
| `REGISTRY_PORT` | `9000` (default) |
| `PUBLIC_HOSTNAME` | `registry.shogun-os.ai` |

**Token permissions required (User API Token):**

- Zone → Zone → Read  
- Zone → DNS → Edit  
- Account → Cloudflare Tunnel → Edit (or Cloudflare One Connectors / cloudflared Edit)  
- Zone Resources: specific zone `shogun-os.ai`  
- Account Resources: include the account  

If any secret is missing, **stop and ask the human** — do not invent tokens.

---

## 1. Confirm environment

Run in WSL (Ubuntu preferred):

```bash
uname -a
cat /etc/os-release | head -5
whoami
pwd
# Need outbound HTTPS
curl -sS -o /dev/null -w "%{http_code}\n" https://api.cloudflare.com/client/v4/ips
```

**WSL requirements:**

- WSL2 (not WSL1): `uname -r` should look like `*-microsoft-standard-WSL2*`
- Prefer Ubuntu 22.04/24.04
- Enough disk: `df -h ~` — need ~5 GB free

If WSL1: tell human to convert to WSL2 before continuing.

---

## 2. Install Docker Engine **inside WSL**

Do **not** rely on Docker Desktop unless it is already wired to this distro. Prefer native Docker in WSL:

```bash
# Idempotent-ish install for Debian/Ubuntu
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg git jq openssl

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi

# Compose plugin
sudo apt-get install -y docker-compose-plugin || true

# Start dockerd if not running (WSL often needs this)
if ! docker info >/dev/null 2>&1; then
  # Try service, then manual dockerd
  sudo service docker start 2>/dev/null || true
  if ! docker info >/dev/null 2>&1; then
    sudo dockerd >/tmp/dockerd.log 2>&1 &
    sleep 3
  fi
fi

docker version
docker compose version
```

If `docker` still permission-denied: either `newgrp docker` / re-login, or prefix with `sudo` for the rest of this guide (note which you use).

**Azure NSG (Windows host):** later we need either:

- Inbound **TCP 9000** from Cloudflare IPs (or `0.0.0.0/0` for a quick test), **or**
- No public 9000 if using **cloudflared** on this machine (recommended for WSL).

---

## 3. Clone / update repo

```bash
INSTALL_ROOT="${INSTALL_ROOT:-$HOME/shogun-os}"
REPO_URL="${REPO_URL:-https://github.com/limcheehow/shogun-os.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"

if [[ -d "$INSTALL_ROOT/.git" ]]; then
  git -C "$INSTALL_ROOT" fetch origin
  git -C "$INSTALL_ROOT" checkout "$REPO_BRANCH"
  git -C "$INSTALL_ROOT" pull --ff-only origin "$REPO_BRANCH"
else
  git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_ROOT"
fi

cd "$INSTALL_ROOT/shogun-web/registry"
pwd
ls docker-compose.yml Dockerfile .env.example
```

---

## 4. Write `.env` (secrets from human)

```bash
cd "$INSTALL_ROOT/shogun-web/registry"
umask 077

# --- Human-provided (REQUIRED) ---
# Export these in the shell BEFORE running, or replace placeholders:
: "${CLOUDFLARE_API_TOKEN:?set CLOUDFLARE_API_TOKEN}"
: "${CLOUDFLARE_ACCOUNT_ID:?set CLOUDFLARE_ACCOUNT_ID}"
: "${CLOUDFLARE_ZONE_ID:?set CLOUDFLARE_ZONE_ID}"
: "${REGISTRY_DOMAIN:=shogun-os.ai}"
: "${REGISTRY_PORT:=9000}"
: "${PUBLIC_HOSTNAME:=registry.${REGISTRY_DOMAIN}}"

# Generate if human did not provide
: "${ADMIN_API_KEY:=$(openssl rand -hex 32)}"
: "${REGISTRATION_TOKEN:=$(openssl rand -hex 32)}"

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
echo "Wrote .env (mode 600). Registration token fingerprint: $(printf %s "$REGISTRATION_TOKEN" | head -c 6)…"
```

**Persist secrets for the human** (print once, do not commit):

```bash
echo "ADMIN_API_KEY=$ADMIN_API_KEY"
echo "REGISTRATION_TOKEN=$REGISTRATION_TOKEN"
echo "PUBLIC_HOSTNAME=$PUBLIC_HOSTNAME"
```

Save these in a password manager / operator note.

---

## 5. Verify Cloudflare token from this machine

```bash
cd "$INSTALL_ROOT/shogun-web/registry"
set -a && source .env && set +a

curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/user/tokens/verify" | jq '{success,status:.result.status}'

curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}" \
  | jq '{success,name:.result.name,status:.result.status}'

# DNS write probe + cleanup
PROBE="_shogun-wsl-probe-$(date +%s)"
CREATE=$(curl -sS -X POST -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records" \
  --data "{\"type\":\"TXT\",\"name\":\"${PROBE}\",\"content\":\"ok\",\"ttl\":120}")
echo "$CREATE" | jq '{success,id:.result.id,errors}'
RID=$(echo "$CREATE" | jq -r '.result.id // empty')
if [[ -n "$RID" ]]; then
  curl -sS -X DELETE -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${RID}" | jq '{success}'
fi
```

All must show `"success": true`. If DNS fails, stop — wrong token type or missing Zone DNS Edit.

---

## 6. Start registry (Docker Compose)

```bash
cd "$INSTALL_ROOT/shogun-web/registry"
docker compose up -d --build
docker compose ps
docker compose logs --tail=80
```

Health (inside WSL):

```bash
curl -sS "http://127.0.0.1:${REGISTRY_PORT:-9000}/api/health" | jq .
```

Expect JSON with healthy status / tenant counts (may be zeros).

---

## 7. Expose `registry.shogun-os.ai` (pick ONE)

### Option A — Cloudflare Tunnel from this WSL (recommended on Azure WSL)

No need to open Azure NSG port 9000 to the world.

```bash
# Install cloudflared
if ! command -v cloudflared >/dev/null 2>&1; then
  curl -fsSL -o /tmp/cloudflared.deb \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  sudo dpkg -i /tmp/cloudflared.deb || sudo apt-get install -f -y
fi
cloudflared --version

set -a && source .env && set +a

# Create a dedicated tunnel for the registry API (idempotent-enough: unique name)
TUNNEL_NAME="shogun-registry-wsl"
# Create via API
SECRET=$(openssl rand -base64 32 | tr -d '\n')
CREATE_T=$(curl -sS -X POST \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel" \
  --data "{\"name\":\"${TUNNEL_NAME}\",\"tunnel_secret\":\"${SECRET}\",\"config_src\":\"cloudflare\"}")
echo "$CREATE_T" | jq '{success,id:.result.id,name:.result.name,errors}'
TUNNEL_ID=$(echo "$CREATE_T" | jq -r '.result.id // empty')

if [[ -z "$TUNNEL_ID" || "$TUNNEL_ID" == "null" ]]; then
  # Maybe already exists — list and pick
  curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel?is_deleted=false" \
    | jq -r '.result[] | select(.name=="'"$TUNNEL_NAME"'") | .id' | head -1 > /tmp/tid
  TUNNEL_ID=$(cat /tmp/tid)
fi
echo "TUNNEL_ID=$TUNNEL_ID"
test -n "$TUNNEL_ID"

# Get connector token
TOKEN_JSON=$(curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/token")
# result may be a bare string
TUNNEL_TOKEN=$(echo "$TOKEN_JSON" | jq -r 'if .result|type=="string" then .result else .result.token // empty end')
if [[ -z "$TUNNEL_TOKEN" || "$TUNNEL_TOKEN" == "null" ]]; then
  # some API versions return {success,result:"eyJ..."}
  TUNNEL_TOKEN=$(echo "$TOKEN_JSON" | jq -r '.result')
fi
echo "token_len=${#TUNNEL_TOKEN}"
test "${#TUNNEL_TOKEN}" -gt 20
mkdir -p "$HOME/.shogun-os"
umask 077
printf '%s\n' "$TUNNEL_TOKEN" > "$HOME/.shogun-os/registry-tunnel.token"
chmod 600 "$HOME/.shogun-os/registry-tunnel.token"

# Ingress: hostname → local registry
curl -sS -X PUT \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${TUNNEL_ID}/configurations" \
  --data "{\"config\":{\"ingress\":[{\"hostname\":\"${PUBLIC_HOSTNAME}\",\"service\":\"http://127.0.0.1:${REGISTRY_PORT}\"},{\"service\":\"http_status:404\"}]}}" \
  | jq '{success,errors}'

# DNS CNAME registry → tunnel
# content: <tunnel_id>.cfargotunnel.com
CNAME_CONTENT="${TUNNEL_ID}.cfargotunnel.com"
EXIST=$(curl -sS -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=CNAME&name=${PUBLIC_HOSTNAME}")
EXIST_ID=$(echo "$EXIST" | jq -r '.result[0].id // empty')
if [[ -n "$EXIST_ID" ]]; then
  curl -sS -X PUT -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${EXIST_ID}" \
    --data "{\"type\":\"CNAME\",\"name\":\"${PUBLIC_HOSTNAME}\",\"content\":\"${CNAME_CONTENT}\",\"ttl\":1,\"proxied\":true}" \
    | jq '{success,name:.result.name,content:.result.content}'
else
  curl -sS -X POST -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records" \
    --data "{\"type\":\"CNAME\",\"name\":\"${PUBLIC_HOSTNAME}\",\"content\":\"${CNAME_CONTENT}\",\"ttl\":1,\"proxied\":true}" \
    | jq '{success,name:.result.name,content:.result.content,errors}'
fi

# Run connector (background). Prefer systemd if available in WSL.
if command -v systemctl >/dev/null 2>&1 && systemctl --user is-system-running >/dev/null 2>&1; then
  mkdir -p "$HOME/.config/systemd/user"
  cat > "$HOME/.config/systemd/user/shogun-registry-tunnel.service" <<UNIT
[Unit]
Description=Cloudflare Tunnel for Shogun Registry
After=network-online.target
[Service]
ExecStart=/usr/bin/cloudflared tunnel run --token ${TUNNEL_TOKEN}
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
UNIT
  # Avoid embedding token in unit if possible — use EnvironmentFile
  cat > "$HOME/.config/systemd/user/shogun-registry-tunnel.service" <<UNIT
[Unit]
Description=Cloudflare Tunnel for Shogun Registry
After=network-online.target

[Service]
EnvironmentFile=-%h/.shogun-os/registry-tunnel.env
ExecStart=/usr/bin/cloudflared tunnel run --token \${TUNNEL_TOKEN}
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT
  echo "TUNNEL_TOKEN=${TUNNEL_TOKEN}" > "$HOME/.shogun-os/registry-tunnel.env"
  chmod 600 "$HOME/.shogun-os/registry-tunnel.env"
  systemctl --user daemon-reload
  systemctl --user enable --now shogun-registry-tunnel.service
  systemctl --user status shogun-registry-tunnel.service --no-pager || true
else
  # Fallback: nohup
  pkill -f "cloudflared tunnel run" 2>/dev/null || true
  nohup cloudflared tunnel run --token "$TUNNEL_TOKEN" \
    >"$HOME/.shogun-os/registry-tunnel.log" 2>&1 &
  echo "cloudflared pid $!"
  sleep 2
  tail -n 30 "$HOME/.shogun-os/registry-tunnel.log" || true
fi
```

### Option B — Public port + Azure NSG

Only if tunnel is blocked:

1. Windows Azure portal → VM → Networking → inbound rule **TCP 9000**  
2. WSL must publish port on the Windows host (mirrored networking or `netsh interface portproxy`)  
3. Cloudflare DNS: `A registry → <Azure public IP>` proxied  

WSL portproxy example (from **Windows Admin PowerShell**):

```powershell
wsl hostname -I
# take first IP, e.g. 172.x.x.x
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=9000 `
  connectaddress=172.x.x.x connectport=9000
New-NetFirewallRule -DisplayName "Shogun Registry 9000" -Direction Inbound -Protocol TCP -LocalPort 9000 -Action Allow
```

Prefer **Option A**.

---

## 8. End-to-end verification

```bash
set -a && source "$HOME/shogun-os/shogun-web/registry/.env" && set +a
PUBLIC_HOSTNAME="${PUBLIC_HOSTNAME:-registry.shogun-os.ai}"

# Local
curl -sS "http://127.0.0.1:9000/api/health" | jq .

# Public (may need 30–60s DNS)
for i in 1 2 3 4 5; do
  if curl -fsS "https://${PUBLIC_HOSTNAME}/api/health" | jq .; then break; fi
  sleep 10
done

# Register smoke tenant
curl -sS -X POST "https://${PUBLIC_HOSTNAME}/api/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"host\": \"127.0.0.1\",
    \"port\": 8787,
    \"create_tunnel\": true,
    \"registration_token\": \"${REGISTRATION_TOKEN}\",
    \"metadata\": {\"display_name\": \"WSL Smoke\"}
  }" | jq '{subdomain, public_url, tunnel_status: .tunnel.status, has_token: (.tunnel.tunnel_token!=null)}'
```

**Success criteria:**

- [ ] `https://registry.shogun-os.ai/api/health` returns 200  
- [ ] `POST /api/register` returns random `subdomain` + `public_url`  
- [ ] Optional tunnel object present when provisioning enabled  
- [ ] `.env` mode 600 and not inside a git commit (`git status` clean of `.env`)

---

## 9. Survive reboot (WSL + Windows)

Document for the human:

1. **Windows:** Azure VM must autostart; set WSL to start on boot if needed:
   - Task Scheduler → At startup → `wsl -d Ubuntu -u root -- service docker start`  
   - And start cloudflared / `docker compose up -d` in the distro  
2. **Inside WSL:** if systemd user services work, enable them; else a `@reboot` crontab:

```bash
crontab -l 2>/dev/null | grep -v shogun-registry > /tmp/cron || true
cat >> /tmp/cron <<'CRON'
@reboot sleep 20 && cd $HOME/shogun-os/shogun-web/registry && /usr/bin/docker compose up -d
@reboot sleep 25 && /usr/bin/cloudflared tunnel run --token "$(cat $HOME/.shogun-os/registry-tunnel.token)" >>$HOME/.shogun-os/registry-tunnel.log 2>&1
CRON
crontab /tmp/cron
```

3. Warn: **if the Windows VM stops, the registry stops** — customers cannot register new tenants until it is back.

---

## 10. Agent final report (required)

When done, reply to the human with:

```text
## Registry deploy report
- Host: WSL on Azure Windows (hostname / uname)
- Repo path: …
- Health local: …
- Health public: https://registry.shogun-os.ai/api/health → …
- Register smoke: subdomain=… public_url=…
- REGISTRATION_TOKEN fingerprint: first6…
- ADMIN_API_KEY fingerprint: first6…
- Tunnel: id=… connector=running|failed
- Reboot persistence: systemd|cron|none
- Blockers: …
```

**Do not** paste full API tokens or full registration secrets in chat logs if avoidable — fingerprints only. Store full values only in `.env` on disk.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `docker info` fails | Start `dockerd`; ensure WSL2 |
| DNS API 403 | Use User token `cfut_`, Zone DNS Edit |
| Tunnel create 403 | Account → Cloudflare Tunnel Edit |
| Public health timeout | cloudflared not running; CNAME wrong; wait for DNS |
| Port works in WSL not from internet | Use Option A tunnel; or fix Windows portproxy + NSG |
| Compose can’t mount DB | Check volume permissions; `DATABASE_PATH` as in compose |
| `.env` lost after recreate | Restore from password manager; never git commit |

---

## Related

- Product design: [`docs/architecture/WEB_PORTAL.md`](../architecture/WEB_PORTAL.md)  
- Cloudflare operator checklist: [`docs/ops/cloudflare-registry-setup.md`](cloudflare-registry-setup.md)  
- Registry code: `shogun-web/registry/`  
- Customer installer: `scripts/install-web.sh`  

---

## One-shot prompt for Hermes (copy-paste)

```text
Execute the Shogun registry deploy runbook on this WSL machine:

https://raw.githubusercontent.com/limcheehow/shogun-os/main/docs/ops/deploy-registry-wsl-azure.md

Use these secrets (do not commit them):

export CLOUDFLARE_API_TOKEN='…'
export CLOUDFLARE_ACCOUNT_ID='562ae3b0db6eecf7976a523cddca4cfc'
export CLOUDFLARE_ZONE_ID='2cb16aaf0b99ded5e4d595195760d43b'
export REGISTRY_DOMAIN='shogun-os.ai'
export PUBLIC_HOSTNAME='registry.shogun-os.ai'

Follow every section. Prefer Cloudflare Tunnel (Option A). Report health + smoke register results with secret fingerprints only.
```
