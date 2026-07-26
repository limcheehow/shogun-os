# Shogun OS Central Registry

Reverse-proxy + tenant registry for `*.{REGISTRY_DOMAIN}` traffic.

## Product rules

- Customers get a **random** subdomain (`adjective-noun-NN`) — they never pick one.
- DNS + tunnels use **our** Cloudflare credentials only.
- Each tenant is one company portal with **one dashboard** for all departments.
- `ALLOW_PREFERRED_SUBDOMAIN=false` by default (vanity is admin/paid later).

Operator Cloudflare setup: [`docs/ops/cloudflare-registry-setup.md`](../../docs/ops/cloudflare-registry-setup.md).

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
| POST | `/api/register` | optional `registration_token` | Assign random subdomain (+ tunnel) |
| POST | `/api/heartbeat` | none | Update `last_seen` / host:port |
| GET | `/api/tenants` | admin | List tenants |
| DELETE | `/api/tenants/{id}` | admin | Deregister |
| GET | `/api/health` | none | Liveness + tenant counts |

Admin auth: `Authorization: Bearer <ADMIN_API_KEY>` or `X-API-Key: <ADMIN_API_KEY>`

Register body (customer installer):

```json
{
  "host": "127.0.0.1",
  "port": 8787,
  "create_tunnel": true,
  "registration_token": "…",
  "metadata": { "display_name": "Acme" }
}
```

Do **not** send `preferred_subdomain` in the default product path.

## Docker

```bash
docker compose up -d --build
# optional Postgres sidecar (not used by app yet):
docker compose --profile postgres up -d
```

## Routing

1. Customer browser hits `https://quiet-lotus-42.shogun-os.ai`.
2. Cloudflare resolves per-tenant CNAME → tenant tunnel (created on register).
3. `cloudflared` on the **customer** machine forwards to `http://127.0.0.1:8787`.
4. Apex / `registry.{domain}` serves this registry API for register/heartbeat/admin.
