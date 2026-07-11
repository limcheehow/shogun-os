# Recipe Index

Self-contained integration packages (gbrain recipe style). Each has YAML frontmatter with metadata and a full setup playbook.

## Dependency Graph

```
google-dwd (auth)
  ├── token-watchdog (optional belt-and-suspenders)
  ├── brain-ingest-pipeline (replaces old email/calendar collectors)
  ├── drive-to-brain
  └── slides-deck-gen

token-utilization (standalone — no deps)
jibble-time-tracking (standalone — no deps)
department-scrum (standalone — no deps, requires Hermes + Slack)
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

MCP bridge + skill + cron templates for Jibble time tracking. Query time entries, detect late arrivals, compile weekly timesheets.

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

### 10. `model-health-auto-fallback` — Provider Auto-Failover

| Field | Value |
|-------|-------|
| Category | infra |
| Setup time | 10 min |
| Cost | $0 |
| Depends on | — |
| Cron | Every 5 min, no_agent, default profile |

Tests primary provider every 5 minutes. Auto-switches to backup on failure, switches back when primary recovers. Config-driven — reads provider settings from `config.yaml`.

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

Profile creation patterns: SOUL.md authoring with workflow enforcement snippet, config.yaml from templates, systemd enable + start, skill installation via symlink.

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

## Installation Order

```
 1. google-dwd              # Foundation — everything needs auth
 2. token-utilization       # Standalone — can do anytime
 3. token-watchdog          # Optional — only if caching tokens
 4. brain-ingest-pipeline   # Requires DWD — replaces old email/calendar collectors
 5. drive-to-brain          # Requires DWD
 6. jibble-time-tracking    # Standalone — for hr-manager
 7. slides-deck-gen         # Requires DWD — for marketing-manager
 8. department-scrum        # Standalone — add after profile basics are set up
 9. gateway-systemd-management  # Infra — add after profiles are deployed
10. model-health-auto-fallback  # Infra — add after gateway is running
11. brain-maintenance       # Ops — add after brain has content
12. profile-provisioning    # Ops — reference for adding new profiles
13. cron-management         # Ops — for backup/restore
14. session-db-postgres     # Infra — for multi-profile deployments
15. scrum-production-hardening  # Reference — read before going live with scrum
```