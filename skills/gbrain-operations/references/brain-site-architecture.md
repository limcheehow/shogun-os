# Brain Site Architecture

## Request Flow

```
User browser
    ↓
cheehow-brain.gotapway.com (DNS: Cloudflare)
    ↓
Cloudflare Tunnel (ID: d28fb846-d57c-4238-81c3-a4fb47663bf8)
    ↓ Named "samurai-vqa" tunnel
    ↓
localhost:8766 ← brain-auth-proxy.service
    ↓ HTTP Basic Auth (cheehow / BRAIN_PASS)
    ↓
localhost:8767 ← brain-site-server.service (Quartz or dynamic)
    ↓
~/brain-quartz/public/  (Quartz static build)
--OR--
~/brain/  (dynamic renderer serving .md files on-the-fly)
```

## Tunnel Config

File: `~/.cloudflared/config.yml`

```yaml
tunnel: d28fb846-d57c-4238-81c3-a4fb47663bf8
credentials-file: /home/cheehow/.cloudflared/d28fb846-d57c-4238-81c3-a4fb47663bf8.json
ingress:
  - hostname: cafe.gotapway.com
    service: http://localhost:3000
  - hostname: playground.gotapway.com
    service: http://localhost:8765
  - hostname: cheehow-brain.gotapway.com
    service: http://localhost:8766
  - hostname: crm.gotapway.com
    service: http://localhost:8768
  - service: http_status:404
```

Tunnel script: `~/.hermes/scripts/cloudflared-tunnel.sh` — runs `cloudflared tunnel run d28fb846-...`

## Systemd Services

### brain-auth-proxy.service (port 8766)
File: `~/.config/systemd/user/brain-auth-proxy.service`
- **Source:** `~/brain-site/brain-auth-proxy.py`
- **Role:** HTTP Basic Auth reverse proxy
- **Creds:** `BRAIN_USER=cheehow`, `BRAIN_PASS=<env>`
- **Upstream:** `http://localhost:8767`
- **Auth:** Prompts for user/password, proxies everything to upstream
- **Dependency:** `After=brain-site-server.service`, `Requires=brain-site-server.service`

### brain-site-server.service (port 8767)
File: `~/.config/systemd/user/brain-site-server.service`
- **Source:** `~/brain-quartz/serve.py` (Quartz), or `~/brain-site/brain-site-server.py` (dynamic)
- **Role:** Serves brain content as rendered HTML

## gbrain MCP Server (port 8768)
- **URL:** `http://localhost:8768`
- **Tunnel:** `crm.gotapway.com` → port 8768
- **Features:** Admin dashboard (React SPA at `/admin`), MCP endpoint at `/mcp`, health at `/health`
- **Engine:** Postgres (local)
- **Systemd:** `~/.config/systemd/user/gbrain-mcp.service` (currently for CRM)

## Known Issues

### Quartz scaling ceiling
Quartz v5 times out building with 20K+ files because:
1. It checks git dates on every file
2. Untracked files emit individual warnings → output flood (20K+ warnings)
3. `npx quartz build` hangs for 5+ minutes and gets killed
4. The `public/` output directory may be left empty or deleted

**User is evaluating replacing Quartz with a dynamic markdown renderer** that:
- Reads `~/brain/` on-the-fly (no build step)
- Renders .md → HTML per-request
- Handles any number of files
- Shows changes instantly

### Port mapping
| Port | Service | Tunnel Hostname |
|------|---------|----------------|
| 8766 | brain-auth-proxy | cheehow-brain.gotapway.com |
| 8767 | brain-site-server | (behind auth proxy) |
| 8768 | gbrain MCP server | crm.gotapway.com |
