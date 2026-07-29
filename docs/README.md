# Shogun OS — Technical Documentation Index

Welcome to the technical documentation for **Shogun OS**.

---

## Core Technical Documentation (`tapway-repo-docs` Standard)

| Document | Purpose | Description |
|---|---|---|
| 🏗️ **[ARCHITECTURE.md](ARCHITECTURE.md)** | System Design | 3-layer architecture, Mermaid system diagram, component breakdown, data flow, key design decisions, and external dependencies. |
| 🗄️ **[DB_SCHEMA.md](DB_SCHEMA.md)** | Data Architecture | PostgreSQL + `pgvector` schema for GBrain sources, `budget.json` baseline format, `scrum.yaml` state, and retention policies. |
| 🔄 **[WORKFLOWS.md](WORKFLOWS.md)** | Sequence Diagrams | Mermaid sequence diagrams for Weekly Pulse Report, Monthly Board Report & BvA Variance Analysis, 3-Tier Scrum, and Provisioning. |
| 🚀 **[DEPLOYMENT.md](DEPLOYMENT.md)** | Operations Playbook | Prerequisites, environment variables, profile generation (`generate-profile.py`), cron wiring (`wire-crons.py`), WSL/Linux gateway deployment, and health checks. |

---

## Development Phase Index

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Repo Restructure | ✅ [Docs](phase-01-restructure.md) |
| 2 | Install Script | ✅ [Docs](phase-02-install-script.md) |
| 3 | Skill Compliance | ✅ [Docs](phase-03-skill-compliance.md) |
| 4 | Profile Generator | ✅ [Docs](phase-04-profile-generator.md) |
| 5 | Cron Wirer | ✅ [Docs](phase-05-cron-wirer.md) |
| 6 | Verification Suite | ✅ [Docs](phase-06-verification-suite.md) |
| 7 | Doc Overhaul | ✅ [Docs](phase-07-doc-overhaul.md) |
| 8 | Hub Publishing | ✅ [Docs](phase-08-hub-publishing.md) |

---

## Quick Reference

- **Skills:** [`../skills/`](../skills/) — 22 Finance skills (`skills/finance/`), `shogunify`, `department-scrum`, `brain-ingest-pipeline`, `company-workflow`, …
- **Scripts:** [`../scripts/`](../scripts/) — `install.sh`, `generate-profile.py`, `install-web.sh`, `wire-crons.py`, `verify-install.sh`
- **Templates:** [`../templates/`](../templates/) — profile configs
- **Examples:** [`../examples/`](../examples/) — `finance-budget.json`, scrum configs, gmail batch configs
- **Recipes:** [`../recipes/`](../recipes/) — `recipes/accounting/` (`acct_*` contract), integration guides
- **Schema:** [`../schema/`](../schema/) — config schemas
- **Web portal design:** [`architecture/WEB_PORTAL.md`](architecture/WEB_PORTAL.md)
- **Shogunify (add skill/connector/workflow):** [`recipes/shogunify.md`](recipes/shogunify.md) — slash `/shogunify`
