# Shogun OS — Hermes Skill Tap Manifest

This repository is a [Hermes Agent skill tap](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills#publishing-a-custom-skill-tap).
Add it as a custom skill source to install Shogun OS skills directly.

## Add as a Tap

```bash
hermes skills tap add limcheehow/shogun-os
```

## Install Skills

```bash
# Browse available skills
hermes skills search --source limcheehow/shogun-os

# Install specific skills
hermes skills install limcheehow/shogun-os/department-scrum
hermes skills install limcheehow/shogun-os/brain-ingest-pipeline
hermes skills install limcheehow/shogun-os/accounting-provider
```

## Skills Available

Approximate inventory: **~40+ installable skill packages** under `skills/` (78 `SKILL.md` files including nested manufacturing/retail/gbrain packs), plus **10 domain provider abstractions** under `recipes/`.

| Skill | Description |
|-------|-------------|
| `department-scrum` | Cross-department 3-tier daily scrum workflow (9am/11am/5pm) |
| `brain-ingest-pipeline` | Unified COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE data pipeline |
| `slack-formatting` | Format output for Slack — mrkdwn text and Block Kit JSON |
| `brain-compliance` | Standards and validation for Gbrain-compliant brain pages |
| `profile-enrichment` | Enrich company and contact profiles via web research + gbrain |
| `gbrain-operations` | GBrain operations: sync, embed, doctor, dream cycle, MCP setup |
| `lark-formatting` | Format messages for Lark (Feishu) — CardKit JSON and text formatting |
| `brain-first-lookup` | Mandatory brain-first lookup protocol |
| `brain-e2e-tests` | Brain compliance E2E testing suite |
| `brain-file-delivery` | Enforce file-attachment delivery for brain pages |
| `brain-link-campaign` | Reduce orphan pages, increase link coverage |
| `gbrain-capture` | Quick capture of thoughts and ideas to gbrain |
| `gbrain-query` | Three-layer gbrain query pipeline |
| `gbrain-think` | Multi-hop synthesis with cited answers |
| `gbrain-maintain` | Brain health checks, orphan detection, link campaigns |
| `gbrain-frontmatter-guard` | YAML frontmatter validation on every brain write |
| `gbrain-signal-detector` | Ambient signal capture for gbrain |
| `timeline-inject-v2` | gbrain-compatible timeline entry injection |
| `coding-workflow` | Master coding workflow with subagent delegation |
| `systematic-debugging` | 4-phase root cause debugging methodology |
| `writing-plans` | Implementation plan authoring |
| `plan` | Plan mode — write markdown plans without execution |
| `verify-first` | Behavioral overlay — verify before claiming |
| `search-router` | Intelligent search routing |
| `company-workflow` | Mandatory 6-gate workflow enforcement |
| `document-processing` | Extract text from PDFs, scans, and documents with OCR |
| `google-workspace` | Google Workspace API operations (Gmail, Calendar, Drive, Docs) |
| `lark-workspace` | Lark/Feishu API operations (Calendar, messaging) |
| `profile-management` | Manage Hermes profiles end-to-end — persona authoring, config, lifecycle |
| `time-tracking` | HR time tracking — Jibble, Kami, etc. via MCP provider abstraction (`tt_*`) |
| `accounting-provider` | Accounting — Bukku, QuickBooks, Xero via unified MCP bridge (`acct_*`) |
| `procurement-provider` | Procurement — PO, vendor, contract provider abstraction (`proc_*`) |
| `crm-provider` | CRM — contacts, deals, pipeline provider abstraction (`crm_*`) |
| `marketing-provider` | Marketing — campaigns, audience, analytics provider abstraction (`mkt_*`) |
| `compliance-provider` | Compliance — documents, e-sign, policy provider abstraction (`comp_*`) |
| `support-provider` | Support — tickets, SLA, knowledge base provider abstraction (`spt_*`) |
| `engineering-provider` | Engineering — repos, issues, PRs, CI provider abstraction (`eng_*`) |
| `projects-provider` | Project management — tasks, milestones, timeline provider abstraction (`proj_*`) |
| `product-provider` | Product management — ideas, roadmap, releases provider abstraction (`pd_*`) |

### Related CRM skills (Kizuna post-install)

| Skill | Description |
|-------|-------------|
| `customer-communication-onboarding` | Shared inbox onboarding (Respond.io or Chatwoot) after core install |
| `respondio-bridge` | Respond.io webhook → Hermes → reply / escalate |
| `chatwoot-bridge` | Chatwoot webhook → draft/auto-reply + SLA |

Industry packs (manufacturing, retail) and nested skills under `skills/crm/`, `skills/devops/`, etc. are also present in-repo; use `hermes skills search --source limcheehow/shogun-os` for the live tap listing.

## Web Portal (v3.10.0)

Not a Hermes skill package — install from the repo:

| Artifact | Path / command |
|----------|----------------|
| App | `shogun-web/server/` (FastAPI), `shogun-web/ui/` (React), `shogun-web/registry/` |
| Install | `./scripts/install-web.sh` |
| Verify | `./scripts/verify-web.sh` |
| Templates | `templates/web-portal/config.yaml`, `templates/web-portal/web.json` |
| Local URL | `http://127.0.0.1:8787` (default `SHOGUN_WEB_PORT`) |
| Public URL | `https://<subdomain>.shogun-os.ai` via central registry + Cloudflare Tunnel |

**What you get:** multi-tenant `*.shogun-os.ai` subdomain, login (OAuth + password), 4-step onboarding wizard, department dashboards (**Chat / Brain / Docs**), unified chat to each profile gateway.

**Default department → gateway ports** (must match running Hermes gateways):

| UI dept | Profile | Port |
|---------|---------|------|
| HR | `hr-manager` | 9101 |
| Finance | `finance-manager` | 9102 |
| Procurement | `procurement-manager` | 9103 |
| CRM | `crm-manager` | 9104 |
| Marketing | `marketing-manager` | 9105 |
| Compliance | `compliance-manager` | 9106 |
| Customer Support | `customer-support` | 9107 |
| Project | `project-manager` | 9108 |
| Product | `product-manager` | 9109 |
| Coding | `coding-agent` | 9110 |

Full profile matrix: [`PROFILE_CATALOG.md`](PROFILE_CATALOG.md). Recipe graph: [`RECIPE_INDEX.md`](RECIPE_INDEX.md).

## Repository Structure

```
skills/                         # Hermes skill tap packages (~40+ top-level entries)
├── department-scrum/
│   ├── SKILL.md
│   ├── references/
│   ├── templates/
│   └── scripts/
├── brain-ingest-pipeline/
│   ├── SKILL.md
│   └── scripts/
└── … (gbrain-*, provider-* via recipes, industry packs)

recipes/                        # 25 integration recipes + 10 domain abstractions
├── hr/time-tracking/           # tt_* CONTRACT + providers (replaces jibble-time-tracking)
├── accounting/                 # acct_* + bridge + Bukku/QBO/Xero
├── procurement/ crm/ marketing/ compliance/
├── support/ engineering/ projects/ product/
└── google-dwd.md, department-scrum.md, …

shogun-web/                     # NEW v3.10.0 — multi-tenant portal
├── server/                     # FastAPI backend
├── ui/                         # React SPA
└── registry/                   # Central subdomain router (Docker)

templates/web-portal/           # config.yaml + web.json
scripts/install-web.sh
scripts/verify-web.sh
```

## About

Shogun OS is a reference architecture for running an organization through Hermes Agent. Each department gets a dedicated AI agent with role-specific tools, memory, and autonomy — plus optional **web portal** chat/brain UI and **provider-abstracted** SaaS backends.

See the [full repo](https://github.com/limcheehow/shogun-os) for profiles, templates, install scripts, and documentation.

## Architecture

- [Provider Abstraction](docs/architecture/PROVIDER_ABSTRACTION.md) — Bring your own backends to agent profiles via standard MCP contracts
- [Creating Provider Abstractions](docs/recipes/creating-provider-abstractions.md) — CONTRACT + bridge + plugin lifecycle
- [Profile Catalog](PROFILE_CATALOG.md) — Personas, skills, gateway ports, web UI mapping
- [Recipe Index](RECIPE_INDEX.md) — Dependency graph and install order (including web portal)
