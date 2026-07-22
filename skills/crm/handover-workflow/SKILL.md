---
name: handover-workflow
description: "Sales-to-Project handover lifecycle — won deal handover, project initiation gates, activity sync, and risk detection. Bridges CRM and project management agents."
version: 1.0.0
tags: [crm, projects, handover, workflow, gates]
triggers:
  - "handover"
  - "deal won"
  - "close deal"
  - "create project"
  - "handover deal"
  - "process handover"
  - "gate status"
  - "project initiation"
  - "deal activity sync"
  - "sync activity"
---

# Sales-to-Project Handover Workflow

## Overview

When a deal is won in CRM, it must be handed over to the project team. This skill defines the complete lifecycle:

```
Deal Won (CRM Agent)
  │
  ▼
CREATE HANDOVER  →  ~/brain/handovers/pending/<deal>.md
  │  customer info, scope, PO, next steps
  │
  ▼
NOTIFY PROJECT MANAGER  →  Slack/Telegram DM
  │
  ▼
PROCESS HANDOVER  →  Review scope, create project, progress gates
  │  G0 → G1 → G2 → G3
  │
  ▼
HANDOVER COMPLETED  →  Move to ~/brain/handovers/completed/
  │                    Project created in ~/brain/projects/active_projects/
  │
  ▼
ONGOING ACTIVITY SYNC  →  Email → timeline entries + risk detection
```

## Environment Variables

| Env Var | Default | Purpose |
|---------|---------|---------|
| `BRAIN_DIR` | `~/brain` | Brain root directory |
| `HANDOVER_SALES_ROLE` | `CRM Manager` | Who creates handovers |
| `HANDOVER_PROJECT_ROLE` | `Project Manager` | Who processes handovers |
| `HANDOVER_NOTIFY_CHANNEL` | (empty) | Where to notify new handovers (Slack/Telegram channel or DM) |
| `HANDOVER_GATES` | `G0:Deal Scoped,G1:Charter Signed,G2:Kick-off Complete,G3:Funding Cleared` | Configurable gate sequence |

## Handover Directory Structure

```
~/brain/handovers/
├── _schema.json           # Schema for handover pages
├── pending/               # Pending handovers (not yet processed)
│   └── <deal-slug>.md     # Individual handover page
├── pending_prompt/        # Handovers awaiting a prompt from the creator
│   └── _schema.json       # Schema for pending_prompt
└── completed/             # Completed handovers (processed)
    └── <deal-slug>.md     # Archive of completed handover
```

## Gate System

Each handover progresses through configurable gates. Default sequence:

| Gate | Name | Criteria | Sign-off From |
|------|------|----------|---------------|
| G0 | Deal Scoped | PO/POC signed, PM assigned, client confirmed, product identified | Sales Manager |
| G1 | Charter Signed | Project Charter signed, budget approved, objectives defined, dates set | Executive |
| G2 | Kick-off Complete | Internal + external kick-off done, timeline submitted, tasks broken down, risks initialized | Project Manager |
| G3 | Funding Cleared | Downpayment/deposit received, procurement unblocked, timeline confirmed | Finance |

Gates are configurable via `HANDOVER_GATES` env var. Customize the sequence for your company's approval process.

## Handover Page Template

When creating a handover, the CRM agent should populate this structure:

```markdown
---
title: "Customer Name — Project Name"
type: handover
status: pending
source_deal: "deals/<deal-slug>"
source: "CRM — <owner>"
created: YYYY-MM-DD
handover_target: <Project Manager>
gate: 0
gate_status: gated
---

# Project Handover: Customer Name — Project Name

> **Handed over by:** <CRM Owner> (via <CRM Profile>)
> **Pick up by:** <Project Manager>
> **Target:** <brief target description>

---

## Customer Information

| Field | Value |
|-------|-------|
| **Customer** | Customer Name |
| **End Client** | End Client Name |
| **Contact Person** | Name |
| **Contact Email** | email@example.com |
| **Contact Phone** | Phone Number |

## Deal & PO Details

| Field | Value |
|-------|-------|
| **PO Number** | PO-XXXXX |
| **PO Date** | YYYY-MM-DD |
| **PO Amount** | $X,XXX.XX |
| **Currency** | USD |
| **Payment Terms** | Per PO |

## Scope of Work

<Detailed scope description>

## Deliverables

- [ ] Deliverable 1
- [ ] Deliverable 2

## Timeline

| Milestone | Target Date |
|-----------|-------------|
| Quotation issued | YYYY-MM-DD |
| PO received | YYYY-MM-DD |
| Setup completion | YYYY-MM-DD |
| Handover to customer | YYYY-MM-DD |

## References

| Item | Path |
|------|------|
| PO Document | `~/brain/deals/references/<filename>.pdf` |
| Quote Document | `~/brain/deals/references/<filename>.pdf` |
| Email Thread | <description> |

## Next Steps for Project Manager

- [ ] Acknowledge receipt
- [ ] Review scope and contact customer
- [ ] Create project in `~/brain/projects/active_projects/`
- [ ] Progress gates (G0→G1→G2→G3)
- [ ] Move to `~/brain/handovers/completed/` when done
```

## Scripts

### `create-handover.py`

Creates a handover page from a won deal. Called by the CRM agent.

```bash
python3 ~/.hermes/scripts/create-handover.py \
  --deal "deals/acme-foo" \
  --customer "Acme Corp" \
  --scope "Implementation of widget system" \
  --po-number "PO-12345" \
  --amount 15000 \
  --currency USD \
  --contact "John Doe <john@acme.com>"
```

### `process-handover.py`

Processes a pending handover — reviews, progresses gates, creates project, moves to completed.

```bash
# Review handover
python3 ~/.hermes/scripts/process-handover.py --review "deals/acme-foo"

# Progress a gate
python3 ~/.hermes/scripts/process-handover.py --gate 1 "deals/acme-foo"

# Complete handover (creates project, moves to completed)
python3 ~/.hermes/scripts/process-handover.py --complete "deals/acme-foo"
```

### `sync-deal-activity.py`

Bridges email activity into deal/project pages. Runs as a cron job after email collection.

```bash
# Dry run — preview what would change
python3 ~/.hermes/scripts/sync-deal-activity.py --dry-run

# Live run — update deal/project pages
python3 ~/.hermes/scripts/sync-deal-activity.py

# Live run + Slack DM owners about risks
python3 ~/.hermes/scripts/sync-deal-activity.py --dm
```

## Cron Jobs

### Handover Check (every 15 minutes)

```bash
hermes cron create \
  --name "handover-detection" \
  --schedule "*/15 * * * *" \
  --script ~/.hermes/scripts/create-handover.py \
  --no-agent \
  --deliver <HANDOVER_NOTIFY_CHANNEL>
```

### Activity Sync (hourly, weekdays)

```bash
hermes cron create \
  --name "deal-project-activity-sync" \
  --schedule "35 8-19 * * 1-5" \
  --script ~/.hermes/scripts/sync-deal-activity.py \
  --no-agent \
  --deliver local
```

## Pitfalls

- ❌ **Don't skip the handover page** — the handover page is the single source of truth for the project kickoff. Without it, the project manager has no context.
- ❌ **Don't skip gates** — each gate must be explicitly approved before moving to the next. Skipping gates causes scope creep and budget overruns.
- ❌ **Don't forget to notify** — the project manager needs to know a handover is waiting. Always notify via `HANDOVER_NOTIFY_CHANNEL`.
- ❌ **Don't create duplicate projects** — always check `~/brain/projects/active_projects/` before creating a new project.
- ❌ **Don't skip compliance validation** — run the brain compliance validator on every handover page and project page created.

## Related Skills

- `brain-compliance` — Validate brain pages after creation
- `department-scrum` — Daily scrum for project teams
- `brain-link-campaign` — Link new pages to prevent orphans
- `gbrain-operations` — Core gbrain read/write operations