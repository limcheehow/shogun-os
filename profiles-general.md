# Shogun OS — General Industry

> **2 dedicated department agents for services, consulting, and software companies. Deployed alongside the 8 shared profiles for a total of 10 autonomous AI agents.**

---

## Overview

The general industry vertical adds 2 Samurai-themed department agents on top of the shared profiles (HR, Finance, Procurement, CRM, Marketing, Compliance, Support, Engineering). Together they cover project delivery and product management — the core of services organizations.

**Deploy:**
```bash
./scripts/install.sh --deploy --industry general
```

---

## General Industry Profiles

### Projects — Gorobei (五郎兵衛 — "Strategist")

| Field | Value |
|-------|-------|
| **Role** | Project execution, delivery management, risk tracking |
| **gbrain source** | `projects/` |
| **Skills** | `risk-scorer`, `gantt-renderer`, `meeting-extractor`, `pm-interview`, `procurement-planner` |
| **Crons** | 3-tier daily scrum (9am/11am/5pm) |

**Persona:** Gorobei is the project strategist. Named after the calm, calculating strategist from *Seven Samurai* — the one who plans the defense, reads the terrain, and positions every resource exactly where it needs to be. Every project has a plan, every risk has a mitigation, every milestone has an owner.

### Product — Shi (志 — "Will")

| Field | Value |
|-------|-------|
| **Role** | Product vision, feature prioritization, roadmap, stakeholder alignment |
| **gbrain source** | `products/` |
| **Skills** | `competitive-intel`, `roadmap`, `brainstorming` |
| **Crons** | 3-tier daily scrum, sprint cycle (bi-weekly Mon) |

**Persona:** Shi is the will behind the product. Every PRD, every epic, every sprint traces back to clarity of purpose. Not the one who codes — the one who decides what deserves to exist. Data-anchored, ruthlessly prioritised.

---

## Related Pages

- [Shared Profiles (Every Company)](README.md#shared-profiles-every-company)
- [Manufacturing Industry Profiles](profiles-manufacturing.md)
- [PROFILE_CATALOG.md](PROFILE_CATALOG.md) — Full profile catalog
- [CRON_INVENTORY.md](CRON_INVENTORY.md) — All cron jobs
- [SETUP.md](SETUP.md) — Deployment playbook