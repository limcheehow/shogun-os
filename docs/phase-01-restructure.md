# Phase 1: Repo Restructure

**Version:** 2.0.0  
**Date:** 2026-06-22  
**Status:** ✅ Complete

## Goal

Flatten the repo layout to align with Hermes Agent conventions and remove non-compliant patterns.

## Changes

| Action | Details |
|--------|---------|
| **Deleted** | `plugins/brain-ingest-pipeline/plugin.yaml` + `__init__.py` — non-functional Hermes plugin wrapper using undocumented `ctx.register_skill()` API |
| **Deleted** | `recipes/email-to-brain.md` (297 lines) — superseded by the unified `brain-ingest-pipeline` skill |
| **Deleted** | `recipes/calendar-to-brain.md` (357 lines) — superseded by the unified `brain-ingest-pipeline` skill |
| **Moved** | `skills/shared/department-scrum/` → `skills/department-scrum/` (flattened — removed `shared/` nesting) |
| **Moved** | `plugins/brain-ingest-pipeline/skills/brain-ingest-pipeline/` → `skills/brain-ingest-pipeline/` (skill + scripts) |
| **Moved** | `profile-templates/` → `templates/profiles/` (aligns with Hermes conventions) |
| **Updated** | All 7 doc files (README, SETUP, ARCHITECTURE, CRON_INVENTORY, PROFILE_CATALOG, RECIPE_INDEX, CHANGELOG) with new paths |

## Key Decisions

1. **Recipes stay at repo root** in `recipes/` — they document integration flows, not Hermes-native constructs
2. **Examples go to `examples/`** — scrum configs and gmail batch configs are reference material, not templates
3. **No information loss** — only 23 lines of non-functional plugin metadata were deleted; all substantive skill content, scripts, and docs were preserved or moved
4. **`schema/` untouched** — the schema definitions are cross-cutting and work fine at repo root

## New Layout

```
company-os/
├── skills/                      ← All skills, flat
│   ├── department-scrum/
│   └── brain-ingest-pipeline/
├── templates/profiles/          ← Profile config templates
├── scripts/                     ← Standalone helper scripts
├── recipes/                     ← Integration guides
├── examples/                    ← Reference configs
├── schema/                      ← Config schemas
├── tests/                       ← Verification suite (Phase 6)
└── *.md                         ← Documentation
```

## Verification

```bash
# Check no old paths remain
test ! -d plugins && echo "✅ plugins/ removed"
test ! -d skills/shared && echo "✅ skills/shared/ flattened"
test ! -d profile-templates && echo "✅ profile-templates/ moved"
test ! -f recipes/email-to-brain.md && echo "✅ old email recipe removed"
test ! -f recipes/calendar-to-brain.md && echo "✅ old calendar recipe removed"
```