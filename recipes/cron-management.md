---
name: cron-management
id: cron-management
category: ops
setup_time: 5
cost: $0
depends_on: [hermes-agent]
---

# Cron Job Management

Lifecycle management for Hermes Agent cron jobs — creation, backup, restore, and migration.

## Setup

The backup/restore scripts are already in the repo:

```bash
# Backup all cron jobs to portable JSON
python3 scripts/backup-crons.py --output cron-backup.json

# Restore from JSON (dry-run first)
python3 scripts/restore-crons.py --input cron-backup.json --dry-run

# Restore for real
python3 scripts/restore-crons.py --input cron-backup.json
```

## Cron Job Patterns

### Deterministic (no_agent) — Code for Data
```bash
cronjob action=create schedule='*/30 * * * *' name='my-job' \
  script='my-script.sh' no_agent=true deliver=local
```

### Agent (LLM-driven) — LLMs for Judgment
```bash
cronjob action=create schedule='0 9,13,17 * * 1-5' name='my-agent-job' \
  prompt='Do the thing.' skills=['brain-ingest-pipeline'] deliver=origin
```

### Script-only (no agent, no script — watchdog pattern)
```bash
cronjob action=create schedule='*/2 * * * *' name='my-watchdog' \
  script='my-watchdog.sh' no_agent=true deliver=local
```

## Migration Across Machines

1. On source machine:
```bash
python3 scripts/backup-crons.py --output cron-backup.json
```

2. Copy `cron-backup.json` to the new machine

3. On target machine:
```bash
python3 scripts/restore-crons.py --input cron-backup.json --dry-run  # verify
python3 scripts/restore-crons.py --input cron-backup.json            # apply
```

## Config

No additional config — uses Hermes CLI directly.
