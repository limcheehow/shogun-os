# Company OS

> **Hermes Agent profile templates, recipes, and architecture for the AI-native company.**
>
> Every department gets its own AI agent with a distinct Samurai persona, its own gbrain source, and a shared infrastructure layer. One Slack bot per profile. One unified task system. One brain.

## Overview

Company OS is a reference architecture for running an entire organization through AI agents. Built on [Hermes Agent](https://hermes-agent.nousresearch.com) + [GBrain](https://github.com/garrytan/gbrain), it gives each department a dedicated AI operator with role-specific tools, memory, and autonomy.

```
┌──────────────────────────────────────────────────────────────┐
│                    Company OS Architecture                    │
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
│         └─────────┘  └──────────┘  └─────────┘              │
└──────────────────────────────────────────────────────────────┘
```

## Contents

| File | What It Covers |
|------|---------------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System design, gbrain sources, MCP wiring, model config |
| [`SETUP.md`](SETUP.md) | End-to-end setup playbook from zero to running profiles |
| [`PROFILE_CATALOG.md`](PROFILE_CATALOG.md) | All 10 department profiles with personas, sources, skills, crons |
| [`CRON_INVENTORY.md`](CRON_INVENTORY.md) | Every cron job across all profiles |
| [`RECIPE_INDEX.md`](RECIPE_INDEX.md) | All recipes with dependencies and setup order |
| `profile-templates/` | YAML config presets (base, coding) |
| `recipes/` | Self-contained integration recipes |
| `skills/` | Cross-department scrum workflow + other shared skills |
| `scripts/` | Utility tooling (profile switching, scrum DM sending) |
| `schema/` | Data schemas (task management) |

## Quick Start

```bash
# Prerequisites
which hermes        # Hermes Agent installed
which gbrain        # GBrain installed
gh auth status      # GitHub authenticated

# 1. Clone this repo
git clone https://github.com/limcheehow/company-os.git
cd company-os

# 2. Set up Google DWD (foundation for all Google integrations)
# See recipes/google-dwd.md

# 3. Create a profile
hermes profile create hr-manager
# Then apply the template from this repo

# 4. Set up gbrain source
gbrain init
gbrain init-source hr

# 5. Wire Slack bot
# Follow SETUP.md → Slack Bot Configuration
```

## Personas

Every profile embodies a **Samurai** persona — a character from Akira Kurosawa's *Seven Samurai* (plus extras), chosen for their domain:

| Profile | Persona | Role |
|---------|---------|------|
| HR | **Jinzai** (人材 — "Talent") | People operations, culture |
| Finance | **Koku** (石 — "Stone") | Financial stability |
| Projects | **Gorobei** (五郎兵衛 — "Strategist") | Project execution |
| Procurement | **Kura** (蔵 — "Vault") | Supply chain |
| Product | **Shi** (士 — "Samurai") | Product vision |
| CRM | **Kizuna** (絆 — "Bond") | Client relationships |
| Marketing | **Haiku** (俳句) | Brand & narrative |
| Compliance | **Kata** (型 — "Form") | Standards & audits |
| Customer Support | **Bōei** (防衛 — "Defense") | Client shield |
| Coding Agent | **Takumi** (匠 — "Artisan") | Engineering craft |

## Infrastructure

### Default Profile (Shared Infrastructure)

The `default` profile runs shared resource crons:

| Cron | Schedule | Purpose |
|------|----------|---------|
| Email Collector | Every 30 min | Deterministic Gmail → brain |
| Calendar Sync | Daily 6AM | Calendar events → brain pages |
| Drive Sync | Weekdays 12/16/20 | Google Docs → brain |
| Token Utilization | Weekly Monday 8AM | AI spend report |
| DWD Token Watchdog | Daily 6AM (optional) | Auth belt-and-suspenders |

### Recipes

Eight self-contained integration packages (gbrain recipe style):

| Recipe | Category | Depends On |
|--------|----------|-----------|
| `google-dwd` | auth | — |
| `token-watchdog` | auth | google-dwd |
| `email-to-brain` | ingest | google-dwd |
| `calendar-to-brain` | ingest | google-dwd |
| `drive-to-brain` | ingest | google-dwd |
| `token-utilization` | monitor | — |
| `jibble-time-tracking` | connector | — |
| `slides-deck-gen` | connector | google-dwd |

## Shared Skills

Every profile reaches into `skills/shared/` (symlinked):

| Skill | Purpose |
|-------|---------|
| `department-scrum` | Cross-department 3-tier scrum workflow (9am/11am/5pm) |
| `profile-enrichment` | Company/contact research |
| `staff-lookup` | Employee directory |
| `task-management` | Unified task schema |
| `brain-compliance` | Brain page validation |
| `slack-formatting` | Message formatting |

## Scrum Workflow

Every department (except Coding) runs a **3-tier daily scrum** using a single shared framework:

```
9:00 AM ── send-scrum-dms.py (no_agent script)
               → Reads scrum.yaml for team roster
               → Opens Slack DMs with each member
               → Saves state to scrum-states/{profile}/{date}.json

REALTIME ── Gateway agent (Option B, no daemon)
               → SOUL.md routes: scrum reply → save + post to channel
                              non-scrum → answer with domain knowledge

11:00 AM ── check-scrum-replies.py warn (LLM agent)
               → Cross-references replies against gbrain
               → Warns non-responders via Slack DM

5:00 PM  ── check-scrum-replies.py report (LLM agent)
               → Full compliance report
               → SMART quality gates per domain
               → Logs to gbrain _scrum/{profile}/{date}
```

Key design principles:
- **One script, all departments** — parameterized via per-profile `scrum.yaml`
- **Option B gateway** — no socket daemons, no polling
- **Holiday-aware** — KL public holidays via offline Hijri algorithm
- **Cross-ref against gbrain** — task IDs, domain terms matched per department

See `skills/shared/department-scrum/SKILL.md` for full documentation, cron templates, and migration path.

## Task Management

Unified task schema across all departments. Core fields: `title`, `status`, `priority`, `assignee`, `due_date`, `group`, `group_type`, `department`, `custom_fields`.

`group_type` varies by department:

| Profile | group_type | Example |
|---------|-----------|---------|
| Projects | project | "IOI Project" |
| Product | epic | "Dashboard v3" |
| Procurement | project | "IOI Project" |
| Customer Support | ticket | "TS-2026-001" |
| HR | initiative | "Q3 Hiring Drive" |
| Finance | initiative | "Annual Audit" |
| Marketing | campaign | "Edge AI Launch" |
| Compliance | audit | "ISO Recert" |
| Coding | epic | "Auth Refactor" |

See [`schema/task-management.md`](schema/task-management.md) for the full specification.