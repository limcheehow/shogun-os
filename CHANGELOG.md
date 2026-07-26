# Changelog

## [3.13.0] — 2026-07-26

### Profile Dashboards — CRM CEO dashboard in Shogun web portal

Replaces the "Reports" placeholder tab with a fully functional "Dashboard" tab that
shows profile-specific operational dashboards, starting with CRM.

**Backend:**
- New shared gbrain HTTP client (`gbrain_client.py`) — fetch pages, search, single page
- New `dashboard.py` FastAPI router with CEO stats aggregation (Python port of the
  CRM Next.js API route — full 348-line aggregation: ownerMap, stageMap, partnerMap,
  productMap, monthly trends, at-risk tracking, top deals)
- All dashboard data sourced from gbrain MCP (local Postgres) — no Supabase dependency

**Frontend:**
- Recharts v3.10.1 as the standard charting library
- Shared chart wrappers (BarChart, LineChart, PieChart, FunnelChart) enforcing
  Shogun design tokens + empty-state handling
- DashboardViewer generic wrapper + DashboardSubNav pill navigation
- CRM dashboard with 5 sub-tabs: Sales Booking, Pipeline & Forecast,
  Partner Performance, Manager Performance, Deals Deep-Dive
- Manager drill-down modal overlay with per-owner KPIs

**Data flow:**
```
SPA → /api/departments/{name}/dashboard/ceo-stats
    → FastAPI → gbrain MCP (port 7432) → local Postgres
    → Aggregated JSON → Recharts in sub-tabs
```

## [3.12.3] — 2026-07-26

### Fix: URL claim is install-time, not web UX (chicken-and-egg fix)

The "Go live" step in web onboarding was wrong — you can't claim a URL from a web portal that
doesn't have a URL yet. Redesigned:
- **install-web.sh** is the canonical URL claim path (bootstrap + register, already worked)
- **Web onboarding** step 4 is now "Review" — shows the URL that was claimed during install
- **Dashboard** has a fallback "Claim URL" button if registry was skipped during install
- Server `onboarding/complete` no longer attempts auto-go-live

## [3.12.2] — 2026-07-26
## [3.12.1] — 2026-07-26

### Web portal product contract

- **One random URL per company** assigned by central registry + **our** Cloudflare (customers never need a CF account or subdomain choice).
- **One dashboard** for all department agents (not per-department portals).
- `install-web.sh` v0.2: no subdomain prompt; register payload matches registry schema; persists assigned `public_url` + tunnel token.
- Registry: `ALLOW_PREFERRED_SUBDOMAIN=false` by default; auto tunnel when provisioning enabled; tunnel targets `127.0.0.1:{port}` on tenant.
- Docs: `docs/architecture/WEB_PORTAL.md`, `docs/ops/cloudflare-registry-setup.md`.

## [3.12.0] — 2026-07-26

### Shogunify — agent skillify for Shogun OS

Structured, profile-aware questionnaire so agents can add skills, connectors, workflows, and department profiles correctly (Hermes path rules + gbrain compliance).

- **New skill: `skills/shogunify/`** — slash command **`/shogunify`** (Hermes auto-registers skill names as slash commands on CLI + messaging gateways).
- **Questionnaires:** integration/connector, skill, workflow/cron, new department profile (`references/questionnaire-*.md`).
- **Path map:** `references/path-map.md` — default vs named-profile skill/cron/env/MCP destinations.
- **Templates:** skill SKILL.md, CONTRACT, GENERIC_SKILL, provider doc stubs.
- **`scripts/install-to-profiles.py`:** symlink or copy a skill into `~/.hermes/skills/` and every `~/.hermes/profiles/*/skills/`.
- **`scripts/e2e_test_shogunify.py`:** E2E — install, disposable `test-shogunify` profile, demo skill + connector scaffold, slash registration, path isolation.
- **Wiring:** `generate-profile.py` `SHARED_PROFILE_SKILLS` always includes `shogunify`; `install.sh` profile required skills; `verify-install.sh` skill check; `HUB.md` + `RECIPE_INDEX.md`.
- **Docs:** `docs/recipes/shogunify.md`, README What's New + Shared Skills, `docs/README.md`, `AGENTS.md` common task.

## [3.11.0] — 2026-07-26

### GBrain Production Integration

Full upgrade of the knowledge layer from ad-hoc per-profile stdio to a zero-cost, multi-transport production deployment.

- **Local embeddings:** Switched from OpenAI `text-embedding-3-small` (1536d, paid) to Ollama `nomic-embed-text` (768d, local inference, $0 cost). Added `scripts/init-gbrain.sh` Ollama check + install step.
- **Local PostgreSQL auto-install:** Script now auto-installs `postgresql-16` + `postgresql-contrib-16` if missing, creates `gbrain` user + database, and enables pgvector extension.
- **New: `shogun-enterprise` schema pack** — 30+ department-specific page types (staff, leave-request, candidate, budget, expense, invoice, milestone, ticket, vendor, purchase-order, contract, prd, roadmap, release, deal, contact, company, campaign, content, event, audit, control, risk, adr, codebase, deployment, kb-article, customer) with typed link verbs and frontmatter link extraction.
- **Dual MCP transport:** stdio for 10 Hermes Agent profiles + HTTP server on port 3100 for web portal access.
- **Nightly dream cycle:** `gbrain-dream-cron.sh` runs consolidate + synthesize + patterns phases at 2:00 AM daily.
- **pg_dump backups:** `gbrain-backup.sh` runs nightly at 2:30 AM, creates timestamped `.sql.gz` backups in `~/.gbrain/backups/`.
- **PGLite migration script:** `gbrain-migrate-pglite-to-postgres.sh` for users migrating from the old PGLite-based gbrain setup.
- **Updated: `ARCHITECTURE.md`** — Layer 2 section rewritten to reflect local PG16, Ollama embeddings, shogun-enterprise schema pack, dual MCP transport, and nightly maintenance schedule.
- **Updated: `scripts/init-gbrain.sh`** — v1.2.0 now includes Postgres auto-install, pgvector enable, and Ollama provisioning.
- **Updated: `scripts/install.sh`** — Bumps to v3.11.0 with gbrain production integration checks.
- **Updated: `scripts/verify-install.sh`** — Adds gbrain production transport, backup, and dream cycle verification.

## [3.9.0] — 2026-07-25

### Provider Abstraction Architecture (All 10 Domains)

- **New: Accounting provider abstraction** (`recipes/accounting/`) — Bukku, QuickBooks, Xero with unified MCP bridge (`acct-bridge.py`) that loads provider plugins dynamically. Includes 11 P0 `acct_*` tools, shared OAuth2 helper, and full provider setup docs.
- **New: 8 domain abstractions scaffolded** — Procurement (`proc_*`), CRM (`crm_*`), Marketing (`mkt_*`), Compliance (`comp_*`), Support (`spt_*`), Engineering (`eng_*`), Projects (`proj_*`), Product (`pd_*`). Each with CONTRACT.md + GENERIC_SKILL.md ready for provider plugins.
- **Refactored: Time-tracking** — Moved from `recipes/time-tracking/` to `recipes/hr/time-tracking/` under the HR domain. Added `providers/jibble.md` provider doc.
- **New: Creating Provider Abstractions guide** (`docs/recipes/creating-provider-abstractions.md`) — 500+ line step-by-step guide covering CONTRACT creation, bridge strategies, multi-connector profiles, lifecycle checklist, and 8 documented pitfalls.
- **Updated: PROFILE_CATALOG.md** — All 10 profiles now list their domain provider abstraction skills.
- **Updated: CRON_INVENTORY.md** — Finance crons tagged as using `acct_*` tools; HR crons renamed to provider-agnostic names.
- **Updated: RECIPE_INDEX.md** — All 25 recipes documented including installation order.
- **Updated: scripts/generate-profile.py** — All 8 profile types now include their domain provider abstraction skill.
- **Updated: scripts/install.sh** — Installs all 10 provider abstraction directories.
- **Updated: scripts/verify-install.sh** — Checks all 10 provider abstractions exist.
- **Updated: docs/architecture/PROVIDER_ABSTRACTION.md** — Full accounting contract table added, references to new guide.

## [3.8.2] — 2026-07-24

### GBrain Model Tier Inheritance

- **`scripts/init-gbrain.sh`** — now reads the user's Hermes default model and sets gbrain `models.tier.{reasoning,utility,subagent}` to match, instead of using gbrain's built-in defaults (`anthropic:claude-sonnet-4-6`) which consume a separate Anthropic API key.
- Provider resolution: if the Hermes provider is a known gbrain provider (`openrouter`, `anthropic`, `openai`, `google`), passes it through. If the provider is `custom` (DashScope etc.), falls back to the first fallback provider's model. If already custom-configured, leaves it untouched.
- Python interpreter resolver added to `init-gbrain.sh` for Windows compatibility.
- Bumped to v1.1.0.

## [3.8.1] — 2026-07-24

### Merge: Windows/Hermes/GBrain v0.42 Compatibility + Verification Suite

- **Profile generation:** model inheritance from active default, Windows symlink fallback, `.env` merge on `--force`, `gbrain serve` MCP command, project-manager/Gorobei type added
- **GBrain init:** v0.42 git repo compat (tracked README.md), JSON source detection, federation persistence via CLI
- **Cron wiring:** profile-scoped commands (`hermes -p <profile> cron create`), non-zero exit on failure, path resolution
- **Verification:** fixed fatal errors, Python interpreter resolver, Windows path normalization, GBrain MCP test
- **Installer:** proper profile existence check, deploy status tracking
- **15 new tests** covering Windows generation, federation, profile-scoped crons

## [3.8.0] — 2026-07-24

### Customer Communication Platform — Kizuna (CRM) Post-Install

Three new CRM skills for setting up a shared customer inbox (IG, FB, WhatsApp, Website) via Respond.io or Chatwoot:

#### New: `customer-communication-onboarding`
- Kizuna-specific onboarding wizard that runs *after* core Shogun OS install
- 8-step wizard with two branches: **[a] Respond.io** (SaaS) or **[b] Chatwoot** (self-hosted)
- Branch A: API key capture → channel inventory → webhook setup → template scan → assignment model
- Branch B: Docker deploy → inbox creation → agent accounts → webhook wiring → assignment model
- Scripts: `create-chatwoot-inboxes.py`, `create-chatwoot-agents.py`, `create-channel-pages.py`
- Templates: Docker Compose + `.env.example` for Chatwoot deployment
- Trigger: `hermes -p kizuna -q 'cc setup'`

#### New: `respondio-bridge`
- Runtime integration: Respond.io webhook → Hermes processing → auto-reply or escalate
- `sync-contact.py`: Respond.io contacts → brain people pages
- `send-template.py`: Fixed templates from brain → Respond.io messages
- `check-sla.py`: First response time SLA report (runnable on cron)
- API reference docs

#### New: `chatwoot-bridge`
- Runtime integration: Chatwoot webhook → Hermes processing → draft/auto-reply
- `sync-contact.py`: Chatwoot contacts → brain people pages
- `log-conversation.py`: Chatwoot conversations → brain timeline entries
- `check-sla.py`: Response time SLA report (runnable on cron)
- Supports 3 assignment models: Hermes-first, Human-first, Co-pilot (private notes)
- API reference docs

#### Changes to existing files
- **`scripts/install.sh`** — bumped to v3.8.0
- **`scripts/verify-install.sh`** — added checks for 3 new skills
- **`skills/shogun/shogun-installer/SKILL.md`** — Step 9 summary now points Kizuna users to post-install CC setup

Full docs: `skills/crm/customer-communication-onboarding/SKILL.md`

## [3.7.0] — 2026-07-23

### Documentation & CLI Fixes

Major documentation update to catch up with the following fixes:

#### Microsoft 365 Integration

- **New skill at `skills/devops/microsoft-integration/`** — Graph API client (`msft_api.py`) for mail, calendar, OneDrive, and directory operations via OAuth 2.0 client credentials
- **`docs/README.md` updated** — Added Microsoft 365 Integration to quick reference
- **`CHANGELOG.md`** — This entry

#### Removed Env Var References from Profile Templates

- **`INSTALL_FOR_AGENTS.md`** — Removed `DASHSCOPE_API_KEY` and `OPENROUTER_API_KEY` from per-profile API keys (Phase 2 table, .env example, Phase 5.1). Profiles use the default model config — no per-profile API keys needed.
- **`skills/gbrain-operations/SKILL.md`** — Removed `OPENROUTER_API_KEY` from prerequisites table; clarified it belongs in the main `~/.hermes/.env`
- **`skills/gbrain-operations/SKILL.md`** — Removed `${GBRAIN_SOURCE}` and `${GBRAIN_FEDERATED_READ}` env vars from gbrain MCP config example (auto-configured by init-gbrain.sh)

#### Fixed gbrain CLI Compatibility

- **`INSTALL_FOR_AGENTS.md` (Phase 3)** — `gbrain list-sources` → `gbrain sources list`
- **`docs/deployment-readiness-review.md`** — `gbrain init-source` → `gbrain sources add`
- **`skills/gbrain-operations/SKILL.md`** — `gbrain serve` → `gbrain mcp` (command + args + troubleshooting references)

#### Fixed hermes cron create CLI Syntax

- **`--schedule` removed** — Schedule is now a POSITIONAL argument (first arg after `cron create`). Updated across all recipes and skills:
  - `recipes/brain-maintenance.md` (4 crons)
  - `recipes/drive-to-brain.md` (2 crons)
  - `recipes/jibble-time-tracking.md` (2 crons)
  - `recipes/profile-provisioning.md` (1 cron)
  - `recipes/time-tracking/GENERIC_SKILL.md` (1 cron)
  - `skills/gbrain-operations/SKILL.md` (3 crons)
  - `skills/google-workspace/references/rclone-sync-cron.md`
  - `skills/google-workspace/references/google-token-watchdog.md`
  - `skills/google-workspace/references/google-dwd-setup.md`
- **`--skills` → `--skill`** — Updated across all recipes and skills

#### Fixed install.sh --deploy Syntax

- **`--deploy all` → `--deploy`** — `--deploy` is boolean, `--deploy all` is invalid. Updated in:
  - `INSTALL_FOR_AGENTS.md` (Phase 4)
  - `profiles-general.md`
  - `docs/deployment-readiness-review.md` (closure criteria)

#### Documentation

- **`docs/deployment-readiness-review.md`** — Updated G1 phantom skills entry to reflect v2.3.0 fix; updated 0.1 execution plan item to checked status
- **`AGENTS.md`** — Updated `gbrain init-source` → `gbrain sources add` in common tasks

---

## [3.0.0] — 2026-07-11

### Production Hardening + Workflow Enforcement + Expanded Skill Catalog

Major update driven by 2 weeks of production deployment. Adds 18 new shared skills, 7 new recipes, 12 new scripts, production-hardened scrum v3.0.0, and mandatory workflow enforcement for all profiles.

#### Scrum v3.0.0 — Production Hardened

- **15 production pitfalls documented** in `references/production-pitfalls.md` — lessons from running department-scrum in production. Covers: gateway WebSocket crash loops, LLM timeout cascades, cron batch-fire race conditions, HERMES_HOME path issues, JSON extraction from CLI, brain tool selection, listener crash vs LLM outage, save-state ordering, recovery sweep date filtering, compliance_state values, pass-through post failures, CLI syntax verification, Block Kit format, duplicate systemd services, cron silent skips.
- **`send-scrum-dms.py` updated**: State saved BEFORE sending DMs (race condition fix), `posted_to_channel` and `submission_state` fields added to state schema, state saved after each DM for crash resilience.
- **Migration path updated**: Phases 5-7 marked as ✅ Deployed, Phase 10 (pitfalls merge) added.
- **Skill version bumped** to 3.0.0 with `production-hardened` tag.

#### New: Workflow Enforcement (company-workflow skill)

- **`skills/company-workflow/`** — Mandatory 6-gate workflow for any feature/bug/change request: Triage → RCA → Brainstorm → Plan → TDD → E2E.
- **`generate-profile.py` updated**: Every generated SOUL.md now includes a `## Workflow Enforcement (MANDATORY)` section with the gate sequence and trigger phrases.
- **Every profile type** in `PROFILE_META` now includes `company-workflow` in its skills list.
- **`references/soul-snippet-workflow.md`** — Standalone snippet for manual SOUL.md updates.

#### New: 18 Shared Skills

Brain operations (11, already generic — copied as-is):
- `brain-first-lookup`, `gbrain-capture`, `gbrain-query`, `gbrain-think`, `gbrain-maintain`, `gbrain-frontmatter-guard`, `brain-link-campaign`, `brain-file-delivery`, `brain-e2e-tests`, `gbrain-signal-detector`, `timeline-inject-v2`

Development & operations (7, generalized from production):
- `coding-workflow`, `systematic-debugging`, `writing-plans`, `plan`, `verify-first`, `search-router`, `company-workflow`

#### New: 7 Recipes

- `recipes/gateway-systemd-management.md` — systemd template units, restart script, watchdog, crash recovery
- `recipes/model-health-auto-fallback.md` — Provider health check cron + auto-switchover
- `recipes/brain-maintenance.md` — Health checks, orphan detection, link campaigns, compliance validation
- `recipes/profile-provisioning.md` — Profile creation, SOUL.md authoring, systemd enable
- `recipes/cron-management.md` — Cron job lifecycle, backup/restore, migration
- `recipes/session-db-postgres.md` — Migrate from SQLite to shared Postgres
- `recipes/scrum-production-hardening.md` — All 15 production pitfalls as a standalone reference

#### New: 12 Scripts

- `restart-profile-gateway.sh` — Unified gateway restart with auto-profile detection via symlinks
- `gateway-signal-monitor.sh` — Monitor gateway PID changes + SIGTERM events
- `model-health-check.sh` — Provider health check + auto-switchover (config-driven)
- `dashboard-watchdog.sh` — Site health monitoring (config-driven URLs)
- `sites-startup.sh` — @reboot site startup (config-driven site list)
- `hermes-backup.sh` — DB backup to local + optional cloud storage
- `cloudflared-tunnel-watchdog.sh` — Tunnel health check
- `session-db-health-check.sh` — Postgres/SQLite health check
- `daily-disk-cleanup.py` — Disk space cleanup (config-driven paths)
- `daily-token-cost.py` — AI spend tracking via tokscale
- `generate-org-chart.py` — Org chart from brain data
- `gateway-scheduled-restart.sh` — Scheduled gateway restart

#### Template Generalization

- **`base-config.yaml`**: Hardcoded provider URLs/keys replaced with `${PLACEHOLDER}` variables (`PRIMARY_PROVIDER_BASE_URL`, `PRIMARY_PROVIDER_API_KEY`, `BACKUP_PROVIDER_NAME`, `BACKUP_PROVIDER_MODEL`, `AUXILIARY_MODEL`)
- **`coding-config.yaml`**: Hardcoded Anthropic/Primary Provider references replaced with `${CODING_MODEL}`, `${CODING_PROVIDER}`. Removed hardcoded `stock-scanner` MCP (company-specific).
- **All scripts**: Company names, product names, Slack channel IDs, person names, and hardcoded ports replaced with config-driven placeholders.

#### Excluded (env-specific, not in repo)

- SQLite WAL recovery scripts (`enforce-wal.sh`, `wsl-drop-caches.sh`, `cache-dropper.sh`, `memory-watchdog.sh`) — WSL/SQLite environment-specific
- All company-specific skills (`your-company-*`, `your-company-dwd`)
- Company-specific scrum scripts (`product-scrum-*.py`, `project-scrum-*.py`) — replaced by generic `send-scrum-dms.py` / `check-scrum-replies.py`

---

## [2.3.0] — 2026-06-25

### Deployment Readiness Update

Comprehensive audit and fix pass to make Shogun OS deployable to a fresh Hermes copy with zero errors. Full analysis at `docs/deployment-readiness-review.md`.

#### Fixed: Deployment Blockers

- **Fixed phantom skill references in wire-crons.py:** Replaced 4 non-existent skills (`hr-leave-management`, `finance-budget-tracker`, `project-task-management`, `crm-assistant`) with empty skill arrays so cron creation doesn't fail
- **Added 10 Samurai SOUL snippets to generate-profile.py:** Takumi (coding), Jinzai (hr), Koku (finance), Gorobei (projects), Kura (procurement), Shi (product), Kizuna (crm), Haiku (marketing), Kata (compliance), Bōei (support) — each with persona, responsibilities, boundaries, communication style, and sources
- **Added support profile type** to PROFILE_META (was missing from the profile generator)
- **Added 4 reusable skills:** `slack-formatting`, `brain-compliance`, `profile-enrichment` (gbrain-native shared version), `gbrain-operations`

#### New: Deployment Tooling

- **install.sh:** Added `--deploy` flag (chains install → profile creation → generate-profile for all 10 departments), `--deploy-profile` flag for single-profile deploy
- **install.sh:** Added `section_gbrain()` — checks gbrain is installed, warns if older than v0.42.x, provides install instructions
- **scripts/init-gbrain.sh:** New standalone script — initializes gbrain, creates all 11 sources (shared + 10 departments), configures federated read, verifies connectivity
- **verify-install.sh:** Added MCP connectivity probe — tests gbrain MCP and stock-scanner MCP actually respond
- **verify-install.sh:** Extended skill check from 2 to 6 skills
- **examples/scrum-configs/:** Added 8 new templates (hr, finance, product, crm, support, procurement, marketing, compliance) — 9 total with existing project-manager.yaml. Each has placeholder Slack IDs, team roster, and domain terms
- **scripts/backup-crons.py:** Export all cron jobs to portable JSON for cross-machine migration
- **scripts/restore-crons.py:** Restore cron jobs from backup via `hermes cron create` — supports dry-run, profile filter
- **skills/gbrain-operations:** Slimmed from 96KB to 10KB — stripped Your Company-specific content, kept generic gbrain CLI patterns (sync, embed, doctor, dream, MCP, Python wrapper, troubleshooting). Removed 12 personal references, kept 7 generic ones
- **skills/brain-compliance:** Updated validator reference to prefer gbrain MCP tools over local validator script

#### Documentation

- **docs/deployment-readiness-review.md:** Full gap analysis, execution plan, skills audit, profile mapping, closure criteria
- **HUB.md:** Updated skill table with 4 new skills
- **README.md:** Complete rewrite — gbrain-inspired structure: vision statement, concrete "what this looks like" example, architecture diagram, quick start, install-by-agent pattern, contents table, skill table, troubleshooting section
- **AGENTS.md:** New agent-first deployment guide with entry order, file layout, common tasks, trust boundary
- **INSTALL_FOR_AGENTS.md:** New full 8-phase install protocol for AI agents (clone → API keys → gbrain init → profile deploy → Slack setup → cron wiring → verify → go live)
- **CLAUDE.md:** New Claude Code entry point with orientation, key files, cross-cutting invariants
- **CONTRIBUTING.md:** New contributor guide — what goes in/out, repo structure, skill format, PR workflow
- **SECURITY.md:** New security policy — threat model, trust boundaries, secret management, operational security
- **llms.txt:** New documentation map for single-fetch LLM context injection (inspired by gbrain's llms.txt) — uses raw GitHub URLs for automated fetching
- **scripts/build-llms.sh:** New script that generates `llms-full.txt` by inlining 7 core docs (AGENTS.md, INSTALL_FOR_AGENTS.md, ARCHITECTURE.md, SETUP.md, PROFILE_CATALOG.md, CRON_INVENTORY.md, SECURITY.md) into a single 1,391-line file for single-fetch LLM context injection
- **docs/tutorials/getting-started.md:** New tutorial — from zero to first department agent in 30 minutes (10 steps, covers prerequisites through verification)
- **docs/tutorials/add-new-department.md:** New tutorial — how to create a new department agent beyond the 10 defaults (gbrain source → PROFILE_META → SOUL → cron → scrum → deploy), using Legal/Hōritsu as a worked example
- **docs/architecture/OVERVIEW.md:** New architecture docs — three layers, profile architecture, MCP wiring, scrum architecture, data flow, cron architecture, security model
- **docs/architecture/PROVIDER_ABSTRACTION.md:** New architecture — bring-your-own-backend pattern for agent profiles. Standard MCP contract interface with pluggable provider bridges. Three layers: generic skill → provider bridge → external API. Covers time tracking, HR leave, and expense contracts.
- **recipes/time-tracking/ (new):** Provider abstraction directory with CONTRACT.md (9 standard tt_* tools, response shapes), GENERIC_SKILL.md (provider-agnostic agent workflows), bridges/tt-bridge-jibble.py (reference Jibble implementation), providers/kami.md (Kami setup guide)
- **recipes/jibble-time-tracking.md (updated):** Marked as SUPERSEDED — points to new time-tracking abstraction
- **docs/architecture/COMMS_ABSTRACTION.md:** New architecture — communication provider abstraction. Standard interface (send_dm, read_replies, post_message, add_reaction) with pluggable providers (Slack, Telegram). Provider auto-discovery via `comm/provider.py`.
- **skills/department-scrum/scripts/comm/ (new):** Provider abstraction module with `provider.py` (interface + registry + auto-discovery), `slack.py` (using slack_sdk WebClient), `telegram.py` (using direct Telegram Bot HTTP API)
- **skills/department-scrum/scripts/send-scrum-dms.py (rewritten):** Replaced direct Slack API calls with abstract comm provider. Reads `comm_provider` from scrum.yaml (defaults to slack). Uses `user_id` field (falls back to `slack_id` for backward compat). State file uses provider-agnostic `thread_id`/`conversation_id` instead of Slack-specific `dm_channel`/`question_ts`.
- **skills/department-scrum/scripts/comm/lark.py (new):** Lark (Feishu) communication provider — implements CommProvider interface using Lark Open APIs. Supports app_id+app_secret auth with auto-refresh, or direct access token. Maps send_dm, post_message, add_reaction, search_messages.
- **scripts/verify-e2e.py (new):** 14-test E2E suite covering all comm providers (Slack, Telegram, Lark), time tracking contract/bridge, scrum state format, backward compatibility. Mock-based — no real API keys needed. Run: `python3 scripts/verify-e2e.py`
- **docs/architecture/COMMS_ABSTRACTION.md (new):** Architecture doc for pluggable comm providers. Documents the CommProvider interface, MCP comm_* tool contract, provider registration pattern, and how to add new providers.
- **skills/department-scrum/references/scrum-config-schema.md (updated):** Added `comm_provider` field to full schema example
- **examples/scrum-configs/ (9 templates updated):** Added `comm_provider: slack` to all 9 templates

---

## [2.2.0] — 2026-06-23

### Added: Phases 4–8 (Profile Generator, Cron Wirer, Verification, Docs, Hub)

Complete Shogun OS tooling and documentation suite:

#### New Scripts

| Script | Purpose |
|--------|---------|
| `scripts/generate-profile.py` | Generate new Hermes profiles from templates with SOUL.md, config.yaml, scrum config |
| `scripts/wire-crons.py` | Generate and optionally apply cron jobs per profile type (--list, --apply, --output) |
| `scripts/verify-install.sh` | Full install verification with --quick and --fix modes; checks skills, scripts, configs, symlinks |

#### New Docs Structure

- `docs/README.md` — Phase index and quick reference
- `docs/phase-01-restructure.md` through `docs/phase-08-hub-publishing.md` — Phase-by-phase development docs with design decisions

#### Hub Publishing

- Created `HUB.md` — Hermes skill tap manifest. Usage: `hermes skills tap add limcheehow/shogun-os`

#### Docs Updated

- `README.md` — Contents table now includes `docs/` reference

## [1.1.0] — 2026-06-22

### Added: Cross-Department Scrum Workflow

New shared skill `skills/shared/department-scrum/` — a unified 3-tier daily scrum (9am/11am/5pm) that works for ANY department profile:

- **Generic scripts** — `send-scrum-dms.py` and `check-scrum-replies.py` accept `--profile` flag, read per-profile `scrum.yaml` config
- **48 test suite** — config parsing, task ID extraction, domain term matching, SMART quality gates, state file schema, cross-dept isolation
- **Cron templates** — 4 templates (9am, 11am, 5pm, holiday gate) with placeholders for any profile
- **Option B DM handling** — SOUL.md snippet replaces socket daemons with gateway-based routing
- **Per-profile config** — `scrum.yaml` with team roster, task ID patterns, domain terms, brain source

### Updated

- `ARCHITECTURE.md` — added Scrum Architecture section (Option B gateway + 3-tier cadence)
- `CRON_INVENTORY.md` — replaced old single-standup pattern with 3-tier scrum crons per profile
- `PROFILE_CATALOG.md` — added scrum columns, task IDs, scrum.yaml requirements
- `SETUP.md` — Phase 5.2 now documents scrum setup (prerequisites, cron wiring, verification)
- `README.md` — added Scrum Workflow section, updated shared skills and contents table
- `RECIPE_INDEX.md` — added department-scrum recipe (#9) with dependency and installation order

### Examples

- `examples/scrum-configs/project-manager.yaml` — complete scrum.yaml for Gorobei (9 members, 22 domain terms, TS ticket patterns)

## [2.0.0] — 2026-06-22

### Repo Restructure

Complete overhaul for Hermes compliance and new-user experience:

- **Flattened layout** — `skills/`, `templates/`, `scripts/`, `tests/` at repo root (removed `skills/shared/`, `plugins/`, `profile-templates/`)
- **Removed non-compliant plugin shell** — `plugins/brain-ingest-pipeline/` stripped of non-functional `plugin.yaml`/`__init__.py` `ctx.register_skill()` pattern; SKILL.md and scripts moved to `skills/brain-ingest-pipeline/`
- **Removed superseded recipes** — `email-to-brain.md` and `calendar-to-brain.md` deleted; replaced by `brain-ingest-pipeline` skill
- **All doc paths updated** — README, SETUP, ARCHITECTURE, CRON_INVENTORY, PROFILE_CATALOG, RECIPE_INDEX now reference new locations

### Path Changes

| Old Path | New Path |
|---|---|
| `skills/shared/department-scrum/` | `skills/department-scrum/` |
| `plugins/.../skills/brain-ingest-pipeline/` | `skills/brain-ingest-pipeline/` |
| `profile-templates/` | `templates/profiles/` |
| `plugins/brain-ingest-pipeline/scripts/` | `skills/brain-ingest-pipeline/scripts/` |

## [1.2.0] — 2026-06-22

### Added: Brain Ingest Pipeline

New unified **COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE** pipeline as a Hermes plugin:

- **Plugin** at `plugins/brain-ingest-pipeline/` — first-class Hermes plugin with registerable skill
- **Gmail triage** — `gmail-triage.py` replaces old IMAP email collector: labels inbox via Gmail API (Sales, Projects, HR, Finance, etc.), priority scoring (high/medium/low), promotion detection, batch rotation
- **Calendar collector** — `collect-calendar.py` replaces old single-user OAuth: SA-DWD, all 10 team members' calendars, 7d lookback + 14d lookahead, PII scrubbing
- **5-phase skill** — `brain-ingest-pipeline` skill defines the unified flow for all data sources
- **Batch config** — `examples/brain-ingest-configs/gmail-batches.json` — 3 batches of 3-4 accounts

### Removed

- Old `email-collector`, `calendar-sync`, `email-enrichment`, `calendar-enrichment` crons — replaced by pipeline
- OAuth token refresh cron — not needed with SA-DWD

### Updated

- `ARCHITECTURE.md` — added Brain Ingest Pipeline section with data flow diagram and key design decisions
- `CRON_INVENTORY.md` — replaced old email/calendar crons with the 3 new pipeline crons
- `README.md` — updated infrastructure table, added Brain Ingest Pipeline section with flow diagram
- `SETUP.md` — added SA-DWD key setup note in Phase 2