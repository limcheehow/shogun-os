# Phase 6: Verification Suite

**Version:** 2.2.0  
**Date:** 2026-06-23  
**Status:** ✅ Complete

## Goal

Create a comprehensive verification script that validates all Shogun OS assets are correctly installed and reports any issues with optional auto-fix.

## Script: `scripts/verify-install.sh`

### Usage

```bash
# Full verification
./scripts/verify-install.sh

# Quick mode (skip expensive checks)
./scripts/verify-install.sh --quick

# Auto-fix missing items
./scripts/verify-install.sh --fix
```

### What It Checks

| Check # | Category | What's Verified |
|---------|----------|-----------------|
| 1 | **Skills** | `department-scrum` and `brain-ingest-pipeline` are installed with SKILL.md |
| 2 | **Scripts** | All 6 scripts exist in `~/.hermes/scripts/` (Python syntax validated) |
| 3 | **Configs** | `gmail-batches.json` exists, valid JSON |
| 4 | **Symlinks** | SA-DWD symlink points to valid target |
| 5 | **Hermes Health** | CLI available, skills recognized |
| 6 | **Repo Integrity** | No old paths (plugins/, skills/shared/), removed recipes gone, docs/ present |

### Modes

**Standard mode** runs all checks and reports pass/warn/fail counts. Exits with error code = number of failures (useful for CI).

**Quick mode** (`--quick`) skips Python syntax validation and Hermes skills list check — suitable for rapid verification after install.

**Fix mode** (`--fix`) attempts to re-install any missing items:
- Missing skills → `cp` from repo `skills/` to `~/.hermes/skills/`
- Missing scripts → `find` in repo and `cp` to `~/.hermes/scripts/`
- Missing configs → `cp` from repo `examples/` to `~/.hermes/config/`

### Integration

The script is referenced in the install.sh summary as the final verification step:

```
5. Verify install:    ./verify-install.sh
```

### Design Decisions

1. **Separate from install.sh** — verification is a standalone script so users can re-check at any time, not just after install
2. **Exit code = failure count** — enables CI pipeline integration (`assert $(./verify-install.sh) -eq 0`)
3. **Warnings vs failures** — warnings for optional items (symlinks, Hermes CLI availability), failures for missing critical assets (skills, scripts)
4. **Fix mode idempotent** — re-running fix mode doesn't duplicate or corrupt existing files