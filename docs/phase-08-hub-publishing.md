# Phase 8: Hub Publishing

**Version:** 2.2.0  
**Date:** 2026-06-23  
**Status:** ✅ Complete

## Goal

Make Company OS skills discoverable and installable via the Hermes Agent skill hub system.

## What Was Done

### 1. Created `HUB.md` (Hub Manifest)

A discoverability document at the repo root describing:

- How to add the repo as a Hermes skill tap (`hermes skills tap add limcheehow/company-os`)
- How to install individual skills (`hermes skills install limcheehow/company-os/department-scrum`)
- Listing of available skills with descriptions
- Link to the full repo for profiles, templates, and documentation

### 2. Verified Repository Structure

The repo already follows the required layout for a Hermes skill tap:

```
skills/
├── department-scrum/SKILL.md          ✅
└── brain-ingest-pipeline/SKILL.md     ✅
```

Each skills is already in the standard format with:
- YAML frontmatter (`name`, `description`, `version`, `author`, `metadata.hermes`)
- SKILL.md with progressive disclosure
- `references/`, `templates/`, `scripts/` subdirectories

## How It Works

A "tap" is a GitHub repo containing `skills/<name>/SKILL.md` directories. Users run:

```bash
hermes skills tap add limcheehow/company-os
```

This registers the repo as a skill source. Then:

```bash
hermes skills search pipeline --source limcheehow/company-os
hermes skills install limcheehow/company-os/brain-ingest-pipeline
```

Skills install to `~/.hermes/skills/` and become available as slash commands.

## Future

If Company OS grows additional skills (task-management, profile-enrichment, etc.), they should be added to the `skills/` directory with proper SKILL.md frontmatter — no other hub configuration is needed. The `HUB.md` should be updated to list new skills.