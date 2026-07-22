# Shogun OS

> **Every department gets its own AI agent with a Samurai persona, its own gbrain source, and shared infrastructure. One Slack bot per profile. One unified task system. One brain.**

Shogun OS is a reference architecture for running an entire organization through AI agents. Built on [Hermes Agent](https://hermes-agent.nousresearch.com) + [GBrain](https://github.com/garrytan/gbrain), it gives each department a dedicated AI operator with role-specific tools, memory, and autonomy — isolated from every other department by design.

Choose your **industry vertical** during setup: **General** (services, consulting, software) or **Manufacturing** (factory, production, OEM). Shared profiles deploy regardless of industry; department-specific profiles activate based on your selection.

> **~30 minutes to a working multi-agent setup.** Clone the repo, run the installer, wire Slack bots. Your agents handle the rest.

> **Agents:** start with [`AGENTS.md`](AGENTS.md). **Humans:** start with [`SETUP.md`](SETUP.md). **LLMs:** fetch [`llms.txt`](llms.txt) for the documentation map.

## Prerequisites

Before deploying Shogun OS, you need two core tools installed on your server (Linux or WSL2):

### 1. Hermes Agent

The AI agent runtime that powers every department profile.

```bash
# Install via the official script
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Verify
hermes --version
```

**Links:** [Documentation](https://hermes-agent.nousresearch.com/docs) | [GitHub](https://github.com/NousResearch/hermes-agent) | [Install Guide](https://hermes-agent.nousresearch.com/docs/getting-started/installation)

### 2. GBrain (Knowledge Base)

The hybrid-search knowledge engine that stores and retrieves every department's data.

```bash
# Install via Bun (recommended)
curl -fsSL https://bun.sh/install | bash
export PATH="$HOME/.bun/bin:$PATH"
bun install -g github:garrytan/gbrain

# Verify
gbrain --version  # should be v0.42.x+
```

**Links:** [GitHub](https://github.com/garrytan/gbrain) | [AGENTS.md](https://github.com/garrytan/gbrain/blob/main/AGENTS.md) (install protocol for AI agents)

### 3. Optional but Recommended

| Tool | Why | Install |
|------|-----|---------|
| **Slack Bot** | Every department agent communicates via Slack | [api.slack.com/apps](https://api.slack.com/apps) — create one bot per profile |
| **Google Workspace SA-DWD** | Gmail/Calendar/Drive access via service accounts | See [`recipes/google-dwd.md`](recipes/google-dwd.md) |
| **PostgreSQL 16+** | Production-grade session storage (vs PGLite) | `sudo apt install postgresql-16` or use Supabase |
| **Node.js 20+** | Required by GBrain (Bun runtime) | `curl -fsSL https://deb.nodesource.com/setup_20.x \| sudo bash -` |

### Quick Check

Run this to confirm everything is in place:

```bash
which hermes && echo "✅ Hermes" || echo "❌ Hermes"
which gbrain && echo "✅ GBrain" || echo "❌ GBrain"
which bun    && echo "✅ Bun"    || echo "⚠️  Bun (recommended for gbrain)"
```

## What this looks like

Say you're the CEO. You want to know how things are going across the company. Here's what you'd ask, and what you'd get back.

**You ask:**
> "What's the status of the IOI project, and is the team healthy?"

**Most project trackers give you a dashboard to navigate and interpret yourself.** You open Jira, find the project board, scan through cards, switch to Slack for context, check the support ticket system — it's your brain doing the synthesis across 5 tools.

**Shogun OS gives you a synthesized answer across departments:**

```
IOI Project — Gorobei (Projects)

73% complete. 3 of 8 milestones delivered. Next: camera
installation (pending vendor schedule).

RISK: Support ticket TS-2026-012 is 3 days past SLA — Bōei
      flagged it this morning. IOI customer has mentioned
      this twice. Gorobei escalated to Kizuna (CRM).

Team health — Jinzai (HR)
- 9 team members. 0 on leave today. 1 MC yesterday (recovered).
- Last week's SPACE Pulse: 4.2/5 (stable).
- No overdue performance reviews.

Budget — Koku (Finance)
- Project budget: RM 240K. Spent: RM 178K (74%).
- Cloud cost this month: RM 14.2K (within forecast).
- Runway: 14 months at current burn rate.
```

Each sentence is a claim written by the department agent, verified against its gbrain source, and cross-referenced with the shared staff directory. You get the answer, not the dashboard.

## Agent Roster — Shared vs Industry-Specific

Shogun OS profiles are organized by **industry vertical**. Every company gets shared profiles, then picks an industry for department-specific agents.

| Category | Profiles | Details |
|----------|----------|---------|
| **Shared** (every company) | Jinzai, Koku, Kura, Kizuna, Haiku, Kata, Boei, Takumi, Benkei | HR, Finance, Procurement, CRM, Marketing, Compliance, Support, Engineering, Executive |
| **General** (services/software) | Gorobei, Shi | Project management, Product management → [`profiles-general.md`](profiles-general.md) |
| **Manufacturing** (factory/OEM) | Kojo, Kensa, Shuri, Soko, Anzen | Production, Quality, Maintenance, Warehouse, HSE → [`profiles-manufacturing.md`](profiles-manufacturing.md) |

> **Deploy:** `./install.sh --deploy all --industry manufacturing` — creates 13 profiles total.
> **Deploy:** `./install.sh --deploy all --industry general` — creates 10 profiles total.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Shogun OS Architecture                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐     ┌──────────┐   │
│  │  HR      │ │ Finance  │ │ Projects │ ... │  Coding  │   │
│  │  Jinzai  │ │ Koku     │ │ Gorobei  │     │  Takumi  │   │
│  ├──────────┤ ├──────────┤ ├──────────┤     ├──────────┤   │
│  │ Slack Bot│ │Slack Bot │ │Slack Bot │     │Slack Bot │   │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘     └────┬─────┘   │
│       │            │            │                │          │
│       └────────────┴────────────┴────────────────┘          │
│                            │                                 │
│                   ┌────────▼────────┐                        │
│                   │   GBrain MCP    │                        │
│                   │  (Hybrid Search) │                       │
│                   └────────┬────────┘                        │
│                            │                                 │
│              ┌─────────────┼─────────────┐                   │
│              │             │             │                   │
│         ┌────▼───┐  ┌─────▼────┐  ┌────▼────┐              │
│         │ Shared  │  │Dept Brain│  │ Shared  │              │
│         │ Skills  │  │ Sources  │  │ Recipes │              │
│         └─────────┘  └──────────┘  └──────────┘             │
└──────────────────────────────────────────────────────────────┘
```

### Three Layers

**Layer 1: Hermes Agent Profiles** — Each department gets a dedicated Hermes profile with its own SOUL.md (persona), config.yaml (model config + MCP servers + Slack connection), skills, cron jobs, and gbrain source. Physical isolation prevents cross-dept data leaks.

**Layer 2: GBrain (Knowledge Layer)** — Every profile connects to gbrain via MCP. Hybrid search across 11 department sources (`hr/`, `finance/`, `projects/`, etc.) with federated read of `shared/`. One Supabase instance, segmented by source.

**Layer 3: Slack (Communication Layer)** — One Slack bot per profile. Each bot lives in its department's channels, receives DMs from team members, and posts cron deliveries to its home channel. Slack bot isolation is a hard requirement — a single bot serving all departments creates cross-dept visibility issues.

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

## Quick Start

```bash
# 1. Prerequisites
which hermes                    # Hermes Agent installed
which gbrain                    # GBrain installed (v0.42.x+)

# 2. Clone this repo
git clone https://github.com/limcheehow/shogun-os.git
cd company-os

# 3. Install skills, scripts, and templates
./scripts/install.sh

# 4. Initialize gbrain with department sources
./scripts/init-gbrain.sh --yes

# 5. Deploy all 10 department profiles
./scripts/install.sh --deploy all

# 6. Verify everything is in place
./scripts/verify-install.sh
```

The full end-to-end setup playbook (Google DWD, Slack bot configuration, cron wiring) lives in [`SETUP.md`](SETUP.md).

## Install by AI Agent (recommended)

If you have an AI agent running (Hermes, OpenClaw, Codex, Claude Code), paste this:

```
Retrieve and follow the instructions at:
https://raw.githubusercontent.com/limcheehow/shogun-os/main/INSTALL_FOR_AGENTS.md
```

The agent installs Shogun OS, creates profiles, sets up gbrain sources, configures Slack bots, wires scrum crons, and verifies the install end-to-end. ~30 minutes. You answer questions about Slack tokens and channel IDs.

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
| `templates/` | Profile configs, scrum config templates |
| `recipes/` | Self-contained integration recipes (DWD, ingest, scrum, etc.) |
| `skills/` | 6 reusable Hermes skills for any company |
| `scripts/` | 7 provisioning scripts (install, profile gen, cron wire, etc.) |
| `examples/` | 9 scrum config templates with placeholders |

## Shared Skills

Every profile loads shared Hermes skills shipped with this repo:

| Skill | Purpose |
|-------|---------|
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

## What You Get

### 10 Department Agents

Each runs as an isolated Hermes Agent profile with:
- **SOUL.md** — persona definition with voice, boundaries, and domain knowledge
- **config.yaml** — model config (deepseek-v4-flash by default), gbrain MCP, Slack connection
- **Skills** — domain-specific + shared skills
- **Cron jobs** — 3-tier daily scrum + department-specific extras
- **gbrain source** — isolated knowledge store with federated read of `shared/`

### 54 Automated Cron Jobs

| Category | Jobs | Type |
|----------|------|------|
| Daily scrum (9 departments × 3 tiers) | 27 | 9 no_agent + 18 agent |
| Infrastructure (brain ingest, gmail, calendar, drive) | 8 | Mixed |
| Department-specific (pipeline, budget, leave, etc.) | 15 | Agent |
| Health & monitoring | 4 | no_agent |

### 25 Reusable Skills

Shipped in this repo, installable via Hermes skill tap:
```bash
hermes skills tap add limcheehow/shogun-os
hermes skills install shogun-os/company-workflow
```

### Complete Setup Tooling

| Script | What It Does |
|--------|-------------|
| `install.sh` | Install skills, scripts, templates, check gbrain version, deploy profiles |
| `generate-profile.py` | Generate a new Hermes profile with SOUL.md + config.yaml from template |
| `wire-crons.py` | Generate and apply cron jobs per profile type |
| `init-gbrain.sh` | Initialize gbrain with all 11 department sources |
| `verify-install.sh` | Full install verification with MCP connectivity probe |
| `backup-crons.py` | Export all cron jobs to portable JSON for migration |
| `restore-crons.py` | Restore cron jobs from backup |

## Troubleshooting

### Install fails: gbrain not found
```bash
bun install -g github:garrytan/gbrain
# Verify
gbrain --version  # should be v0.42.x+
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

## License

MIT. Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research and [GBrain](https://github.com/garrytan/gbrain) by Garry Tan / Y Combinator.