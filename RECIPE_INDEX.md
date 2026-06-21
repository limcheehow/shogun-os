# Recipe Index

Self-contained integration packages (gbrain recipe style). Each has YAML frontmatter with metadata and a full setup playbook.

## Dependency Graph

```
google-dwd (auth)
  ├── token-watchdog (optional belt-and-suspenders)
  ├── email-to-brain
  ├── calendar-to-brain
  ├── drive-to-brain
  └── slides-deck-gen

token-utilization (standalone — no deps)
jibble-time-tracking (standalone — no deps)
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

### 3. `email-to-brain` — Gmail → Knowledge Base

| Field | Value |
|-------|-------|
| Category | ingest |
| Setup time | 20 min |
| Cost | $0 |
| Depends on | google-dwd |
| Crons | Collector every 30min (no_agent) + Enrichment 9/13/17 (agent) |

Deterministic collector pulls Gmail inbox, filters noise, generates Gmail links in code. Agent reads digest and updates person/company brain pages.

### 4. `calendar-to-brain` — Calendar → Brain Pages

| Field | Value |
|-------|-------|
| Category | ingest |
| Setup time | 20 min |
| Cost | $0 |
| Depends on | google-dwd |
| Crons | Daily sync 6AM (no_agent) + Attendee enrichment 8AM (agent) |

Paginated sync pulls events, writes daily markdown files with attendees and locations. Agent extracts attendees and creates/updates person pages.

### 5. `drive-to-brain` — Google Drive → Knowledge Base

| Field | Value |
|-------|-------|
| Category | ingest |
| Setup time | 20 min |
| Cost | $0 |
| Depends on | google-dwd |
| Crons | Sync 12/16/20 weekdays (no_agent) + Enrichment 13/17 (agent) |

Monitors Drive folders for documents (meeting notes, proposals, reports), syncs to brain pages with entity extraction.

### 6. `token-utilization` — AI Spend Monitoring

| Field | Value |
|-------|-------|
| Category | monitor |
| Setup time | 5 min |
| Cost | $0 |
| Depends on | — |
| Cron | Weekly Monday 8AM, no_agent, default profile |

Runs `tokscale monthly --json` and generates a formatted markdown report showing cost, tokens, cache efficiency per model per month.

### 7. `jibble-time-tracking` — HR Time Tracking

| Field | Value |
|-------|-------|
| Category | connector |
| Setup time | 15 min |
| Cost | $0 |
| Depends on | — |
| Crons | Daily attendance 9:30AM + Weekly timesheet Mon 10AM (hr-manager) |

MCP bridge + skill + cron templates for Jibble time tracking. Query time entries, detect late arrivals, compile weekly timesheets.

### 8. `slides-deck-gen` — Google Slides Integration

| Field | Value |
|-------|-------|
| Category | connector |
| Setup time | 15 min |
| Cost | $0 |
| Depends on | google-dwd |
| Cron | (none — ad-hoc) |

Slides API skill for creating decks, replacing placeholder text, adding slides, exporting as PDF. Used by marketing-manager (Haiku) for client decks.

## Installation Order

```
1. google-dwd              # Foundation — everything needs auth
2. token-utilization       # Standalone — can do anytime
3. token-watchdog          # Optional — only if caching tokens
4. email-to-brain          # Requires DWD
5. calendar-to-brain       # Requires DWD
6. drive-to-brain          # Requires DWD
7. jibble-time-tracking    # Standalone — for hr-manager
8. slides-deck-gen         # Requires DWD — for marketing-manager
```