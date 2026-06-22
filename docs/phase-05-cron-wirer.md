# Phase 5: Cron Wirer

**Version:** 2.2.0  
**Date:** 2026-06-23  
**Status:** ✅ Complete

## Goal

Create a script that generates and optionally applies cron jobs for any Hermes profile based on its type — eliminating the manual cron-wiring step from the setup process.

## Script: `scripts/wire-crons.py`

### Usage

```bash
# Show summary of recommended crons
python3 scripts/wire-crons.py gorobei --type project-manager

# List as hermes CLI commands
python3 scripts/wire-crons.py gorobei --type project-manager --list

# Apply crons (requires hermes CLI)
python3 scripts/wire-crons.py gorobei --type project-manager --apply

# Dry-run apply
python3 scripts/wire-crons.py gorobei --type project-manager --apply --dry-run

# Write to YAML file
python3 scripts/wire-crons.py gorobei --type project-manager --output crons.yaml

# Custom delivery target
python3 scripts/wire-crons.py jinzai --type hr --deliver telegram:-1001234567890
```

### Cron Jobs Per Profile Type

| Type | Scrum 9a | Scrum 11a | Scrum 5p | Holiday Gate | Extra |
|------|----------|-----------|----------|--------------|-------|
| `base` | ✅ | ✅ | ✅ | ✅ | — |
| `hr` | ✅ | ✅ | ✅ | ✅ | Daily leave summary at 8a |
| `finance` | ✅ | ✅ | ✅ | ✅ | Budget check at 10a |
| `project-manager` | ✅ | ✅ | ✅ | ✅ | Daily status at 9:30a |
| `crm` | ✅ | ✅ | ✅ | ✅ | Pipeline check at 9a |
| `engineering` | ✅ | ✅ | ✅ | ✅ | Deployment check at 9a |
| `compliance` | ✅ | ✅ | ✅ | ✅ | Weekly audit Mon 10a |
| `marketing` | ✅ | ✅ | ✅ | ✅ | Weekly campaign Mon 9a |
| `procurement` | ✅ | ✅ | ✅ | ✅ | Weekly PO reminder Mon 9a |
| `product` | ✅ | ✅ | ✅ | ✅ | Weekly sprint reminder Mon 9a |
| `coding` | ✅ | ✅ | ✅ | ✅ | Daily PR reminder at 10a |

### Mode: `--apply`

When `--apply` is used, the script calls `hermes cron create` for each job. Requires:
1. The `hermes` CLI in PATH
2. The target profile to already exist
3. Cron scheduler running (for jobs to actually fire)

### Mode: `--output`

Writes a YAML file with all cron specs that can be reviewed or committed to version control before applying.

### Design Decisions

1. **Scrum defaults to `deliver: local`** — morning/midday/eod scrum data is saved locally rather than sent to a channel; individual profiles can override this
2. **Extra crons are scheduled at distinct times** — never overlapping with scrum crons (8:00, 9:30, 10:00)
3. **Holiday gate runs early at 6:00** — before any scrum cron, giving time to suppress morning reminders
4. **Self-contained prompts** — each cron prompt includes the skill load instruction so it works independently of session state