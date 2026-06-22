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