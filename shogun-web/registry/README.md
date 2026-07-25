# Shogun OS Central Registry

Reverse-proxy + tenant registry for `*.{REGISTRY_DOMAIN}` traffic.

## Local run

```bash
cd ~/shogun-os/shogun-web/registry
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# optional: ALLOW_INSECURE_LOCAL_DB is auto-enabled when /var/lib/... is not writable
python main.py
```

## API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/register` | optional `registration_token` | Tenant self-register; returns subdomain |
| POST | `/api/heartbeat` | none | Update `last_seen` / host:port |
| GET | `/api/tenants` | admin | List tenants |
| DELETE | `/api/tenants/{id}` | admin | Deregister |
| GET | `/api/health` | none | Liveness + tenant counts |

Admin auth: `Authorization: Bearer $ADMIN_API_KEY` or `X-API-Key: $ADMIN_API_KEY`.

## Docker

```bash
docker compose up -d --build
# optional Postgres sidecar (not used by app yet):
docker compose --profile postgres up -d
```

## Routing

1. Cloudflare Tunnel wildcard → this service on port 9000.
2. Host `kura-zen-42.shogun-os.ai` → proxy to tenant `host:port`.
3. WebSocket paths proxy to the same backend for chat gateways.
4. Apex host serves registry API + service banner only.
