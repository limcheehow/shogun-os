# Shogun OS — Docs

This directory documents the phased development of Shogun OS, a Hermes Agent companion repository that standardizes skills, templates, profiles, and scripts for new-user onboarding.

## Phase Index

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

## Quick Reference

- **Skills:** [`../skills/`](../skills/) — `shogunify`, `department-scrum`, `brain-ingest-pipeline`, `company-workflow`, …
- **Scripts:** [`../scripts/`](../scripts/) — `install.sh`, `generate-profile.py`, `install-web.sh`, `wire-crons.py`, `verify-install.sh`
- **Templates:** [`../templates/`](../templates/) — profile configs
- **Examples:** [`../examples/`](../examples/) — scrum configs, gmail batch configs
- **Recipes:** [`../recipes/`](../recipes/) — integration guides
- **Schema:** [`../schema/`](../schema/) — config schemas
- **Web portal design:** [`architecture/WEB_PORTAL.md`](architecture/WEB_PORTAL.md) — one dashboard, random URL, our Cloudflare
- **Cloudflare (operator):** [`ops/cloudflare-registry-setup.md`](ops/cloudflare-registry-setup.md)
- **WSL Azure deploy (for Hermes on Windows VM):** [`ops/deploy-registry-wsl-azure.md`](ops/deploy-registry-wsl-azure.md)
- **Shogunify (add skill/connector/workflow):** [`recipes/shogunify.md`](recipes/shogunify.md) — slash `/shogunify`
- **Provider abstractions guide:** [`recipes/creating-provider-abstractions.md`](recipes/creating-provider-abstractions.md)
- **Microsoft 365 Integration:** [`../skills/devops/microsoft-integration/`](../skills/devops/microsoft-integration/) — Graph API client for mail, calendar, OneDrive, and directory
