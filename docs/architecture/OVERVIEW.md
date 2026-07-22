# Architecture Overview

## System Design

Shogun OS runs on three layers, each providing isolation and autonomy for department-specific AI agents.

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

Every profile connects to gbrain via MCP (30+ tools available through the MCP server). The brain architecture uses 11 sources:

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

**Hybrid search:** gbrain uses pgvector in Supabase for semantic + keyword search. All profiles share the same Supabase instance but are segmented by source.

### Layer 3: Slack (Communication Layer)

One Slack bot per profile. Each bot:
- Lives in its department's Slack channels
- Receives DMs from department members
- Has its own app ID and bot token
- Posts cron delivery to its home channel

**Slack bot isolation is a hard requirement.** A single bot trying to serve all departments would create cross-department visibility issues (every profile sees every channel).

---

## Profile Architecture

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
  default: ~anthropic/claude-sonnet-4-20250514
  provider: backup-provider
  fallback:
    - provider: custom
      model: deepseek-v4-flash
      base_url: https://primary-provider-intl.aliyuncs.com/compatible-mode/v1
```

### Shared MCP Servers (all profiles)

| MCP Server | Purpose |
|-----------|---------|
| `gbrain` | Brain search/read/write via gbrain MCP |
| `stock-scanner` | Market data (optional, for financial profiles) |

---

## Scrum Architecture

### Gateway-Based DM Handling

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
|------|------|--------|-------------|
| 9:00 AM | `no_agent` | `send-scrum-dms.py --profile <p>` | Sends DMs, saves state, logs to gbrain |
| 11:00 AM | Agent | `check-scrum-replies.py warn --profile <p>` | Cross-ref against gbrain, warn non-responders |
| 5:00 PM | Agent | `check-scrum-replies.py report --profile <p>` | Compliance + SMART gates + brain cross-ref |

---

## Data Flow

### Brain Ingest Pipeline

Unified **COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE** pipeline for all data sources:

```
COLLECT ──→ gmail-triage.py (email, 30min)
         ──→ collect-calendar.py (calendar, daily 6AM)

ROUTE ──→ Classify signals (Sales/CRM, Projects, HR, Finance)
         ──→ Find matching brain pages via gbrain query
         ──→ Flag unmatched as brain_missing

BRIDGE ──→ Extract entities → create typed links
         ──→ Add timeline entries → detect risks

ENRICH ──→ Web research → fill missing person/company data

VALIDATE ──→ Run compliance check on every modified page
           ──→ Orphan detection → link coverage check
```

---

## Cron Architecture

Two-tier cron system:

**Tier 1: Deterministic (no_agent)**
- Runs code, produces data. No LLM involved.
- Cheap, fast, reliable.
- Examples: email collector, calendar sync, brain sync, token watchdog

**Tier 2: Agent (LLM-driven)**
- Reads output from Tier 1, makes judgment calls.
- Uses LLM tokens but on a limited schedule (3x/day, not every 30min).
- Examples: email enrichment, scrum compliance reports, drive enrichment

---

## Security Model

### Profile Isolation

| Boundary | How It's Enforced |
|----------|------------------|
| Config isolation | Each profile has its own config.yaml |
| Skill isolation | Each profile has its own skills/ directory |
| Memory isolation | Each profile has its own memories/ |
| Knowledge isolation | Each profile writes to its own gbrain source |
| Slack isolation | Each profile has its own Slack bot token |
| Process isolation | Each profile runs as an independent Hermes gateway process |

### Data Flow Security

- **API keys**: stored in `~/.hermes/.env` (main) or per-profile `.env` — never in the repo
- **Service accounts**: Google DWD key at `~/.hermes/secrets/google-dwd-sa.json` — never in the repo
- **Slack tokens**: stored in profile `.env` files — never in the repo
- **Brain data**: Supabase at rest encryption + row-level security by gbrain source
- **gateway secrets**: webhook secret in config.yaml (auto-generated on install)

See [`SECURITY.md`](SECURITY.md) for the full threat model.