---
name: dashboard-snapshot-writer
description: "Use when refreshing the Finance dashboard with live system data. Calls acct_* MCP tools, computes the 5-tab payload, and writes JSON snapshots to finance/snapshots/*.json gbrain pages. Idempotent + empty-brain-safe. Standalone script: scripts/write_snapshots.py. Slash trigger: /refresh-finance-dashboard."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, dashboard, snapshot, gbrain, refresh]
    category: finance
    related_skills: [cash-runway-forecasting, ar-credit-control, bva-variance-analysis, revenue-concentration-audit, tax-sst-compliance, period-end-close-checklist, malaysia-contractor-cp58-wht]
---

# Dashboard Snapshot Writer (Finance)

## Overview

Closes the live-data gap for the Finance dashboard (Concern 5 of
`TO-DO-PD.md` — same systemic mismatch as Procurement). Reads finance system
data through the existing `acct_*` MCP tools, computes the full 5-tab payload,
and writes machine-readable JSON into seven `finance/snapshots/*.json` gbrain
pages. The dashboard backend (`server/dashboard.py:_run_finance_aggregation`)
already reads these slugs (see `recipes/DASHBOARD_SNAPSHOT_CONTRACT.md`) — no
backend change is needed for live data to flow. When snapshots are absent or
empty, the dashboard falls back to `examples/finance-budget.json` (unchanged
graceful degradation).

## When to Use

- Daily 7am cron refreshes all 7 snapshot pages.
- On-demand via `/refresh-finance-dashboard` slash trigger.
- Manually: `python skills/finance/dashboard-snapshot-writer/scripts/write_snapshots.py`
  (supports `--dry-run` to print payloads without writing).

## Prerequisites

- Owning profile: `finance-manager` (Koku persona).
- Finance agent gateway must be **up** for `acct_*` MCP tools to respond. If
  the gateway is down, the skill stays on mock fallback (acceptable
  degradation — it writes empty/zero snapshots, no crash).
- MCP tools: `acct_get_balance_sheet`, `acct_get_profit_loss`,
  `acct_get_aging_report`, `acct_list_sales_invoices`, `acct_list_purchase_bills`,
  `acct_list_contacts`. Plus `finance/budget.json` for BvA.

## Snapshot Slugs Written

Exactly the contract in `recipes/DASHBOARD_SNAPSHOT_CONTRACT.md`:

| Slug | Tab |
|---|---|
| `finance/snapshots/cash.json` | 1 (Cash & Treasury) |
| `finance/snapshots/pl.json` | 1 / 3 (P&L) |
| `finance/snapshots/concentration.json` | 3 (Revenue Concentration) |
| `finance/snapshots/bva.json` | 3 (Budget vs Actual) |
| `finance/snapshots/ar.json` | 4 (AR & Dunning) |
| `finance/snapshots/ap.json` | 4 (AP & Bills) |
| `finance/snapshots/compliance.json` | 5 (Compliance) |

## Computation Notes

- Reuses logic from the 22 finance skills:
  - Cash runway from `bank-payment-reconciliation` + `cash-runway-forecasting`.
  - AR aging (0-30 / 31-60 / 61-90 / 90+) from `ar-credit-control`.
  - BvA (department-level variance vs budget) from `bva-variance-analysis`.
  - Revenue concentration (>20% alert) from `revenue-concentration-audit`.
  - Compliance (close checklist, SST, CP58/WHT) from `tax-sst-compliance` +
    `period-end-close-checklist` + `malaysia-contractor-cp58-wht`.
- Budget baseline read from `finance/budget.json`.

## Idempotency & Empty-Brain Safety

Every run overwrites each snapshot page with a full recomputed payload. An
empty brain (no invoices / contacts / bills) writes snapshots with zeros and
empty arrays and exits 0 — it never crashes or writes partial data (Karpathy:
empty input → zeros, exit 0).