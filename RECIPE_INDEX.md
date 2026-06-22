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

Sets up Google Domain-Wide Delegation — a service account impersonating `cheehow@gotapway.com`. Every Google integration depends on this.

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

See `skills/department-scrum/SKILL.md` for full docs.

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
```