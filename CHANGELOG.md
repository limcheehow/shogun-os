# Changelog

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

Comprehensive audit and fix pass to make Company OS deployable to a fresh Hermes copy with zero errors. Full analysis at `docs/deployment-readiness-review.md`.

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

Complete Company OS tooling and documentation suite:

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

- Created `HUB.md` — Hermes skill tap manifest. Usage: `hermes skills tap add limcheehow/company-os`

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