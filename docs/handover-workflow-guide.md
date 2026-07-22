# Handover Workflow Guide

> **Sales-to-Project handover lifecycle** — from won deal to active project.

## Overview

The handover workflow bridges the gap between your CRM agent (who closes deals) and your project agent (who delivers them). It provides:

1. **Structured handover pages** — standardized format with customer info, scope, PO details
2. **Gate-based project initiation** — 4 sequential gates ensure nothing is missed
3. **Activity sync** — ongoing email→project timeline bridging
4. **Risk detection** — automated flagging of stalled deals, overdue projects

## Lifecycle

```
Deal Won (CRM)
  │
  ▼ Step 1: Create Handover
  create-handover.py --deal "deals/acme-foo" --customer "Acme Corp" --scope "..." --po-number "PO-12345"
  │
  ▼ Step 2: Review Handover
  process-handover.py --review "deals/acme-foo"
  │
  ▼ Step 3: Progress Gates
  process-handover.py --gate 1 "deals/acme-foo"   # G0 → G1
  process-handover.py --gate 2 "deals/acme-foo"   # G1 → G2
  process-handover.py --gate 3 "deals/acme-foo"   # G2 → G3
  │
  ▼ Step 4: Complete Handover
  process-handover.py --complete "deals/acme-foo"
  │
  ▼ Ongoing: Activity Sync
  sync-deal-activity.py   # Cron job, bridges emails → timeline
```

## The 4 Gates

| Gate | Name | Criteria | Sign-off From |
|------|------|----------|---------------|
| **G0** | Deal Scoped | PO/POC signed, PM assigned, client confirmed, product identified | Sales Manager |
| **G1** | Charter Signed | Project Charter signed, budget approved, objectives defined, dates set | Executive |
| **G2** | Kick-off Complete | Internal + external kick-off done, timeline submitted, tasks broken down, risks initialized | Project Manager |
| **G3** | Funding Cleared | Downpayment/deposit received, procurement unblocked, timeline confirmed | Finance |

Gates are configurable via `HANDOVER_GATES` env var.

## Directory Structure

```
~/brain/
├── handovers/
│   ├── _schema.json           # Schema (auto-generated)
│   ├── pending/               # Handovers waiting for processing
│   │   └── <deal>-handover.md
│   ├── pending_prompt/        # Handovers awaiting clarification
│   │   └── _schema.json
│   └── completed/             # Processed handovers (archive)
│       └── <deal>-handover.md
├── deals/                     # Deal pages (CRM)
│   └── <deal>.md
└── projects/
    └── active_projects/       # Project pages (created on handover completion)
        └── PRJ-<project>.md
```

## Environment Variables

| Env Var | Default | Purpose |
|---------|---------|---------|
| `BRAIN_DIR` | `~/brain` | Brain root |
| `HANDOVER_SALES_ROLE` | `CRM Manager` | Who creates handovers |
| `HANDOVER_PROJECT_ROLE` | `Project Manager` | Who processes handovers |
| `HANDOVER_NOTIFY_CHANNEL` | (empty) | Where to notify new handovers |
| `HANDOVER_GATES` | `G0:Deal Scoped,G1:Charter Signed,G2:Kick-off Complete,G3:Funding Cleared` | Gate sequence |
| `LOOKBACK_HOURS` | `3` | Email scan window (hours) |
| `STALL_DAYS` | `7` | Deal inactivity threshold |
| `COLD_DAYS` | `14` | Qualified deal inactivity threshold |
| `INTERNAL_EMAIL_DOMAINS` | `example.com` | Comma-separated internal domains |
| `OWNER_SLACK_MAP` | (path) | JSON file mapping owner names to Slack IDs |

## Scripts Reference

### `create-handover.py`

Creates a handover page from a won deal. Call this when a deal reaches "Won" stage.

```bash
python3 create-handover.py \
  --deal "deals/acme-foo" \
  --customer "Acme Corp" \
  --scope "Implementation of CCTV system with 12 cameras" \
  --po-number "PO-2026-0042" \
  --amount 25000.00 \
  --currency USD \
  --contact "John Doe <john@acme.com>" \
  --end-client "Acme End Client" \
  --owner "Sales Rep Name" \
  --quote-ref "Q-2026-0042"
```

### `process-handover.py`

Processes a pending handover. Three modes:

```bash
# Review — see what's in the handover
python3 process-handover.py --review "deals/acme-foo"

# Progress a gate — move to next gate
python3 process-handover.py --gate 1 "deals/acme-foo"

# Complete — move to completed, create project
python3 process-handover.py --complete "deals/acme-foo"
```

### `sync-deal-activity.py`

Bridges email activity into deal/project pages. Runs as a cron job:

```bash
# Dry run
python3 sync-deal-activity.py --dry-run

# Live run (adds timeline entries, detects risks)
python3 sync-deal-activity.py

# Live run with Slack DMs to owners
python3 sync-deal-activity.py --dm
```

## Related Skills

- `skills/crm/handover-workflow` — This skill
- `skills/department-scrum` — Daily scrum for project teams
- `skills/brain-compliance` — Validate brain pages after creation
- `skills/company-workflow` — General gate sequence for feature/bug work