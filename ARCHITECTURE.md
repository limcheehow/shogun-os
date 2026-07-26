# Architecture

## System Design

Shogun OS runs on four layers:

```
┌─────────────────────────────────────────────────────────────────┐
│              Layer 0: Web Portal (Multi-Tenant UI)              │
│   Random *.shogun-os.ai ← OUR Cloudflare (customer never logs in)│
│   ONE company dashboard for ALL department agents               │
│   FastAPI (server/) + React (ui/) + central registry/           │
│   Onboarding · Unified dashboard · Dept agent workspaces        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│           Layer 1: Hermes Agent Profiles (×10 depts)            │
│  SOUL.md · config.yaml · skills/ · cron/ · memories/ · gbrain   │
│  Provider abstractions (MCP bridges) per domain                 │
└───────┬─────────────────────────────┬───────────────────────────┘
        │                             │
┌───────▼──────────┐         ┌────────▼───────────────────────────┐
│ Layer 2: GBrain  │         │ Layer 3: Slack (per-profile bots)  │
│ Knowledge / MCP  │         │ DMs · channels · cron delivery     │
│ 11 sources +     │         │ Isolation is a hard requirement    │
│ federated shared │         │                                    │
└──────────────────┘         └────────────────────────────────────┘
```

### Layer 0: Web Portal

Multi-tenant **FastAPI + React** application. Product rules:

1. **One URL per customer company**, randomly assigned (e.g. `quiet-lotus-42.shogun-os.ai`)
2. **DNS + tunnels only from OUR Cloudflare account** — customers never need CF
3. **One dashboard** listing all department agents (not a portal per department)
4. Hermes still uses **one profile per department** under the hood (isolation)

- **Central registry on our VPS** creates random subdomains and (optionally) per-tenant Cloudflare tunnels via the Cloudflare API
- Customer installer registers with a shared token and receives `public_url` + tunnel connector token
- Repo layout under `shogun-web/`:
  - `server/` — tenant portal API
  - `ui/` — single React app (Dashboard + department workspaces)
  - `registry/` — central routing / tenant registry (operator deploy)
- Provisioning & checks: `install-web.sh` + `verify-web.sh`
- Design doc: [`docs/architecture/WEB_PORTAL.md`](docs/architecture/WEB_PORTAL.md)
- Operator Cloudflare checklist: [`docs/ops/cloudflare-registry-setup.md`](docs/ops/cloudflare-registry-setup.md)
- **WSL / Azure Windows deploy (agent runbook):** [`docs/ops/deploy-registry-wsl-azure.md`](docs/ops/deploy-registry-wsl-azure.md)

### Layer 1: Hermes Agent Profiles

Each department gets a dedicated Hermes Agent profile. Profiles are isolated — they have their own:
- **SOUL.md** — persona, voice, boundaries
- **config.yaml** — model config, MCP servers, Slack connection
- **skills/** — domain-specific skills (symlinks to shared/ for common ones)
- **cron/** — scheduled jobs
- **memories/** — persisted facts
- **gbrain source** — department's own brain pages

**Why one profile per department instead of one profile with channel routing:**
- Physical isolation prevents cross-department data leaks
- Each Slack bot has its own DMs and channel memberships
- Each profile can have different model configs (e.g., Coding uses Claude, HR uses DeepSeek)
- Cron jobs schedule independently per department

### Layer 2: GBrain (Knowledge Layer)

Every profile connects to gbrain via MCP (83 tools available). The brain architecture:

```
gbrain sources/
├── shared/          ← Federated read, write restricted to HR
├── hr/
├── finance/
├── projects/
├── procurement/
├── products/
├── crm/
├── marketing/
├── compliance/
├── engineering/
└── support/
```

**Federated read:** Every profile can read from `shared/` (staff directory, company policies, taxonomy). Writes go to the profile's own source.

**Production details:**

| Component | Implementation |
|-----------|---------------|
| **Engine** | Local PostgreSQL 16 with pgvector extension |
| **Embedding** | Ollama `nomic-embed-text` (768d, local inference, $0 API cost) |
| **Schema Pack** | `shogun-enterprise` — 30+ department-specific page types (staff, deal, vendor, ticket, etc.) with typed link verbs |
| **MCP Transport** | stdio for Hermes Agent profiles + HTTP (port **3100**) for web portal integration |
| **Nightly Maintenance** | Dream cycle (consolidate + synthesize + patterns) at 2:00 AM; `pg_dump` backup at 2:30 AM |

### Layer 3: Slack (Communication Layer)

One Slack bot per profile. Each bot:
- Lives in its department's Slack channels
- Receives DMs from department members
- Has its own app ID and bot token
- Posts cron delivery to its home channel

**Slack bot isolation is a hard requirement.** A single bot trying to serve all departments would create cross-department visibility issues (every profile sees every channel).

## Provider Abstractions

Every domain exposes a **unified MCP bridge pattern** with pluggable provider plugins (one bridge per domain; providers loaded via `importlib`). Skills and crons call **contract tools** only — never provider-specific APIs.

| Domain | Providers | Contract Tools | Bridge / recipes |
|--------|-----------|----------------|------------------|
| **HR / Time-Tracking** | Jibble, Kami | 11 `tt_*` tools | `recipes/hr/` |
| **Accounting** | Bukku, QuickBooks, Xero | 11 `acct_*` tools | `recipes/accounting/` |
| **Procurement** | — | 11 `proc_*` tools | `recipes/procurement/` |
| **CRM** | HubSpot | 11 `crm_*` tools | `recipes/crm/` |
| **Marketing** | — | 11 `mkt_*` tools | `recipes/marketing/` |
| **Compliance** | — | 11 `comp_*` tools | `recipes/compliance/` |
| **Support** | — | 11 `spt_*` tools | `recipes/support/` |
| **Engineering** | — | 11 `eng_*` tools | `recipes/engineering/` |
| **Projects** | — | 11 `proj_*` tools | `recipes/projects/` |
| **Product** | — | 11 `pd_*` tools | `recipes/product/` |

**Pattern:** One MCP bridge per domain. Provider plugins from a `plugins/` directory. Active provider selected via env (e.g. `ACCT_PROVIDER`). OAuth tokens cached at `~/.hermes/mcp-tokens/<domain>-<provider>.json`.

Full guide: [`docs/recipes/creating-provider-abstractions.md`](docs/recipes/creating-provider-abstractions.md). Also see [`docs/architecture/PROVIDER_ABSTRACTION.md`](docs/architecture/PROVIDER_ABSTRACTION.md).

## MCP Architecture

### Standard Model Config

```yaml
model:
  default: deepseek-v4-flash
  provider: custom:primary-provider
  fallback:
    - provider: backup-provider
      model: deepseek/deepseek-v4-flash
```

### Coding Model Config

```yaml
model:
  default: claude-sonnet-4
  provider: anthropic
  fallback:
    - provider: custom:primary-provider
      model: deepseek-v4-flash
```

### Shared MCP Servers (all profiles)

| MCP Server | Purpose | Config Location |
|-----------|---------|----------------|
| `gbrain` | Brain search/read/write | Per-profile config.yaml |
| `stock-scanner` | Market data | Per-profile config.yaml |

### Per-Profile MCP Servers

| Profile | Additional MCP |
|---------|---------------|
| hr-manager | Jibble time tracking |
| crm-manager | (none beyond shared) |
| marketing-manager | (none beyond shared) |

## Google DWD Auth

All Google API access (Gmail, Calendar, Drive, Slides) uses **Domain-Wide Delegation** — a service account impersonating `your-user@your-domain.com`. No user-level OAuth tokens.

```
Google Cloud Console:
  Project → Service Account (hermes-agent@...)
  ↓ Service Account Key JSON → ~/.hermes/secrets/google-dwd-sa.json
  ↓
Google Workspace Admin Console:
  Security → API Controls → Domain-Wide Delegation
  Add Client ID + Scopes
  ↓
Hermes scripts (default profile):
  service_account.Credentials.from_service_account_file(
    SA_PATH, scopes=SCOPES, subject='your-user@your-domain.com'
  )
  creds.refresh(google.auth.transport.requests.Request())
  # creds.token ready for any Google API
```

**DWD vs Individual OAuth:**

| Aspect | Individual OAuth | DWD Service Account |
|--------|-----------------|---------------------|
| Setup effort | User clicks consent screen every 90 days | Admin enables DWD once |
| Token lifetime | ~7 days inactivity → dead | Never expires |
| Refresh | Refresh token may expire | `creds.refresh()` always works |
| Multiple profiles | Token per profile | One SA key shared |
| Revocation | User revokes | Admin revokes |

## Data Flow

### Email → Brain

```
Gmail (via DWD)
  ↓
Email Collector (no_agent cron, every 30min)
  ↓ Collects → filters noise → generates Gmail links
  ↓
~/brain/daily/email/digests/{date}.md
  ↓
Email Enrichment (agent cron, 3x/day)
  ↓ Reads digest → updates person/company brain pages
  ↓
gbrain sync
```

### Calendar → Brain

```
Google Calendar (via DWD)
  ↓
Calendar Sync (no_agent cron, daily 6AM)
  ↓ Paginated retrieval → daily markdown files
  ↓
~/brain/daily/calendar/{year}/{date}.md
  ↓
Attendee Enrichment (agent cron, daily 8AM)
  ↓ Extracts attendees → creates/updates person pages
  ↓
gbrain import + embed
```

### Drive → Brain

```
Google Drive Folders (via DWD)
  ↓
Drive Sync (no_agent cron, weekdays 12/16/20)
  ↓ Lists files → reads content → writes brain pages
  ↓
~/brain/meetings/ | proposals/ | reports/
  ↓
Drive Enrichment (agent cron, weekdays 13/17)
  ↓ Extracts entities → updates person/company pages
  ↓
gbrain import + embed
```

## Cron Architecture

Two-tier cron system:

**Tier 1: Deterministic (no_agent)**
- Runs code, produces data. No LLM involved.
- Cheap, fast, reliable.
- Examples: email collector, calendar sync, drive sync, token watchdog, token utilization report

**Tier 2: Agent (LLM-driven)**
- Reads output from Tier 1, makes judgment calls.
- Uses LLM tokens but on a limited schedule (3x/day, not every 30min).
- Examples: email enrichment, attendee enrichment, drive enrichment

## Scrum Architecture

### Option B: Gateway-Based DM Handling

Every profile's scrum runs without socket daemons. The Hermes gateway handles all Slack DMs:

```
Slack Events API
  ↓
Hermes Gateway (per profile)
  ↓
SOUL.md instruction: "Is sender in today's scrum team?"
  ├─ Yes, scrum reply → check-scrum-replies.py report --profile <p>
  │                    → save state → post to #scrum-channel
  └─ No → answer with domain knowledge using gbrain
```

### 3-Tier Cron Cadence

Every department runs the same 3-tier scrum pattern (weekdays):

| Time | Type | Script | What it does |
|---|---|---|---|
| 9:00 AM | `no_agent` | `send-scrum-dms.py --profile <p>` | Sends DMs, saves state, logs to gbrain |
| 11:00 AM | Agent | `check-scrum-replies.py warn --profile <p>` | Cross-ref against gbrain, warn non-responders |
| 5:00 PM | Agent | `check-scrum-replies.py report --profile <p>` | Compliance + SMART gates + brain + gbrain |

Each profile has its own `scrum.yaml` config (team roster, task ID patterns, domain terms). See `skills/department-scrum/`.

This split follows the **code for data, LLMs for judgment** pattern — adopted from gbrain's recipe philosophy.

## Brain Ingest Pipeline

Unified **COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE** pipeline for all data sources. Replaces the old per-source collector + enrichment crons.

### Data Flow

```
E-mail (Gmail API, SA-DWD)
  ↓
gmail-triage.py (no_agent, */30min)
  ↓ Labels inbox, priority scores, batch rotation (3 batches of 3-4 accounts)
  ↓ State: ~/.hermes/cache/gmail-triage-state.json
  ↓

Calendar (Google Calendar API, SA-DWD)
  ↓
collect-calendar.py (no_agent, daily 6AM)
  ↓ Events → ~/brain/data/calendar/ as gbrain-indexable markdown
  ↓ 10 accounts, 7d lookback + 14d lookahead
  ↓

ROUTE → BRIDGE → ENRICH → VALIDATE (agent, 9/13/17 weekdays)
  ↓
mcp_gbrain_* tools:
  └─ ROUTE: mcp_gbrain_query to find matching pages → classify signals
  └─ BRIDGE: mcp_gbrain_add_link + mcp_gbrain_add_timeline_entry
  └─ ENRICH: profile-enrichment skill → web search for missing data
  └─ VALIDATE: validate-brain-page.py → orphan detection → link coverage
```

### Key Design Decisions

| Decision | Why |
|---|---|
| **SA-DWD over OAuth** | No token refresh, never expires, covers all team members with one key |
| **Batch rotation for Gmail** | Avoids memory spikes — processes 3 accounts per 30min run |
| **Config-driven account list** | `config/gmail-batches.json` — edit one file, no script changes |
| **5-phase pipeline** | Every source follows the same flow, no exceptions |
| **VALIDATE as a phase** | Brain compliance is non-negotiable — every page gets validated |
| **Plugin packaging** | First-class Hermes plugin: installable, registerable, versioned |
