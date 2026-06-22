# Phase 2: Install Script

**Version:** 2.1.0  
**Date:** 2026-06-22  
**Status:** ✅ Complete

## Goal

Create a comprehensive `install.sh` that deploys all Company OS assets into `~/.hermes/` with safety checks, dry-run mode, and profile-specific installs.

## Script: `scripts/install.sh`

### Features

| Feature | Flag | Description |
|---------|------|-------------|
| Full install | (none) | Installs all skills, scripts, configs, and symlinks |
| Dry-run | `--dry-run` | Preview without making changes |
| Force overwrite | `--force` | Overwrite without backup prompt |
| Profile-specific | `--profile <name>` | Install only assets relevant to a given profile |
| Help | `--help` | Show usage |

### Installed Assets

| Asset | Destination | Condition |
|-------|-------------|-----------|
| `skills/brain-ingest-pipeline/` | `~/.hermes/skills/brain-ingest-pipeline/` | Full install (or `--profile default`/`--profile pipeline`) |
| `skills/department-scrum/` | `~/.hermes/skills/department-scrum/` | Always (needed by all profiles) |
| Skill scripts (flat) | `~/.hermes/scripts/` | Always — flattens all `*/scripts/*` files |
| `scripts/switch-profile.py` | `~/.hermes/scripts/switch-profile.py` | Always |
| `examples/brain-ingest-configs/gmail-batches.json` | `~/.hermes/config/gmail-batches.json` | Always |
| `examples/scrum-configs/project-manager.yaml` | `~/.hermes/company-os-examples/scrum-configs/project-manager.yaml` | Always |
| SA-DWD symlink | `~/.hermes/service-account-key.json` → `~/.hermes/secrets/google-dwd-sa.json` | If SA key exists |

### Safety

- **Backups** — existing files are backed up to `~/.hermes/.company-os-backup/<timestamp>/` before overwrite
- **Source validation** — aborts if `skills/` directory is missing
- **Dry-run** — preview without side effects
- **Force flag** — skip backup prompt for automated installs

### Design Decisions

1. **Scripts are installed flat** (not in subdirectories) — `~/.hermes/scripts/*.py` is where Hermes cron scripts look by default
2. **Backup directory** is nested under `~/.hermes/.company-os-backup/` — keeps backups close to the assets they protect
3. **Profile-specific install** is intentionally narrow: only `department-scrum` (needed by all) plus `brain-ingest-pipeline` for default/pipeline profiles