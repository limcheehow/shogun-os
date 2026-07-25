# Setup Playbook

> End-to-end guide from zero to running profiles. Follow in order.

## Phase 0: Prerequisites

```bash
# Hermes Agent
pip install hermes-agent  # or your install method
hermes --version

# GBrain
curl -fsSL https://bun.sh/install | bash
bun install -g github:garrytan/gbrain
gbrain --version

# Tokscale (for AI spend tracking)
npm install -g tokscale

# Google Auth libraries
pip install google-auth google-api-python-client
```

## Phase 1: Google DWD (Foundation)

See [`recipes/google-dwd.md`](recipes/google-dwd.md) for the full playbook.

**Summary:**
1. Create service account in Google Cloud Console
2. Enable Domain-Wide Delegation in Google Workspace Admin Console
3. Download service account key to `~/.hermes/secrets/google-dwd-sa.json` (the brain ingest pipeline scripts also look for this at `~/.hermes/service-account-key.json` via symlink — create with `ln -sf ~/.hermes/secrets/google-dwd-sa.json ~/.hermes/service-account-key.json`)
4. Verify token generation

**Depends on:** Google Workspace admin access.

## Phase 2: GBrain Setup

### 2.1 Initialize Brain

```bash
gbrain init
# Choose: Postgres + pgvector via Supabase (recommended for >1000 files)
```

### 2.2 Create Sources

```bash
gbrain sources add shared
gbrain sources add hr
gbrain sources add finance
gbrain sources add projects
gbrain sources add procurement
gbrain sources add products
gbrain sources add crm
gbrain sources add marketing
gbrain sources add compliance
gbrain sources add engineering
gbrain sources add support
```

Each source becomes its own folder under `~/brain/`.

### 2.3 Configure Federated Read

In each profile's `config.yaml` (except HR, which owns `shared/`):

```bash
gbrain config set federated_read true
```

Or set the environment variable:

```bash
export GBRAIN_FEDERATED_READ=true
```

### 2.4 Import Staff Directory

```bash
mkdir -p ~/brain/shared/staff
# Create one page per employee with:
# ---
# type: person
# department: engineering
# role: Senior Developer
# ---
# ...person details...

gbrain import ~/brain/shared/staff --no-embed
gbrain embed --stale
```

## Phase 3: Profile Creation

### 3.1 Create Each Profile

For each department, create the Hermes profile:

```bash
hermes profile create <dept>-manager
```

Then apply the template:
- `SOUL.md` — persona definition
- `config.yaml` — model config + MCP servers + Slack connection
- `skills/` — domain skills (symlink shared skills)
- `cron/jobs/` — cron templates
- `memories/` — initial persisted facts

### 3.2 Symlink Shared Skills

```bash
cd ~/.hermes/profiles/<dept>-manager/skills
ln -sf ../../../../skills/shared ./shared
```

### 3.3 Wire GBrain MCP

In each profile's `config.yaml`:

```yaml
mcp_servers:
  gbrain:
    command: "gbrain"
    args: ["mcp"]
    env:
      GBRAIN_SOURCE: "<dept>"
      GBRAIN_FEDERATED_READ: "true"
      SUPABASE_URL: "${SUPABASE_URL}"
      SUPABASE_SERVICE_ROLE_KEY: "${SUPABASE_SERVICE_ROLE_KEY}"
```

## Phase 4: Slack Bot Configuration

### 4.1 Create Slack Apps

One Slack app per profile.

1. Go to https://api.slack.com/apps → Create New App
2. Choose "From an app manifest"
3. Set bot token scopes: `chat:write`, `channels:history`, `im:history`, `users:read`, `reactions:write`
4. Install to workspace — copy the Bot User OAuth Token
5. Enable Socket Mode (for event subscriptions)
6. Subscribe to bot events: `message.im`, `app_mention`

### 4.2 Configure Profile

In `config.yaml`:

```yaml
slack:
  bot_token: "xoxb-..."
  app_token: "xapp-..."
  signing_secret: "..."
```

### 4.3 Invite Bots to Channels

```bash
# Invite each bot to its department's Slack channels
# e.g., #hr-general for hr-manager, #project-alpha for project-manager
```

## Phase 5: Cron Jobs

### 5.1 Default Profile Infrastructure Crons

These run on the `default` profile (shared infrastructure):

```bash
# Email Collector (no_agent, every 30min)
hermes cron create --name "Email Collector" \
  --schedule "*/30 * * * *" --script email-collector.py --no-agent

# Email Enrichment (agent, 3x/day)
hermes cron create --name "Email Enrichment" \
  --schedule "0 9,13,17 * * 1-5" \
  --skills "gbrain-operations" --enabled-toolsets "terminal,file,search"

# Calendar Sync (no_agent, daily 6AM)
hermes cron create --name "Calendar Sync" \
  --schedule "0 6 * * *" --script calendar-sync.py --no-agent

# Calendar Attendee Enrichment (daily 8AM)
hermes cron create --name "Calendar Attendee Enrichment" \
  --schedule "0 8 * * *" \
  --skills "gbrain-operations" --enabled-toolsets "terminal,file,search"

# Drive Sync (no_agent, weekdays 12/16/20)
hermes cron create --name "Drive Sync" \
  --schedule "0 12,16,20 * * 1-5" --script drive-sync.py --no-agent

# Token Utilization (weekly Monday 8AM, no_agent)
hermes cron create --name "Token Utilization Report" \
  --schedule "0 8 * * 1" --script token-util-report.sh --no-agent
```

### 5.2 Department Scrum (3-Tier Workflow)

Each department profile uses the **3-tier scrum workflow** from `skills/department-scrum/`.

#### Prerequisites

Before wiring crons, you need:

1. **SOUL.md "Scrum DM Handling" section** — copy from `skills/department-scrum/references/soul-snippet.md`
2. **scrum.yaml** — create `~/.hermes/profiles/<profile>/scrum.yaml` (see `examples/scrum-configs/` and `skills/department-scrum/references/scrum-config-schema.md`)
3. **Generic scripts** — `send-scrum-dms.py` and `check-scrum-replies.py` at `~/.hermes/scripts/scrum/`

#### Wire 3 Crons Per Profile

```bash
# 9am — Send DMs (no_agent)
hermes cron create --name "<profile>-scrum-9am" \
  --schedule "0 9 * * 1-5" \
  --script "send-scrum-dms.py --profile <profile>" \
  --no-agent \
  --deliver "slack:<channel_updates>"

# 11am — Warn non-responders (agent)
hermes cron create --name "<profile>-scrum-11am" \
  --schedule "0 11 * * 1-5" \
  --prompt "Loaded skills: department-scrum, task-management, staff-lookup. STEP 1: Run check-scrum-replies.py warn --profile <profile>. STEP 2: Cross-ref against gbrain source: <source>. STEP 3: Post summary to slack:<channel_updates>." \
  --skills "department-scrum,task-management,staff-lookup" \
  --enabled-toolsets "terminal,file,web,search" \
  --deliver "slack:<channel_updates>"

# 5pm — Compliance report (agent)
hermes cron create --name "<profile>-scrum-5pm" \
  --schedule "0 17 * * 1-5" \
  --prompt "Loaded skills: department-scrum, task-management, staff-lookup. STEP 1: Run check-scrum-replies.py report --profile <profile>. STEP 2: Full brain cross-ref + SMART gates. STEP 3: Post enriched report." \
  --skills "department-scrum,task-management,staff-lookup" \
  --enabled-toolsets "terminal,file,web,search" \
  --deliver "slack:<channel_updates>"
```

See `skills/department-scrum/templates/` for full cron prompt templates with placeholders.

#### Verify

```bash
python3 ~/.hermes/scripts/scrum/test-scrum-cross-dept.py
# Expected: 48/48 tests passing, covering Projects, Products, HR, Finance
```

### 5.3 Extra Department Crons

| Profile | Extra Cron | Schedule |
|---------|-----------|----------|
| hr-manager | Candidate Pipeline | Mon 10AM |
| hr-manager | Recruitment GDrive Sync | Daily 6AM |
| crm-manager | Deal Activity Sync | Hourly 9-18 weekdays |
| crm-manager | Sales Pipeline | Mon 9AM |
| crm-manager | Weekly Summary | Fri 5PM |
| finance-manager | Daily Burn Rate | Daily 8AM |
| finance-manager | Invoice Aging | Mon 8AM |
| finance-manager | Monthly P&L | 1st of month 8AM |
| finance-manager | Weekly Budget | Mon 8AM |
| procurement-manager | Contract Expiry | Mon 9AM |
| product-manager | Sprint Cycle | Bi-weekly Mon |
| hr-manager | Jibble Attendance | Weekdays 9:30AM |
| hr-manager | Jibble Timesheet | Weekly Mon 10AM |

## Phase 6: Model Configuration

### 6.1 Set Up Model Presets

Two named presets:

**Standard** (most profiles):
```yaml
model:
  default: deepseek-v4-flash
  provider: custom:primary-provider
  fallback:
    - provider: backup-provider
      model: deepseek/deepseek-v4-flash
```

**Coding** (coding-agent only):
```yaml
model:
  default: claude-sonnet-4
  provider: anthropic
  fallback:
    - provider: custom:primary-provider
      model: deepseek-v4-flash
```

### 6.2 Switch Profile

```bash
python3 scripts/switch-profile.py <profile-name> --model standard
python3 scripts/switch-profile.py coding-agent --model coding
```

## Phase 7: Web Portal Setup

Multi-tenant FastAPI + React portal. Each install gets a `*.shogun-os.ai` (or custom domain) subdomain with login (Google/Microsoft OAuth + email/password), a 4-step onboarding wizard, department dashboards, and a unified chat interface. A central registry on a VPS routes wildcard traffic through Cloudflare Tunnel to tenant backends.

Skip this phase if you only need Slack + Hermes profiles without a browser UI.

### Prerequisites

1. **Domain registered** — `shogun-os.ai` (or your own domain on Cloudflare DNS)
2. **Cloudflare account** — Free plan works; zone must hold the portal domain
3. **VPS with Docker** — Hosts the central registry (Hetzner, DigitalOcean, AWS, etc.)
4. **Optional OAuth apps** — Google Cloud OAuth client and/or Microsoft Entra app for SSO on the portal login page
5. **Profiles already created** — Finish Phases 0–6 first so department gateways have something to expose

### 7.1 Deploy Central Registry to VPS

On the VPS:

```bash
# Clone or copy the repo, then:
cd shogun-web/registry
cp .env.example .env
# Edit .env:
#   CLOUDFLARE_API_TOKEN=...
#   CLOUDFLARE_ZONE_ID=...
#   REGISTRY_DOMAIN=shogun-os.ai   # or your domain
#   REGISTRATION_TOKEN=...        # shared secret tenants use to register
#   ADMIN_API_KEY=...

docker compose up -d --build

# Sanity check
curl -s http://localhost:9000/api/health
```

The registry listens on port **9000**, stores tenants, and reverse-proxies `*.{REGISTRY_DOMAIN}` (and WebSocket chat paths) to each tenant’s host:port. See `shogun-web/registry/README.md` for the full API.

### 7.2 Create Cloudflare Tunnel

One-time on the VPS (or a machine that can manage the tunnel):

```bash
# Install cloudflared if needed, then:
cloudflared tunnel login
cloudflared tunnel create shogun-registry

# Note the tunnel ID from the output, then point the tunnel at the registry:
# (~/.cloudflared/<tunnel-id>.json credentials + config.yml ingress)
# Ingress example:
#   - hostname: "*.shogun-os.ai"
#     service: http://localhost:9000
#   - hostname: "registry.shogun-os.ai"   # optional dedicated API host
#     service: http://localhost:9000
#   - service: http_status:404

cloudflared tunnel run shogun-registry
# Prefer a systemd unit so the tunnel survives reboot
```

### 7.3 Configure Wildcard DNS

In the Cloudflare DNS dashboard for the zone:

```text
Type:  CNAME
Name:  *
Target: <tunnel-id>.cfargotunnel.com
Proxy:  Proxied (orange cloud)

# Optional apex/API host
Type:  CNAME
Name:  registry
Target: <tunnel-id>.cfargotunnel.com
Proxy:  Proxied
```

Wildcard `*.shogun-os.ai` (or your domain) now routes through the tunnel into the central registry, which selects the tenant backend by Host header.

### 7.4 Run install-web.sh on Each Tenant

On every machine that should expose a portal instance (often each company install / laptop-or-server running Hermes):

```bash
# Required env for registry registration (values from VPS .env / operators):
export SHOGUN_REGISTRY_URL="https://registry.shogun-os.ai"   # or your registry URL
export SHOGUN_REGISTRY_TOKEN="<registration_token>"
export SHOGUN_DOMAIN_SUFFIX="shogun-os.ai"                   # must match REGISTRY_DOMAIN

# Optional OAuth (Google / Microsoft) for portal login:
export SHOGUN_GOOGLE_CLIENT_ID="..."
export SHOGUN_GOOGLE_CLIENT_SECRET="..."
export SHOGUN_MS_CLIENT_ID="..."
export SHOGUN_MS_CLIENT_SECRET="..."
export SHOGUN_MS_TENANT_ID="common"

# Optional overrides:
#   --subdomain acme --admin-email admin@acme.com --display-name "Acme Corp"

./scripts/install-web.sh
# Builds React UI, installs Python deps, writes ~/.shogun-os/ config,
# registers the tenant with the central registry, installs systemd user
# services for the portal + department Hermes gateways.
```

Installer highlights:

| Flag / env | Purpose |
|------------|---------|
| `--subdomain <name>` | Force subdomain (else auto-generated) |
| `--admin-email` | Initial admin user email |
| `--skip-registry` | Local-only (no central registration) |
| `--skip-systemd` | Config + build only; start manually |
| `--dry-run` | Print actions without applying |

Default local portal port is **8787** (`SHOGUN_WEB_PORT`). Department gateways bind 9101–9110.

### 7.5 Verify with verify-web.sh

```bash
./scripts/verify-web.sh
# or quick (skip slow network / deep DB checks):
./scripts/verify-web.sh --quick

# Limited auto-repair (daemon-reload / restart web service):
./scripts/verify-web.sh --fix
```

The script checks tenant config (`~/.shogun-os/web.json`, `config.yaml`), SQLite DB, React `ui/dist`, systemd user units, local portal health, department gateways, and registry connectivity.

### 7.6 Visit Subdomain and Complete Onboarding

```bash
# Subdomain is printed by install-web.sh and stored in ~/.shogun-os/web.json
open "https://<your-subdomain>.shogun-os.ai"
# or:
xdg-open "https://<your-subdomain>.shogun-os.ai"
```

1. Open the subdomain URL (TLS terminated by Cloudflare).
2. Sign in with email/password (from install output) or Google/Microsoft OAuth if configured.
3. Complete the **onboarding wizard** (org details, departments, connections).
4. Confirm department dashboards load (Chat, Brain, Docs) and chat WebSockets stay connected.

Local-only smoke test (no tunnel):

```bash
cd shogun-web/server && python3 -m uvicorn main:app --host 0.0.0.0 --port 8787
# Visit http://localhost:8787
```

## Phase 8: Verification

### 8.1 Health Check

```bash
# Test gbrain connectivity
hermes -p hr-manager --exec "mcp_gbrain_get_health"

# Test Slack delivery
hermes -p hr-manager --exec "send_message('Standup agent online')"

# Test cron
hermes -p hr-manager cron run <job-id>
```

### 8.2 Verify Each Profile

```bash
# Check all profiles respond
for p in hr-manager finance-manager project-manager procurement-manager \
         product-manager crm-manager marketing-manager compliance-manager \
         customer-support coding-agent; do
  echo "$p: $(hermes -p $p --exec 'mcp_gbrain_whoami' 2>&1 | head -1)"
done
```

### 8.3 Web Portal Checks

```bash
# Full portal suite (tenant config, DB, UI build, services, registry)
./scripts/verify-web.sh

# Install-wide verification (when available)
./scripts/verify-install.sh --quick
# Full (includes MCP connectivity):
./scripts/verify-install.sh
```

Manual checks:

| Check | How |
|-------|-----|
| Registry liveness | `curl -s https://registry.shogun-os.ai/api/health` (or VPS `localhost:9000`) |
| Tenant page | `https://<subdomain>.shogun-os.ai` loads login UI |
| API health | From tenant: `curl -s http://127.0.0.1:8787/api/health` (or configured port) |
| OAuth | Login → Google/Microsoft completes redirect without error |
| Onboarding | Wizard finishes and marks tenant onboarded |
| Department chat | Open a dept dashboard; WebSocket stays connected |
| Tunnel | `cloudflared tunnel info shogun-registry` / watchdog logs if installed |

## Phase 9: Go Live

When ready to activate, unpause all template cron jobs:

```bash
# List template crons (from profile cron/jobs/*.md)
# Activate each via hermes cron create or un-pause existing
hermes cron list --profile hr-manager
hermes cron resume <job-id>
```

## Post-Setup

- Monitor token utilization weekly (cron already set up)
- Check brain health: `gbrain doctor`
- Review standup summaries for quality
- Re-run `./scripts/verify-web.sh` after portal or tunnel changes
- Extend with new recipes as needs emerge

## Troubleshooting

### Profiles / Slack / GBrain

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `mcp_gbrain_*` fails | Wrong `GBRAIN_SOURCE` or Supabase env | Check profile `config.yaml` MCP env; `gbrain doctor` |
| Slack bot silent | Socket Mode off / bad tokens | Re-check `bot_token` / `app_token`; bot events `message.im`, `app_mention` |
| Cron never fires | Job paused or wrong profile | `hermes cron list --profile <p>`; `hermes cron resume <id>` |
| Federated read empty | Flag not set | `GBRAIN_FEDERATED_READ=true` on non-HR profiles |

### Web Portal

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `*.shogun-os.ai` DNS fails / 1000-class CF error | Wildcard CNAME missing or not proxied | Add `*` → `<tunnel-id>.cfargotunnel.com` (proxied); wait for DNS |
| Tunnel up but registry unreachable | Ingress points at wrong port/host | Confirm `cloudflared` ingress → `http://localhost:9000`; `docker compose ps` on VPS |
| Registry healthy; subdomain 502/blank | Tenant never registered or offline | Re-run `./scripts/install-web.sh`; check registry tenant list; tenant host:port reachable from registry (or heartbeats updating) |
| `install-web.sh` registry error | Wrong `SHOGUN_REGISTRY_URL` / token / domain suffix | Align tenant env with VPS `.env` (`REGISTRATION_TOKEN`, `REGISTRY_DOMAIN`) |
| Portal won't start locally | Missing deps or port bind | Install script Python deps; free port 8787; check user systemd units under `~/.config/systemd/user/` |
| UI 404 / empty assets | React not built | Re-run installer without `--skip-ui-build`; confirm `shogun-web/ui/dist/` exists |
| OAuth redirect_uri mismatch | Console clients lack subdomain URL | Add `https://<subdomain>.shogun-os.ai/...` (and localhost if testing) to Google/Microsoft OAuth redirect URIs |
| Login OK, chat disconnects | WS not proxied / gateway down | Registry must proxy WebSockets; start department gateway units (ports 9101–9110); `./scripts/verify-web.sh` |
| Onboarding stuck | DB/config write failure | Check `~/.shogun-os/data/shogun-web.db` permissions; `./scripts/verify-web.sh --fix` |
| Works on localhost only | Skipped registry/tunnel | Complete Phase 7.1–7.3; drop `--skip-registry` on install |

Useful logs:

```bash
# Tenant portal (systemd user)
journalctl --user -u shogun-web -n 100 --no-pager   # unit name may vary; list with: systemctl --user list-units 'shogun*'

# Registry (VPS)
cd shogun-web/registry && docker compose logs -f --tail=100

# Cloudflare tunnel
cloudflared tunnel info shogun-registry
# or tail cloudflared / watchdog logs under ~/.cloudflared/
```
