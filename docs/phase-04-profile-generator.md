# Phase 4: Profile Generator

**Version:** 2.2.0  
**Date:** 2026-06-23  
**Status:** ✅ Complete

## Goal

Create a script that generates new Hermes profiles from templates, eliminating manual copying and editing of profile configs.

## Script: `scripts/generate-profile.py`

### Usage

```bash
# Create a basic profile
python3 scripts/generate-profile.py gorobei --type project-manager

# Profile with explicit gbrain source
python3 scripts/generate-profile.py jinzai --type hr --gbrain-source hr

# Clone an existing profile
python3 scripts/generate-profile.py new-profile --clone existing-profile

# Force overwrite existing profile
python3 scripts/generate-profile.py gorobei --type project-manager --force

# List available profile types
python3 scripts/generate-profile.py --list-types
```

### Supported Profile Types

| Type | Description | Config Template | SOUL Theme |
|------|-------------|-----------------|------------|
| `base` | Minimal Hermes profile | `base-config.yaml` | Generic assistant |
| `project-manager` | Project management (Gorobei) | `base-config.yaml` | Gorobei — PM |
| `hr` | HR management (Jinzai) | `base-config.yaml` | Jinzai — HR |
| `finance` | Finance (Koku) | `base-config.yaml` | Koku — Finance |
| `procurement` | Procurement (Kura) | `base-config.yaml` | Kura — Procurement |
| `crm` | Sales/CRM (Kizuna) | `base-config.yaml` | Kizuna — CRM |
| `marketing` | Marketing (Haiku) | `base-config.yaml` | Haiku — Marketing |
| `compliance` | Compliance (Kata) | `base-config.yaml` | Kata — Compliance |
| `product` | Product (Shi) | `base-config.yaml` | Shi — Product |
| `engineering` | Engineering | `coding-config.yaml` | Takumi — Engineering |
| `coding` | Coding agent (Takumi) | `coding-config.yaml` | Takumi — Engineering |

### What It Generates

```
~/.hermes/profiles/<name>/
├── config.yaml              ← Profile config (inherits main + overrides)
├── .env                     ← Environment variable stub
├── SOUL.md                  ← Persona definition
└── scrum.yaml               ← Scrum config (for PM, HR, etc.)
```

The `SOUL.md` includes the profile's persona definition — matching what was manually created for Gorobei and Jinzai in earlier sessions. Each type gets a themed persona with appropriate boundaries and daily workflow.

### Design Decisions

1. **Config inheritance** — profile configs inherit from main via `inherit: true` rather than duplicating all settings
2. **SOUL as persona** — the SOUL.md serves as the agent's personality document, defining what it should and shouldn't do, how it interacts, and its daily cadence
3. **Profile types are opinionated** — each type sets appropriate tool restrictions (e.g., HR profile disables `browser` but keeps `web` for leave policy lookup)
4. **Always generate scrum.yaml** — even basic profiles get a minimal scrum config of 1 member (the profile owner) for future extensibility