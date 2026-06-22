# Changelog

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