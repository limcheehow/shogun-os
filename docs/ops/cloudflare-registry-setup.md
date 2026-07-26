# Cloudflare setup for Shogun OS registry (operator only)

> **This guide is for YOU (Tapway / Shogun operators).**  
> End customers never open Cloudflare and never create tunnels.

Goal: customers run `./scripts/install-web.sh` and receive a live URL like  
`https://quiet-lotus-42.shogun-os.ai` with **zero** Cloudflare work on their side.

---

## Architecture you are building

```
Browser → *.shogun-os.ai (OUR Cloudflare zone)
              │
              │  per-tenant CNAME → {tunnel-id}.cfargotunnel.com
              ▼
         cloudflared on CUSTOMER machine (token we issued)
              │
              ▼
         localhost:8787  (shogun-web)
```

Optional edge entry for the **registry API** itself:

```
registry.shogun-os.ai → our VPS :9000  (via our own tunnel or public IP + CF proxy)
```

---

## Prerequisites

- [ ] Domain you control (recommended: `shogun-os.ai`)
- [ ] Cloudflare account (Free plan is enough to start)
- [ ] Domain nameservers pointed at Cloudflare
- [ ] A small VPS for the registry (1 vCPU / 1 GB is fine to start)
- [ ] Docker + Docker Compose on that VPS

---

## Step 1 — Add the domain to Cloudflare

1. Cloudflare Dashboard → **Add a site** → enter `shogun-os.ai` (or your domain).
2. Choose Free plan.
3. Copy the two Cloudflare nameservers.
4. At your registrar, set NS records to Cloudflare’s.
5. Wait until the zone status is **Active**.

---

## Step 2 — Collect Account ID and Zone ID

1. Cloudflare Dashboard → select the zone (`shogun-os.ai`).
2. Right sidebar (or Overview): copy **Zone ID**.
3. Sidebar → **Account home** (or any page URL): copy **Account ID**.

Save:

```bash
export CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export CLOUDFLARE_ZONE_ID=yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
export REGISTRY_DOMAIN=shogun-os.ai
```

---

## Step 3 — Create an API token (least privilege)

Cloudflare Dashboard → **My Profile** → **API Tokens** → **Create Token** → **Custom token**.

| Permission | Access |
|------------|--------|
| Account → Cloudflare Tunnel | Edit |
| Account → Account Settings | Read *(optional)* |
| Zone → DNS | Edit |
| Zone → Zone | Read |

**Zone resources:** Include → Specific zone → `shogun-os.ai`  
**Account resources:** Include → your account  

Create → copy token **once**:

```bash
export CLOUDFLARE_API_TOKEN=zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
```

> Do not put this token on customer machines. It lives only on the registry VPS.

---

## Step 4 — DNS records (baseline)

In the zone DNS:

| Type | Name | Content | Proxy | Purpose |
|------|------|---------|-------|---------|
| A or CNAME | `registry` | VPS IP **or** registry tunnel | Proxied (orange) | Central registry API |
| CNAME | `*` | *(optional wildcard to a shared tunnel — see note)* | Proxied | Optional; per-tenant CNAMEs are auto-created by registry |

**Recommended production path:** leave `*` alone. The registry API creates  
`{subdomain}.shogun-os.ai` → `{tunnel-id}.cfargotunnel.com` **per tenant** when they register.

You only need a stable `registry.shogun-os.ai` pointing at the registry service.

---

## Step 5 — Deploy the registry on your VPS

```bash
# On the VPS
git clone https://github.com/limcheehow/shogun-os.git
cd shogun-os/shogun-web/registry

cp .env.example .env
chmod 600 .env
```

Edit `.env`:

```bash
HOST=0.0.0.0
PORT=9000
REGISTRY_DOMAIN=shogun-os.ai

# Strong random secrets
ADMIN_API_KEY=$(openssl rand -hex 32)
REGISTRATION_TOKEN=$(openssl rand -hex 32)

CLOUDFLARE_API_TOKEN=...   # from Step 3
CLOUDFLARE_ACCOUNT_ID=...  # from Step 2
CLOUDFLARE_ZONE_ID=...     # from Step 2

ENABLE_TUNNEL_PROVISIONING=true
ALLOW_PREFERRED_SUBDOMAIN=false
DEFAULT_CREATE_TUNNEL=true

DATABASE_PATH=/var/lib/shogun-registry/registry.db
```

Start:

```bash
docker compose up -d --build
curl -sS https://registry.shogun-os.ai/api/health || curl -sS http://127.0.0.1:9000/api/health
```

Save `REGISTRATION_TOKEN` somewhere safe — you will hand it to installers / bake it into releases (or a short-lived invite).

---

## Step 6 — Expose `registry.shogun-os.ai` (pick one)

### Option A — Cloudflare Tunnel for the registry only (recommended)

On the VPS:

```bash
# Install cloudflared (see Cloudflare docs for latest)
cloudflared tunnel login
cloudflared tunnel create shogun-registry
cloudflared tunnel route dns shogun-registry registry.shogun-os.ai

# config.yml
# tunnel: <id>
# credentials-file: /root/.cloudflared/<id>.json
# ingress:
#   - hostname: registry.shogun-os.ai
#     service: http://127.0.0.1:9000
#   - service: http_status:404

cloudflared tunnel run shogun-registry
# or install as systemd service
```

### Option B — Public IP + orange-cloud A record

```
A  registry  →  YOUR_VPS_IP  (Proxied)
```

Open firewall port 9000 only if not using a local reverse proxy; better terminate TLS at Cloudflare and proxy to `127.0.0.1:9000` via nginx/Caddy on the VPS.

---

## Step 7 — Smoke-test tenant registration

From any machine (or the VPS):

```bash
curl -sS -X POST "https://registry.shogun-os.ai/api/register" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "127.0.0.1",
    "port": 8787,
    "create_tunnel": true,
    "registration_token": "'"$REGISTRATION_TOKEN"'",
    "metadata": {"display_name": "Smoke Test"}
  }' | jq .
```

Expect:

- `subdomain` like `quiet-lotus-42`
- `public_url` like `https://quiet-lotus-42.shogun-os.ai`
- `tunnel.tunnel_token` present when provisioning is on

Check Cloudflare DNS: a new CNAME `quiet-lotus-42` should exist.

Simulate customer connector:

```bash
# On a machine that will run shogun-web on :8787
cloudflared tunnel run --token "$TUNNEL_TOKEN"
```

---

## Step 8 — Customer install path (what you ship)

```bash
export SHOGUN_REGISTRY_URL=https://registry.shogun-os.ai
export SHOGUN_REGISTRY_TOKEN=<REGISTRATION_TOKEN>

./scripts/install-web.sh --admin-email admin@customer.com
# → prints assigned https://….shogun-os.ai
# → writes ~/.shogun-os/tunnel.token when CF provisioning works
```

Customer then keeps portal + connector up (installer can install systemd units).  
They **never** log into Cloudflare.

---

## Step 9 — Hardening checklist

- [ ] Rotate `ADMIN_API_KEY` and `REGISTRATION_TOKEN` from defaults  
- [ ] Restrict who receives `REGISTRATION_TOKEN` (invite codes later)  
- [ ] Enable Cloudflare WAF rate limits on `/api/register`  
- [ ] Back up `/var/lib/shogun-registry/registry.db` daily  
- [ ] Keep `ALLOW_PREFERRED_SUBDOMAIN=false` in production  
- [ ] Monitor tunnel count vs Cloudflare plan limits  
- [ ] Document on-call: delete tenant = registry DELETE + CF tunnel cleanup  

---

## Step 10 — Optional: vanity subdomains later

Only if product needs `acme.shogun-os.ai`:

1. Set `ALLOW_PREFERRED_SUBDOMAIN=true` on registry (or gate via admin API).  
2. Charge / approve vanity separately.  
3. Never make vanity the default installer path.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Register 401 | `REGISTRATION_TOKEN` mismatch |
| Register 200 but no tunnel | `ENABLE_TUNNEL_PROVISIONING`, CF token scopes, Account/Zone IDs |
| DNS missing | Zone ID wrong; token missing DNS Edit |
| URL 530/502 | Customer `cloudflared` not running with token; portal not on port |
| Preferred name ignored | Expected — `ALLOW_PREFERRED_SUBDOMAIN=false` |
| Customer asked for CF login | Design bug — point them back to installer only |

---

## Quick reference — env on registry VPS

```bash
REGISTRY_DOMAIN=shogun-os.ai
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_ZONE_ID=...
ENABLE_TUNNEL_PROVISIONING=true
ALLOW_PREFERRED_SUBDOMAIN=false
DEFAULT_CREATE_TUNNEL=true
REGISTRATION_TOKEN=...
ADMIN_API_KEY=...
```

See also: [`docs/architecture/WEB_PORTAL.md`](../architecture/WEB_PORTAL.md).
