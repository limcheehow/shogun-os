# Recipe Index

Self-contained integration packages (gbrain recipe style). Each has YAML frontmatter with metadata and a full setup playbook.

**v3.9.0+** adds ten **provider abstraction** domains under `recipes/<domain>/` (CONTRACT + GENERIC_SKILL + providers/plugins/bridges).  
**v3.10.0** adds the **web portal** (`shogun-web/`, `scripts/install-web.sh`, `templates/web-portal/`) — not a classic recipe file, but listed under Installation Order and Infra.

## Dependency Graph

```
google-dwd (auth)
  ├── token-watchdog (optional belt-and-suspenders)
  ├── brain-ingest-pipeline (replaces old email/calendar collectors)
  ├── drive-to-brain
  └── slides-deck-gen

token-utilization (standalone — no deps)

department-scrum (standalone — no deps, requires Hermes + Slack)
  └── scrum-production-hardening (reference)

gateway-systemd-management (infra)
  └── model-health-auto-fallback (infra)

session-db-postgres (infra — multi-profile)

brain-maintenance (ops — needs gbrain)
profile-provisioning (ops — needs Hermes)
cron-management (ops — needs Hermes)

# ── Provider abstractions (v3.9.0) — independent of Google DWD ──
# Pattern: CONTRACT.md + GENERIC_SKILL.md + providers/ + plugins/ + bridge
# Load via importlib; configure with env vars; optional OAuth cache
#   ~/.hermes/mcp-tokens/<domain>-<provider>.json
#
hr/time-tracking   (tt_*)     ← supersedes jibble-time-tracking
accounting         (acct_*)   ← Bukku / QuickBooks / Xero (full bridge)
procurement        (proc_*)
crm                (crm_*)
marketing          (mkt_*)
compliance         (comp_*)
support            (spt_*)
engineering        (eng_*)
projects           (proj_*)
product            (pd_*)

jibble-time-tracking  ⚠️ DEPRECATED → use hr/time-tracking

# ── Web portal (v3.10.0) ──
install-web.sh / verify-web.sh / shogun-web/{server,ui,registry}
  depends on: deployed profiles + free gateway ports (9101–9110 defaults)
  registry optional: Cloudflare Tunnel + Docker registry service
```

## Recipe Details

### 1. `google-dwd` — Auth Foundation

| Field | Value |
|-------|-------|
| Category | auth |
| Setup time | 20 min |
| Cost | $0 |
| Depends on | — |
| Health check | Token generation via `creds.refresh()` |

Sets up Google Domain-Wide Delegation — a service account impersonating a user in your Google Workspace domain. Every Google integration depends on this.

### 2. `token-watchdog` — Optional Auth Belt-and-Suspenders

| Field | Value |
|-------|-------|
| Category | auth |
| Setup time | 5 min |
| Cost | $0 |
| Depends on | google-dwd |
| Cron | Daily 6AM, no_agent, default profile |

Proactively refreshes DWD credentials. Only needed if scripts cache raw access tokens. If all scripts use `google-auth` properly (which the recipes do), skip this.

### 3. `brain-ingest-pipeline` — Unified Brain Ingest Pipeline

| Field | Value |
|-------|-------|
| Category | ingest |
| Setup time | 10 min |
| Cost | $0 |
| Depends on | google-dwd (for SA-DWD key) |
| Crons | 3: gmail triage (*/30min, no_agent) + calendar collect (daily 6AM, no_agent) + pipeline agent (9/13/17 weekdays) |

Unified **COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE** flow for all data sources. Replaces the old per-source email and calendar collectors with a single 5-phase pipeline using SA-DWD, batch rotation, and gbrain linking.

See `skills/brain-ingest-pipeline/SKILL.md` for full docs.

**Supersedes:** `email-to-brain` and `calendar-to-brain` (removed — use this instead).

### 4. `drive-to-brain` — Google Drive → Knowledge Base

| Field | Value |
|-------|-------|
| Category | ingest |
| Setup time | 20 min |
| Cost | $0 |
| Depends on | google-dwd |
| Crons | Sync 12/16/20 weekdays (no_agent) + Enrichment 13/17 (agent) |

Monitors Drive folders for documents (meeting notes, proposals, reports), syncs to brain pages with entity extraction.

### 5. `token-utilization` — AI Spend Monitoring

| Field | Value |
|-------|-------|
| Category | monitor |
| Setup time | 5 min |
| Cost | $0 |
| Depends on | — |
| Cron | Weekly Monday 8AM, no_agent, default profile |

Runs `tokscale monthly --json` and generates a formatted markdown report showing cost, tokens, cache efficiency per model per month.

### 6. `jibble-time-tracking` — HR Time Tracking

| Field | Value |
|-------|-------|
| Category | connector |
| Setup time | 15 min |
| Cost | $0 |
| Depends on | — |
| Crons | Daily attendance 9:30AM + Weekly timesheet Mon 10AM (hr-manager) |
| Status | **DEPRECATED** |

⚠️ **DEPRECATED — Superseded by `recipes/hr/time-tracking/`.** The new provider abstraction covers Jibble and any other provider through the standard MCP contract (`tt_*` tools). See `recipes/hr/time-tracking/` and `providers/jibble.md` for the current implementation. Do not install this standalone recipe on new deployments.

### 7. `slides-deck-gen` — Google Slides Integration

| Field | Value |
|-------|-------|
| Category | connector |
| Setup time | 15 min |
| Cost | $0 |
| Depends on | google-dwd |
| Cron | (none — ad-hoc) |

Slides API skill for creating decks, replacing placeholder text, adding slides, exporting as PDF. Used by marketing-manager (Haiku) for client decks.

### 8. `department-scrum` — Cross-Department Scrum Workflow

| Field | Value |
|-------|-------|
| Category | workflow |
| Setup time | 15 min per profile |
| Cost | $0 |
| Depends on | — (requires Hermes Agent + Slack bot per profile) |
| Crons | 3 per profile: 9am (no_agent) + 11am (agent) + 5pm (agent) |

Unified 3-tier daily scrum for ANY department profile. One generic script (`send-scrum-dms.py` + `check-scrum-replies.py`), per-profile config (`scrum.yaml`). Includes Option B gateway DM handling, SMART quality gates, gbrain cross-ref, and KL holiday gate.

**v3.0.0**: Now includes 15 production-hardened pitfalls in `references/production-pitfalls.md`.

See `skills/department-scrum/SKILL.md` for full docs.

### 9. `gateway-systemd-management` — Gateway Lifecycle Management

| Field | Value |
|-------|-------|
| Category | infra |
| Setup time | 15 min |
| Cost | $0 |
| Depends on | — |
| Crons | Gateway signal monitor (*/2min, no_agent) + Model health check (*/5min, no_agent) |

systemd template units for per-profile gateway management. Includes `hermes-gateway@.service` template, `restart-profile-gateway.sh` (auto-profile detection via symlinks), watchdog with exponential backoff, dead-PTY detection, orphaned process cleanup, and API key corruption check.

Align gateway listen ports with the web portal map (**9101–9110** defaults in `templates/web-portal/`).

### 10. `model-health-auto-fallback` — Provider Auto-Failover

| Field | Value |
|-------|-------|
| Category | infra |
| Setup time | 10 min |
| Cost | $0 |
| Depends on | — |
| Cron | Every 5 min, no_agent, default profile |

Tests primary **LLM** provider every 5 minutes. Auto-switches to backup on failure, switches back when primary recovers. Config-driven — reads provider settings from `config.yaml`. (Distinct from domain SaaS “provider abstractions” below.)

### 11. `brain-maintenance` — Brain Health Maintenance

| Field | Value |
|-------|-------|
| Category | ops |
| Setup time | 10 min |
| Cost | $0 |
| Depends on | gbrain |
| Crons | Health check (daily 9AM) + Auto-link (daily 2AM) + Dream cycle (daily 2AM) |

Automated brain health: `gbrain doctor`, orphan detection, link campaigns, compliance validation, and dream cycle scheduling.

### 12. `profile-provisioning` — Profile Creation & Management

| Field | Value |
|-------|-------|
| Category | ops |
| Setup time | 5 min per profile |
| Cost | $0 |
| Depends on | Hermes Agent |
| Cron | (none — ad-hoc) |

Profile creation patterns: SOUL.md authoring with workflow enforcement snippet, config.yaml from templates, systemd enable + start, skill installation via symlink. `generate-profile.py` also writes `.gateway-port` and attaches the domain provider skill for each profile type.

### 13. `cron-management` — Cron Job Lifecycle

| Field | Value |
|-------|-------|
| Category | ops |
| Setup time | 5 min |
| Cost | $0 |
| Depends on | Hermes Agent |
| Cron | (none — uses backup-crons.py + restore-crons.py) |

Cron job creation patterns, backup to portable JSON, restore from JSON, migration across machines.

### 14. `session-db-postgres` — Shared Postgres Session DB

| Field | Value |
|-------|-------|
| Category | infra |
| Setup time | 20 min |
| Cost | $0 |
| Depends on | PostgreSQL |
| Cron | Health check (daily 7AM, no_agent) |

Migrate from per-profile SQLite to shared Postgres for multi-profile deployments. Eliminates SQLite lock contention. Includes `session-postgres` plugin config and health check script.

### 15. `scrum-production-hardening` — Scrum Production Pitfalls

| Field | Value |
|-------|-------|
| Category | workflow |
| Setup time | 0 min (read-only reference) |
| Cost | $0 |
| Depends on | department-scrum |
| Cron | (none — reference doc) |

All 15 production pitfalls from running department-scrum in production. Read this before deploying scrum for the first time. See `recipes/scrum-production-hardening.md` and `skills/department-scrum/references/production-pitfalls.md`.

---

## Provider Abstraction Recipes (v3.9.0)

Shared pattern for every domain:

| Piece | Purpose |
|-------|---------|
| `CONTRACT.md` | Canonical MCP tool names + schemas (P0 ~11 tools) |
| `GENERIC_SKILL.md` | Agent skill installed into the owning profile |
| `providers/*.md` | Vendor-specific setup and env vars |
| `plugins/` | Python provider implementations |
| `bridges/*-bridge.py` | Unified MCP bridge; loads plugin via `importlib` |

Guide: [`docs/recipes/creating-provider-abstractions.md`](docs/recipes/creating-provider-abstractions.md)

### 16. `hr/time-tracking` — HR Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/hr/time-tracking/` |
| Category | connector / provider-abstraction |
| Setup time | 10 min |
| Cost | $0 |
| Depends on | — |
| Profile | `hr-manager` (gateway **9101**) |
| Tools | `tt_*` |

Generic MCP contract for time-tracking providers (Jibble, Kami, etc.). Universal interface for attendance, timesheets, and clock-in status. **Replaces** standalone `jibble-time-tracking`.

### 17. `accounting` — Accounting Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/accounting/` |
| Category | connector / provider-abstraction |
| Setup time | 10–20 min |
| Cost | $0 |
| Depends on | — |
| Profile | `finance-manager` (gateway **9102**) |
| Tools | `acct_*` (11 P0) |
| Providers | Bukku, QuickBooks, Xero |
| Bridge | `acct-bridge.py` + shared `oauth-helper.py` |

Unified bridge loads provider plugins dynamically. Covers sales invoices, purchase bills, contacts, products, P&L, balance sheet, and aging reports.

### 18. `procurement` — Procurement Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/procurement/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `procurement-manager` (gateway **9103**) |
| Tools | `proc_*` |

Standard interface for purchase orders, vendor management, and contract lifecycle. Scaffold: CONTRACT + GENERIC_SKILL + providers/plugins slots.

### 19. `crm` — CRM Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/crm/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `crm-manager` (gateway **9104**) |
| Tools | `crm_*` |

Standard interface for contacts, deals/pipeline, and activities. Complements Kizuna skills (`customer-communication-onboarding`, Respond.io / Chatwoot bridges).

### 20. `marketing` — Marketing Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/marketing/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `marketing-manager` (gateway **9105**) |
| Tools | `mkt_*` |

Standard interface for campaigns, audience lists, analytics, and social posts.

### 21. `compliance` — Compliance Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/compliance/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `compliance-manager` (gateway **9106**) |
| Tools | `comp_*` |

Standard interface for e-signatures, policy management, and audit trails.

### 22. `support` — Customer Support Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/support/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `customer-support` (gateway **9107**) |
| Tools | `spt_*` |

Standard interface for tickets, SLAs, and knowledge base.

### 23. `engineering` — Engineering Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/engineering/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `coding-agent` (gateway **9110**) |
| Tools | `eng_*` |

Standard interface for repos, issues, PRs, CI/CD, and deployments.

### 24. `projects` — Project Management Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/projects/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `project-manager` (gateway **9108**) |
| Tools | `proj_*` |

Standard interface for projects, tasks, milestones, and timelines.

### 25. `product` — Product Management Provider Abstraction

| Field | Value |
|-------|-------|
| Path | `recipes/product/` |
| Category | connector / provider-abstraction |
| Setup time | 5 min (+ provider plugin) |
| Cost | $0 |
| Depends on | — |
| Profile | `product-manager` (gateway **9109**) |
| Tools | `pd_*` |

Standard interface for ideas, roadmaps, releases, and feedback.

---

### 26. Web portal package (v3.10.0) — not a `.md` recipe

| Field | Value |
|-------|-------|
| Paths | `shogun-web/{server,ui,registry}/`, `scripts/install-web.sh`, `scripts/verify-web.sh`, `templates/web-portal/` |
| Category | infra / portal |
| Setup time | ~10 min (+ Cloudflare/registry for public subdomain) |
| Cost | $0 (infra hosting optional) |
| Depends on | Hermes profiles + gateway ports; optional Docker registry + Cloudflare |
| Default local port | **8787** (`SHOGUN_WEB_PORT`) |

Multi-tenant FastAPI + React portal: onboarding wizard, department dashboards (Chat / Brain / Docs), OAuth + password auth, central registry for `*.shogun-os.ai` routing. Department chat targets the gateway ports above.

---

### Guide: Creating Provider Abstractions

See [`docs/recipes/creating-provider-abstractions.md`](docs/recipes/creating-provider-abstractions.md) for a step-by-step guide on:

- How to create a new domain abstraction (CONTRACT + GENERIC_SKILL + bridge)
- How to wire multiple connectors into a single department profile
- How to add a new provider to an existing domain
- Full lifecycle checklist for adding abstractions to the repo
- Pitfalls (importlib paths, env naming, OAuth token cache layout)

## Installation Order

```
 1. google-dwd                   # Foundation — everything Google needs auth
 2. token-utilization            # Standalone — can do anytime
 3. token-watchdog               # Optional — only if caching tokens
 4. brain-ingest-pipeline        # Requires DWD — replaces old email/calendar collectors
 5. drive-to-brain               # Requires DWD
 6. slides-deck-gen              # Requires DWD — for marketing-manager
 7. department-scrum             # Standalone — after profile basics
 8. gateway-systemd-management   # Infra — after profiles exist (align ports 9101–9110)
 9. model-health-auto-fallback   # Infra — after gateway is running
10. brain-maintenance            # Ops — after brain has content
11. profile-provisioning         # Ops — reference for adding new profiles
12. cron-management              # Ops — backup/restore
13. session-db-postgres          # Infra — multi-profile production
14. scrum-production-hardening   # Reference — before going live with scrum
15. hr/time-tracking             # HR provider abstraction (NOT jibble-time-tracking)
16. accounting                   # Finance — acct_* + Bukku/QBO/Xero bridge
17. procurement                  # proc_*
18. crm                          # crm_*
19. marketing                    # mkt_*
20. compliance                   # comp_*
21. support                      # spt_*
22. engineering                  # eng_*
23. projects                     # proj_*
24. product                      # pd_*
25. web portal                   # install-web.sh + verify-web.sh (+ registry/tunnel for public URL)

# Deprecated — skip on new installs:
#    jibble-time-tracking        → use hr/time-tracking instead
```

### Suggested pairing with profiles

| After profile | Install provider recipe |
|---------------|-------------------------|
| `hr-manager` | `hr/time-tracking` |
| `finance-manager` | `accounting` |
| `procurement-manager` | `procurement` |
| `crm-manager` | `crm` (+ optional CC onboarding skills) |
| `marketing-manager` | `marketing` + `slides-deck-gen` |
| `compliance-manager` | `compliance` |
| `customer-support` | `support` |
| `coding-agent` | `engineering` |
| `project-manager` | `projects` |
| `product-manager` | `product` |
| all enabled depts | **web portal** (department cards + chat) |
