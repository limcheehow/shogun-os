# Shogun OS

> **Every department gets its own AI agent with a Samurai persona, its own gbrain source, and shared infrastructure. One Slack bot per profile. One unified task system. One brain. One web portal.**

Shogun OS is a reference architecture for running an entire organization through AI agents. Built on [Hermes Agent](https://hermes-agent.nousresearch.com) + [GBrain](https://github.com/garrytan/gbrain), it gives each department a dedicated AI operator with role-specific tools, memory, and autonomy — isolated from every other department by design.

**NEW in v3.12.0:** **Shogunify** — `/shogunify` slash command on every profile to scaffold skills, connectors, and workflows the right way (profile-aware + gbrain-compliant).

**Also recent:** v3.10.0 Web Portal (`*.shogun-os.ai`); v3.9.0 provider abstractions across 10 domains.

Choose your **industry vertical** during setup: **General** (services, consulting, software) or **Manufacturing** (factory, production, OEM). Shared profiles deploy regardless of industry; department-specific profiles activate based on your selection.

> **~30 minutes to a working multi-agent setup.** Clone the repo, run the installer, wire Slack bots. Your agents handle the rest.
> **~10 minutes to a working web portal.** Run the web installer; we assign a random `*.shogun-os.ai` URL from our Cloudflare. One dashboard for all departments.

> **Agents:** start with [`AGENTS.md`](AGENTS.md). **Humans:** start with [`SETUP.md`](SETUP.md). **LLMs:** fetch [`llms.txt`](llms.txt) for the documentation map.

---

## What's New

### v3.12.0 — Shogunify
- **`/shogunify` slash command** on all Hermes profiles (skill auto-registers as slash)
- **Questionnaires** for skill, integration/connector, workflow/cron, and new department profile
- **Profile path map** — writes land in the correct `~/.hermes/profiles/<name>/` tree
- **`install-to-profiles.py`** — symlink/copy a skill into default + named profiles
- **E2E suite** — disposable test profile, demo skill + connector scaffold, slash registration checks
- **Wiring** — `generate-profile.py` shared skills, `install.sh`, `verify-install.sh`, `HUB.md`

### v3.10.0 — Web Portal
- **Multi-tenant web portal** — random `*.shogun-os.ai` URL per company (our Cloudflare)
- **One company dashboard** for all department agents (not per-dept portals)
- **Onboarding wizard** — 4-step setup: departments → company info → provider config → launch
- **Unified auth** — Google/Microsoft OAuth + email/password with forced first-login change
- **Central registry** — assigns URLs + tunnels; customers never touch Cloudflare
- **Provider abstractions** — Bukku, QuickBooks, Xero for accounting; Jibble for HR time-tracking

### v3.9.0 — Provider Abstractions
- **10 domain recipes** — HR, Accounting, Procurement, CRM, Marketing, Compliance, Support, Engineering, Projects, Product
- **Unified bridge pattern** — one MCP bridge per domain, provider plugins loaded via `importlib`
- **OAuth helper** — shared token cache at `~/.hermes/mcp-tokens/<domain>-<provider>.json`
- **Full P0 contracts** — 11 tools per domain, standardized across providers

---

## Prerequisites

Before deploying Shogun OS, you need one core tool installed on your server (Linux or WSL2). GBrain is included in the repo and auto-configured by `init-gbrain.sh` during setup.

### 1. Hermes Agent

The AI agent runtime that powers every department profile.

```bash
# Install via the official script
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Verify
hermes --version
```

**Links:** [Documentation](https://hermes-agent.nousresearch.com/docs) | [GitHub](https://github.com/NousResearch/hermes-agent) | [Install Guide](https://hermes-agent.nousresearch.com/docs/getting-started/installation)

### 2. PostgreSQL 16+

Required by GBrain for vector storage (pgvector extension). GBrain's `init-gbrain.sh` script will auto-install and configure PostgreSQL 16 for you if it's not already present.

```bash
# Or install manually
sudo apt install postgresql-16 postgresql-16-pgvector
```

**GBrain is included in this repo** — no separate install needed. The `init-gbrain.sh` script (v1.2.0+) handles everything:
- PostgreSQL auto-install & pgvector setup
- Ollama local embedding (nomic-embed-text, 768d, zero cost)
- 11 department source creation
- `shogun-enterprise` schema pack activation
- Cron wiring (nightly dream cycle at 2am, pg_dump backup at 2:30am)
- Dual MCP transport (stdio for Hermes profiles, HTTP for web portal)

### 3. Optional but Recommended

| Tool | Why | Install |
|------|-----|---------|
| **Slack Bot** | Every department agent communicates via Slack | [api.slack.com/apps](https://api.slack.com/apps) — create one bot per profile |
| **Google Workspace SA-DWD** | Gmail/Calendar/Drive access via service accounts | See [`recipes/google-dwd.md`](recipes/google-dwd.md) |
| **Ollama** | Local embeddings (768d, zero cost) — auto-installed by init-gbrain.sh if not present | `curl -fsSL https://ollama.com/install.sh \| sh` |
| **Cloudflare Account (operator)** | Our zone only — customers never need CF | [cloudflare.com](https://cloudflare.com) — free plan works |
| **Docker** | Registry service deployment | `sudo apt install docker.io docker-compose` |

### Quick Check

Run this to confirm everything is in place:

```bash
which hermes  && echo "✅ Hermes" || echo "❌ Hermes"
which docker  && echo "✅ Docker" || echo "⚠️  Docker (for web registry)"
which psql    && echo "✅ PostgreSQL" || echo "⚠️  PostgreSQL (auto-installed by init-gbrain.sh)"
```
> GBrain, Ollama, and pgvector are verified by `init-gbrain.sh` during setup — no separate check needed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Shogun OS Architecture                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Web Portal │  │  Web Portal │  │  Web Portal │  ...         │
│  │  (Tenant A) │  │  (Tenant B) │  │  (Tenant C) │             │
│  │  *.shogun-  │  │  *.shogun-  │  │  *.shogun-  │             │
│  │   os.ai     │  │   os.ai     │  │   os.ai     │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                    │
│         └────────────────┴────────────────┘                    │
│                          │                                      │
│                 ┌────────▼────────┐                             │
│                 │ Central Registry │  ← Cloudflare Tunnel       │
│                 │  (shogun-os.ai)  │    Wildcard Routing        │
│                 └────────┬────────┘                             │
│                          │                                      │
│  ┌───────────────────────┼───────────────────────┐              │
│  │                       │                       │              │
│  │  ┌──────────┐ ┌───────▼───┐ ┌──────────┐      │              │
│  │  │  HR      │ │  Finance  │ │ Projects │ ...  │              │
│  │  │  Jinzai  │ │   Koku    │ │ Gorobei  │      │              │
│  │  ├──────────┤ ├───────────┤ ├──────────┤      │              │
│  │  │ Slack Bot│ │ Slack Bot │ │ Slack Bot│      │              │
│  │  │ Web Chat │ │ Web Chat  │ │ Web Chat │      │              │
│  │  └────┬─────┘ └─────┬─────┘ └────┬─────┘      │              │
│  │       │             │            │            │              │
│  │       └─────────────┴────────────┴────────────┘              │
│  │                         │                                    │
│  │                ┌────────▼────────┐                           │
│  │                │   GBrain MCP    │                           │
│  │                │  (Hybrid Search) │                           │
│  │                └────────┬────────┘                           │
│  │                         │                                    │
│  │           ┌─────────────┼─────────────┐                      │
│  │           │             │             │                      │
│  │      ┌────▼───┐  ┌─────▼────┐  ┌────▼────┐                 │
│  │      │ Shared  │  │Dept Brain│  │ Shared  │                 │
│  │      │ Skills  │  │ Sources  │  │ Recipes │                 │
│  │      └─────────┘  └──────────┘  └──────────┘                 │
│  └──────────────────────────────────────────────────────────────┘
```

### Four Layers

**Layer 0: Web Portal** — Multi-tenant FastAPI + React. Each company gets **one** random `*.shogun-os.ai` URL assigned by **our** central registry + Cloudflare (customers never log into CF). **One dashboard** for all department agents; Hermes profiles stay isolated underneath. See [`docs/architecture/WEB_PORTAL.md`](docs/architecture/WEB_PORTAL.md).


**Layer 1: Hermes Agent Profiles** — Each department gets a dedicated Hermes profile with its own SOUL.md (persona), config.yaml (model config + MCP servers + Slack connection), skills, cron jobs, and gbrain source. Physical isolation prevents cross-dept data leaks.

**Layer 2: GBrain (Knowledge Layer)** — Every profile connects to gbrain via MCP. Hybrid search across 11 department sources (`hr/`, `finance/`, `projects/`, etc.) with federated read of `shared/`. Local PostgreSQL 16 with pgvector, segmented by source. Local Ollama embeddings (768d, zero cost). `shogun-enterprise` schema pack with 30+ department page types.

**Layer 3: Slack (Communication Layer)** — One Slack bot per profile. Each bot lives in its department's channels, receives DMs from team members, and posts cron deliveries to its home channel. Slack bot isolation is a hard requirement.

### Samurai Personas

Every profile embodies a Samurai persona from Akira Kurosawa's *Seven Samurai* (plus extras), chosen for their domain:

| Profile | Persona | Role |
|---------|---------|------|
| HR | **Jinzai** (人材 — "Talent") | People operations, culture |
| Finance | **Koku** (石 — "Stone") | Financial stability |
| Projects | **Gorobei** (五郎兵衛 — "Strategist") | Project execution |
| Procurement | **Kura** (蔵 — "Vault") | Supply chain |
| Product | **Shi** (志 — "Will") | Product vision |
| CRM | **Kizuna** (絆 — "Bond") | Client relationships |
| Marketing | **Haiku** (俳句) | Brand & narrative |
| Compliance | **Kata** (型 — "Form") | Standards & audits |
| Customer Support | **Bōei** (防衛 — "Defense") | Client shield |
| Coding | **Takumi** (匠 — "Artisan") | Engineering craft |

---

## Agent Roster — Shared vs Industry-Specific

Shogun OS profiles are organized by **industry vertical**. Every company gets shared profiles, then picks an industry for department-specific agents.

| Category | Profiles | Details |
|----------|----------|---------|
| **Shared** (every company) | Jinzai, Koku, Kura, Kizuna, Haiku, Kata, Boei, Takumi, Benkei | HR, Finance, Procurement, CRM, Marketing, Compliance, Support, Engineering, Executive |
| **General** (services/software) | Gorobei, Shi | Project management, Product management → [`profiles-general.md`](profiles-general.md) |
| **Manufacturing** (factory/OEM) | Kojo, Kensa, Shuri, Soko, Anzen | Production, Quality, Maintenance, Warehouse, HSE → [`profiles-manufacturing.md`](profiles-manufacturing.md) |
| **Retail** (stores/e-commerce) | Tenpo, Shohin, Denshi, Kokyaku, Ryutsu, Hyoji | Stores, Merchandising, E-commerce, CRM-Loyalty, Supply Chain, VM → [`profiles-retail.md`](profiles-retail.md) |

> **Deploy:** `./install.sh --deploy all --industry manufacturing` — creates 13 profiles total.
> **Deploy:** `./install.sh --deploy all --industry general` — creates 10 profiles total.
> **Deploy:** `./install.sh --deploy all --industry retail` — creates 14 profiles total.

---

## Provider Abstractions (NEW in v3.9.0)

Every domain has a unified provider abstraction with pluggable backends:

| Domain | Providers | Contract Tools | Bridge |
|--------|-----------|---------------|--------|
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

**Pattern:** One MCP bridge per domain. Provider plugins loaded via `importlib` from `plugins/` directory. Config via `ACCT_PROVIDER` env var. OAuth tokens cached at `~/.hermes/mcp-tokens/<domain>-<provider>.json`.

See [`docs/recipes/creating-provider-abstractions.md`](docs/recipes/creating-provider-abstractions.md) for the full guide.  
**Agent shortcut:** run **`/shogunify`** (see [`docs/recipes/shogunify.md`](docs/recipes/shogunify.md)) to scaffold a domain or provider with the profile-aware questionnaire.

---

## Quick Start

### Option A: Full Install (Profiles + Web Portal)

```bash
# 1. Prerequisites
which hermes                    # Hermes Agent installed
which psql                      # PostgreSQL (or let init-gbrain.sh install it)

# 2. Clone this repo
git clone https://github.com/limcheehow/shogun-os.git
cd shogun-os

# 3. Install skills, scripts, and templates
./scripts/install.sh

# 4. Initialize gbrain (auto-installs PostgreSQL + Ollama if needed)
./scripts/init-gbrain.sh --yes

# 5. Deploy all 10 department profiles
./scripts/install.sh --deploy all

# 6. Set up web portal (NEW)
./scripts/install-web.sh

# 7. Verify everything is in place
./scripts/verify-install.sh
./scripts/verify-web.sh
```

### Option B: Web Portal Only

```bash
# 1. Clone and install web dependencies
git clone https://github.com/limcheehow/shogun-os.git
cd shogun-os/shogun-web

# 2. Install and verify
./scripts/install-web.sh
./scripts/verify-web.sh

# 3. Start the portal
cd server && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
# Visit http://localhost:8000
```

The full end-to-end setup playbook (Google DWD, Slack bot configuration, cron wiring) lives in [`SETUP.md`](SETUP.md).

---

## Web Portal Setup

Each install gets **one random** `*.shogun-os.ai` URL and **one dashboard** for all department agents.

- **Login** — Google/Microsoft OAuth + email/password  
- **Onboarding** — company + departments + providers (once)  
- **Dashboard** — all department agents in one place (chat / status / activate)  
- **Central registry (ours)** — assigns URL + Cloudflare tunnel; customers never open Cloudflare  

### Prerequisites (operator / Tapway)

1. Domain on **our** Cloudflare zone — `shogun-os.ai`  
2. Registry VPS with Docker  
3. Follow **[`docs/ops/cloudflare-registry-setup.md`](docs/ops/cloudflare-registry-setup.md)**  

Customers only need: a machine, Docker/Python, and a registration token you give them.

### Setup Steps

```bash
# ── Operator (once) ──────────────────────────────────────────
# See docs/ops/cloudflare-registry-setup.md
cd shogun-web/registry && cp .env.example .env
# Set CLOUDFLARE_*, REGISTRATION_TOKEN, ENABLE_TUNNEL_PROVISIONING=true
docker compose up -d --build

# ── Customer machine ─────────────────────────────────────────
export SHOGUN_REGISTRY_URL=https://registry.shogun-os.ai
export SHOGUN_REGISTRY_TOKEN=<token-from-us>
./scripts/install-web.sh --admin-email admin@customer.com
# Prints assigned URL, e.g. https://quiet-lotus-42.shogun-os.ai
# No subdomain prompt. No Cloudflare login.
```

Design contract: [`docs/architecture/WEB_PORTAL.md`](docs/architecture/WEB_PORTAL.md).

### Web Portal Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Tenant A    │   │  Tenant B    │   │  Tenant C    │
│ quiet-lotus-42│  │ hana-mizu-17 │   │ tora-yama-3  │
│  ONE dashboard│  │  ONE dashboard│  │  ONE dashboard│
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │ cloudflared      │                  │
       └──────────────────┴──────────────────┘
                          │
                 ┌────────▼────────┐
                 │ Our Cloudflare  │  zone: shogun-os.ai
                 │ + Registry VPS  │  assigns random slugs
                 └─────────────────┘
```

---

## Install by AI Agent (recommended)

If you have an AI agent running (Hermes, OpenClaw, Codex, Claude Code), paste this:

```
Retrieve and follow the instructions at:
https://raw.githubusercontent.com/limcheehow/shogun-os/main/INSTALL_FOR_AGENTS.md
```

The agent installs Shogun OS, creates profiles, sets up gbrain sources, configures Slack bots, wires scrum crons, and verifies the install end-to-end. ~30 minutes. You answer questions about Slack tokens and channel IDs.

---

## Contents

| File | What It Covers |
|------|----------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System design, gbrain sources, MCP wiring, model config |
| [`SETUP.md`](SETUP.md) | End-to-end setup playbook from zero to running profiles |
| [`PROFILE_CATALOG.md`](PROFILE_CATALOG.md) | All 10 department profiles with personas, sources, skills, crons |
| [`CRON_INVENTORY.md`](CRON_INVENTORY.md) | Every cron job across all profiles (54 total) |
| [`RECIPE_INDEX.md`](RECIPE_INDEX.md) | All 8 integration recipes with dependencies and setup order |
| [`AGENTS.md`](AGENTS.md) | Agent-first deployment guide (paste this into your agent) |
| [`INSTALL_FOR_AGENTS.md`](INSTALL_FOR_AGENTS.md) | Full install protocol for AI agents |
| `shogun-web/` | **NEW:** Web portal (FastAPI + React + registry) |
| `recipes/` | Provider abstraction recipes (accounting, HR, CRM, etc.) |
| `templates/` | Profile configs, scrum config templates, web portal config |
| `skills/` | 25+ reusable Hermes skills for any company |
| `scripts/` | Provisioning scripts (install, profile gen, cron wire, web portal, etc.) |
| `examples/` | 9 scrum config templates with placeholders |

---

## Shared Skills

Every profile loads shared Hermes skills shipped with this repo:

| Skill | Purpose |
|-------|---------|
| **`shogunify`** | **Slash `/shogunify`** — structured questionnaire to add skills, connectors, workflows, and profiles (profile-path aware) |
| `company-workflow` | Mandatory 6-gate workflow enforcement (Triage→RCA→Brainstorm→Plan→TDD→E2E) for any feature/bug request |
| `department-scrum` | Cross-department 3-tier scrum workflow (9am/11am/5pm), production-hardened v3.0.0 with 15 documented pitfalls |
| `brain-ingest-pipeline` | Unified 5-phase COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE data pipeline |
| `slack-formatting` | Slack-optimized formatting (mrkdwn + Block Kit) |
| `brain-compliance` | Gbrain-compliant brain page standards & validator |
| `profile-enrichment` | Company/contact research via web + gbrain-native writes |
| `gbrain-operations` | GBrain CLI operations (sync, embed, doctor, dream, MCP) |
| `brain-first-lookup` | Mandatory brain-first lookup protocol before external searches |
| `gbrain-capture` | Quick capture of thoughts, ideas, and observations to gbrain |
| `gbrain-query` | Three-layer gbrain query pipeline (search → recall → think) |
| `gbrain-think` | Multi-hop synthesis with cited answers + conflict analysis |
| `gbrain-maintain` | Brain health checks, orphan detection, link campaigns |
| `gbrain-frontmatter-guard` | YAML frontmatter validation on every brain write |
| `brain-link-campaign` | Reduce orphan pages, increase link coverage |
| `brain-file-delivery` | Enforce file-attachment delivery for brain pages |
| `brain-e2e-tests` | Comprehensive brain compliance testing suite |
| `gbrain-signal-detector` | Ambient signal capture for gbrain |
| `timeline-inject-v2` | gbrain-compatible timeline entry injection |
| `coding-workflow` | Master coding workflow with subagent delegation |
| `systematic-debugging` | 4-phase root cause debugging methodology |
| `writing-plans` | Implementation plan authoring (bite-sized tasks, paths, code) |
| `plan` | Plan mode — write markdown plans without execution |
| `verify-first` | Behavioral overlay — verify before claiming, challenge assumptions |
| `search-router` | Intelligent search routing — analyzes query intent and routes to best source |

Docs: [`docs/recipes/shogunify.md`](docs/recipes/shogunify.md).

---

## What You Get

### 10 Department Agents

Each runs as an isolated Hermes Agent profile with:
- **SOUL.md** — persona definition with voice, boundaries, and domain knowledge
- **config.yaml** — model config (deepseek-v4-flash by default), gbrain MCP, Slack connection
- **Skills** — domain-specific + shared skills
- **Cron jobs** — 3-tier daily scrum + department-specific extras
- **gbrain source** — isolated knowledge store with federated read of `shared/`

### Web Portal

- **Multi-tenant** — each company install gets one random `*.shogun-os.ai` URL (our Cloudflare)
- **One dashboard** — all department agents in a single UI (not separate portals)
- **Onboarding wizard** — 4-step setup: departments → company info → provider config → launch
- **Unified auth** — Google/Microsoft OAuth + email/password with forced first-login change
- **Provider config** — Per-department API keys and settings
- **Central registry** — assigns URL + tunnel; customers never need a Cloudflare account

### 54 Automated Cron Jobs

| Category | Jobs | Type |
|----------|------|------|
| Daily scrum (9 departments × 3 tiers) | 27 | 9 no_agent + 18 agent |
| Infrastructure (brain ingest, gmail, calendar, drive) | 8 | Mixed |
| Department-specific (pipeline, budget, leave, etc.) | 15 | Agent |
| Health & monitoring | 4 | no_agent |

### 25+ Reusable Skills

Shipped in this repo, installable via Hermes skill tap:
```bash
hermes skills tap add limcheehow/shogun-os
hermes skills install shogun-os/company-workflow
```

### Complete Setup Tooling

| Script | What It Does |
|--------|-------------|
| `install.sh` | Install skills, scripts, templates, and deploy profiles |
| `install-web.sh` | **NEW:** Set up web portal (build React, generate config, register tenant) |
| `generate-profile.py` | Generate a new Hermes profile with SOUL.md + config.yaml from template |
| `install-to-profiles.py` | *(in `skills/shogunify/scripts/`)* Install/symlink a skill into default + named profiles for slash commands |
| `wire-crons.py` | Generate and apply cron jobs per profile type |
| `init-gbrain.sh` | Initialize gbrain with all 11 department sources |
| `verify-install.sh` | Full install verification with MCP connectivity probe |
| `verify-web.sh` | **NEW:** Verify web portal setup |
| `backup-crons.py` | Export all cron jobs to portable JSON for migration |
| `restore-crons.py` | Restore cron jobs from backup |

---

## Troubleshooting

### Install fails: gbrain init fails

GBrain is included in the repo — no separate install needed. If `init-gbrain.sh` fails:

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check Ollama is running (for local embeddings)
sudo systemctl status ollama

# Re-run init with verbose output
./scripts/init-gbrain.sh --yes --verbose

# Manual fallback: rebuild gbrain from repo
git clone https://github.com/garrytan/gbrain.git /tmp/gbrain
cd /tmp/gbrain && bun install && bun run build
# Then re-run init-gbrain.sh
```

### Profile creation fails: "Profile already exists"
Use `--force` to overwrite:
```bash
python3 scripts/generate-profile.py hr-manager --type hr --force
```

### Scrum crons not firing
1. Check `scrum.yaml` exists in profile directory
2. Verify Slack channel IDs are correct
3. Run `hermes cron list` to check job status
4. Check gateway logs: `grep -i "scrum" ~/.hermes/logs/gateway.log | tail -10`

### Slack bot not responding
1. Invite bot to channel: `/invite @botname`
2. Check `allowed_channels` in profile's config.yaml
3. Verify gateway is running: `systemctl --user status hermes-gateway-<profile>`

### Agent says "I don't have access to that department"
Each agent is scoped to its own gbrain source. If it needs cross-department context, ensure:
1. Federated read is enabled in config.yaml: `GBRAIN_FEDERATED_READ=true`
2. The data lives in `shared/` source (visible to all profiles)

### Web portal not loading (NEW)
1. Check React build exists: `ls shogun-web/ui/dist/`
2. Verify static_dir in `~/.shogun-os/web.json` points to `ui/dist`
3. Check backend logs: `python3 -m uvicorn main:app --host 0.0.0.0 --port 8000`
4. Verify registry is running (if using subdomains): `docker compose ps`

---

## License

MIT. Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research and [GBrain](https://github.com/garrytan/gbrain) by Garry Tan / Y Combinator.
