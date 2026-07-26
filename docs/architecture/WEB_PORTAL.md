# Web Portal Architecture

> **Product contract (source of truth)**  
> 1. Each customer install gets **one random URL** under our domain (`*.shogun-os.ai`).  
> 2. URLs are assigned **only by our central registry + our Cloudflare account**.  
> 3. Customers **never** need a Cloudflare account, API token, or subdomain choice.  
> 4. Each customer gets **one dashboard** for **all** department agents.  
> 5. Hermes still runs **one profile per department** under the hood (isolation).

---

## Layers

```
Customer browser
      │
      ▼
https://quiet-lotus-42.shogun-os.ai     ← random, assigned by us
      │
      │  DNS CNAME (our Cloudflare zone)
      ▼
Cloudflare Edge / Tunnel connector
      │
      ▼
Customer machine: shogun-web (FastAPI + React)   port 8787
      │
      ├── ONE Dashboard UI
      │     ├── Department cards (HR, Finance, …)
      │     ├── Chat with selected agent
      │     └── Settings / providers / onboarding
      │
      └── Hermes profiles (backend only)
            hr-manager · finance-manager · …
```

Central control plane (our VPS):

```
registry.shogun-os.ai  (FastAPI registry)
  ├── POST /api/register  → assign random subdomain + optional CF tunnel
  ├── POST /api/heartbeat
  ├── GET  /api/tenants   (admin)
  └── Cloudflare API (OUR token) → tunnel + DNS for each tenant
```

---

## What customers experience

| Step | Customer does | System does |
|------|----------------|-------------|
| Install | `./scripts/install-web.sh --admin-email …` | Builds UI, creates admin, registers |
| URL | Nothing | Registry returns `https://{adj}-{noun}-{nn}.shogun-os.ai` |
| Cloudflare | Nothing | Our registry creates tunnel/DNS with **our** CF credentials |
| Dashboard | Login once | **One** home with all department agents |
| Departments | Activate cards in the same UI | Spawns/links Hermes profiles behind the scenes |

---

## What is NOT the design

- ❌ Customer picks `acme.shogun-os.ai` during install (vanity = future paid/admin only)
- ❌ Customer creates their own Cloudflare tunnel / zone
- ❌ Separate web portal URL per department
- ❌ Separate “department dashboards” as different products

Department **detail pages** inside the single portal (chat with Jinzai, brain, docs) are fine — they are routes under the same origin, not separate tenants.

---

## Registry registration contract

Tenant installer → `POST {REGISTRY_URL}/api/register`:

```json
{
  "host": "127.0.0.1",
  "port": 8787,
  "create_tunnel": true,
  "registration_token": "<shared secret>",
  "metadata": { "display_name": "Acme", "admin_email": "admin@acme.com" }
}
```

Response:

```json
{
  "tenant_id": "…",
  "subdomain": "quiet-lotus-42",
  "public_url": "https://quiet-lotus-42.shogun-os.ai",
  "tunnel": { "tunnel_token": "…", "status": "active" }
}
```

Defaults:

| Setting | Default | Meaning |
|---------|---------|---------|
| `ALLOW_PREFERRED_SUBDOMAIN` | `false` | Ignore vanity requests |
| `ENABLE_TUNNEL_PROVISIONING` | `true` (when CF set) | Auto tunnel + DNS |
| `DEFAULT_CREATE_TUNNEL` | `true` | Create tunnel unless client opts out |
| Tunnel local service | `http://127.0.0.1:{port}` | cloudflared runs **on the tenant machine** |

---

## Repo layout

| Path | Role |
|------|------|
| `shogun-web/server/` | Tenant portal API |
| `shogun-web/ui/` | Single React app (Dashboard + Department routes) |
| `shogun-web/registry/` | Central registry (deploy on our VPS) |
| `scripts/install-web.sh` | Customer installer (no subdomain prompt) |
| `scripts/apply-registry-response.py` | Writes assigned URL into `~/.shogun-os/web.json` |
| `docs/ops/cloudflare-registry-setup.md` | **Operator** Cloudflare checklist |

---

## Related

- Operator Cloudflare steps: [`docs/ops/cloudflare-registry-setup.md`](../ops/cloudflare-registry-setup.md)
- High-level system diagram: [`ARCHITECTURE.md`](../../ARCHITECTURE.md)
- Installer: `./scripts/install-web.sh --help`
