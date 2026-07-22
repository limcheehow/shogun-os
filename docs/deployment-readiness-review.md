---
title: Company OS — Deployment Readiness Review & Execution Plan
date: 2026-06-25
author: Hermes Agent (Company OS analysis)
version: 1.0.0
status: planning
---

# Company OS — Deployment Readiness Review & Execution Plan

## Purpose

This document captures a comprehensive audit of the `company-os` repository (v2.2.0) against the actual running Your Company Hermes deployment. It identifies gaps, prioritizes fixes, and provides an execution plan to make the repo deployable to a fresh Hermes copy with zero errors.

## Method

The review compared three sources:

1. **`company-os/` (v2.2.0)** — the blueprint repo at `github.com/limcheehow/company-os`
2. **`your-company-hermes/`** — the predecessor local directory with legacy recipes and profile templates
3. **Running Hermes instance** — 22 live profiles with real SOUL.md, cron jobs, skills, and configuration at `~/.hermes/`

## Architecture (3-Layer)

```
Layer 1: Hermes Agent Profiles
  ├── 10 department profiles + default profile (shared infra)
  ├── Each isolated: SOUL.md, config.yaml, skills/, cron/, memories/, gbrain source
  └── Samurai Personas: Takumi, Jinzai, Koku, Gorobei, Kura, Shi, Kizuna, Haiku, Kata, Bōei

Layer 2: GBrain (Knowledge Layer)
  ├── 12 sources: shared, hr, finance, projects, procurement, products, crm, marketing, compliance, engineering, support
  ├── Federated read: every profile reads shared/ (staff, policies)
  └── Hybrid search via pgvector in Supabase

Layer 3: Communication
  └── One Slack bot per profile (isolated — no cross-dept visibility)
```

## Gap Analysis

### 🔴 Critical — Deployment Blockers

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| G1 | `wire-crons.py` references 4 phantom skills: `hr-leave-management`, `finance-budget-tracker`, `crm-assistant`, `project-task-management` — these don't exist in the repo or on the running machine | Crons created by `wire-crons --apply` reference skills that will silently fail to load | Remove or replace with actual shared skills |
| G2 | Only 2 of 10 Samurai SOUL snippets ship in `generate-profile.py` (`engineering`, `hr`) — 8 profiles get generic stubs | New profiles get empty personas with no domain boundaries or voice | Extract all 10 SOUL.md from running profiles |
| G3 | Only 2 skills ship in repo (`department-scrum`, `brain-ingest-pipeline`). 4 essential skills (`slack-formatting`, `gbrain-operations`, `brain-compliance`, `profile-enrichment`) are missing | Fresh deploy has no formatting, enrichment, or brain ops skills | Copy into `skills/` |
| G4 | No gbrain version pinning in install scripts | Deploy uses whatever `gbrain --version` happens to be installed | Add `gbrain --version` check & recommended version |

### 🟡 Deployment Tooling — High Friction

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| G5 | `install.sh` runs standalone — doesn't chain profile gen, cron wiring, or gbrain init | User must manually run 4+ commands per profile × 10 profiles | Add `--deploy <profile>` flag |
| G6 | No gbrain source init automation | 10 `gbrain init-source` commands + federated read config must be run manually | Add `scripts/init-gbrain.sh` |
| G7 | 9 of 10 scrum.yaml configs missing (only `project-manager.yaml` exists) | Scrum workflow won't work for other departments | Create one per profile |
| G8 | `verify-install.sh` doesn't check MCP connectivity | Scripts may exist but gbrain/stock-scanner MCP may not respond | Add MCP probe |

### 🟢 Polish — Important but Non-Blocking

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| G9 | `gbrain-operations` skill has Your Company-specific paths/troubleshooting | Not reusable out of the box | Strip personal/CH-specific sections |
| G10 | No cron state migration | 54 cron jobs must be re-created manually on new machine | Add export/restore scripts |
| G11 | Superseded recipes still in `your-company-hermes/` | `email-to-brain.md` and `calendar-to-brain.md` replaced by `brain-ingest-pipeline` skill | Mark as deprecated |

## Execution Plan

### Phase 0 — Critical (3 hours)

```
[ ] 0.1 — Fix wire-crons.py phantom skill references
[ ] 0.2 — Add 10 Samurai SOUL snippets to generate-profile.py
[ ] 0.3 — Add 4 essential skills to skills/ directory
[ ] 0.4 — Patch install.sh to sync new skills + add gbrain version check
```

### Phase 1 — Tooling (3 hours)

```
[ ] 1.1 — Chain install.sh with profile gen (`--deploy` flag)
[ ] 1.2 — Create scripts/init-gbrain.sh with latest gbrain version
[ ] 1.3 — Build 10 scrum.yaml templates in examples/scrum-configs/
[ ] 1.4 — Add MCP probe to verify-install.sh
```

### Phase 2 — Polish (1.5 hours)

```
[ ] 2.1 — Create cron export/restore scripts
[ ] 2.2 — Slim gbrain-operations for reuse
[ ] 2.3 — Update README and HUB.md with new skills
```

## Skills Audit

### Skills to Ship in Repo (Essential + Reusable)

| Skill | Source | Reusable? | Notes |
|-------|--------|-----------|-------|
| `department-scrum` | Already in repo ✅ | ✅ | Cross-dept 3-tier scrum |
| `brain-ingest-pipeline` | Already in repo ✅ | ✅ | 5-phase data pipeline |
| `slack-formatting` | Copy from running Hermes | ✅ | Clean — formatting only |
| `gbrain-operations` | Copy + slim | ✅ After stripping | Remove Your Company-specific paths |
| `brain-compliance` | Copy from running Hermes | ✅ | Validation rules |
| `shared/profile-enrichment` | Copy (NOT productivity/ version) | ✅ | gbrain-native, no personal deps |

### Skills NOT to Ship (Personal / Your Company-Specific)

| Skill | Reason |
|-------|--------|
| `productivity/profile-enrichment` (v2.6) | Chrome CDP, Apollo.io, personal brain paths, Facebook friends |
| `google-workspace` | Personal Google account config |
| `fitness-tracking`, `meal-planner`, `budget-tracking` | Personal |
| `technical-trading-scanner`, `atm-fibo-scanner` | Personal trading |
| `expense-tracker-pro` | Personal finance |
| `trip-planner`, `news-digest-management` | Personal preferences |

## Profile Persona Mapping

| Company-OS Profile | Running Profile | Persona |
|--------------------|----------------|---------|
| coding-agent | `coding-agent` | Takumi (匠) |
| hr-manager | `hr-manager` | Jinzai (人材) |
| finance-manager | `finance-manager` | Koku (石) |
| project-manager | `project-manager` | Gorobei (五郎兵衛) |
| procurement-manager | `procurement-manager` | Kura (蔵) |
| product-manager | `product-manager` | Shi (志) |
| crm-manager | `crm-manager` | Kizuna (絆) |
| marketing-manager | `marketing-manager` | Haiku (俳句) |
| compliance-manager | `compliance-manager` | Kata (型) |
| customer-support | `customer-support` | Bōei (防衛) |

## Closure Criteria

The repo is deployable-to-zero-error when:

1. A fresh Hermes install + `git clone` + `./install.sh --deploy all` produces 10 working profiles
2. Each profile has correct SOUL.md, config.yaml, scrum.yaml, and gbrain source
3. `verify-install.sh` passes all checks including MCP connectivity
4. Cron jobs can be wired with `wire-crons.py --apply` without errors
5. Skills load without "skill not found" warnings

---

*Analysis generated by Hermes Agent during Company OS readiness audit, June 2026.*