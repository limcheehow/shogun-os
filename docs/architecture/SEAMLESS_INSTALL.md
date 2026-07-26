# Seamless install: public bootstrap tickets

## Problem

Handing every customer `REGISTRATION_TOKEN` does not scale and leaks a shared secret.

## Solution

```
Customer: ./scripts/install-web.sh
        │
        ▼
POST https://registry.shogun-os.ai/api/install/bootstrap
        │  (public, rate-limited, no secret)
        ▼
  { install_token: "inst_…", expires_in: 3600 }
        │
        ▼
POST /api/register  { registration_token: "inst_…", host, port, … }
        │  ticket redeemed (single-use)
        ▼
  { subdomain, public_url, tunnel_token }
```

| Actor | Credential |
|-------|------------|
| **Customer installer** | None — auto bootstrap |
| **Operator / CI** | Optional `REGISTRATION_TOKEN` still works |
| **Admin API** | `ADMIN_API_KEY` (never shipped to customers) |

## Customer UX

```bash
git clone https://github.com/limcheehow/shogun-os.git
cd shogun-os
./scripts/install-web.sh --admin-email you@company.com
# → https://quiet-lotus-42.shogun-os.ai
```

No Cloudflare account. No subdomain choice. No token from sales.

## Security controls

- Tickets expire (default **1 hour**)
- Tickets are **single-use**
- **Rate limit** per IP (default 10/hour)
- Shared `REGISTRATION_TOKEN` never leaves the registry host
- Optional future: email verification, invite codes, paid plan gates

## Config (registry `.env`)

```bash
ENABLE_PUBLIC_BOOTSTRAP=true
BOOTSTRAP_TICKET_TTL_SECONDS=3600
BOOTSTRAP_RATE_LIMIT_PER_IP=10
# REGISTRATION_TOKEN=...   # optional operator override only
```

## Deploy note (Azure WSL registry)

After pulling this version:

```bash
cd ~/shogun-os && git pull
cd shogun-web/registry
# ensure ENABLE_PUBLIC_BOOTSTRAP=true in .env (default)
docker compose up -d --build
curl -sS https://registry.shogun-os.ai/api/health
curl -sS -X POST https://registry.shogun-os.ai/api/install/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{"email":"ops@test","installer_version":"smoke"}' | jq .
```
