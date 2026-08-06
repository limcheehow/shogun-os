---
name: dashboard-snapshot-writer
description: "Use when refreshing the Procurement dashboard with live system data. Calls proc_* MCP tools, computes the 5-tab payload, and writes JSON snapshots to <dept>/snapshots/*.json gbrain pages. Idempotent + empty-brain-safe. Standalone script: scripts/write_snapshots.py. Slash trigger: /refresh-procurement-dashboard."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, dashboard, snapshot, gbrain, refresh]
    category: procurement
    related_skills: [inventory-valuation-report, dead-slow-stock-detector, reorder-alert-report, stock-movement-audit, accounting-bridge-sync]
---

# Dashboard Snapshot Writer (Procurement)

## Overview

Closes the live-data gap for the Procurement dashboard (Concern 5 of
`TO-DO-PD.md`). Reads procurement system data through the existing `proc_*` MCP
tools, computes the full 5-tab payload, and writes machine-readable JSON into
five `<dept>/snapshots/*.json` gbrain pages. The dashboard backend
(`server/dashboard.py:_run_procurement_aggregation`) already reads these slugs
(see `recipes/DASHBOARD_SNAPSHOT_CONTRACT.md`) — no backend change is needed
for live data to flow. When snapshots are absent or empty, the dashboard falls
back to `examples/procurement-mock.json` (unchanged graceful degradation).

## When to Use

- Daily 7am cron (before the 9am scrum) refreshes all 5 snapshot pages.
- On-demand via `/refresh-procurement-dashboard` slash trigger.
- Manually: `python skills/procurement/dashboard-snapshot-writer/scripts/write_snapshots.py`
  (supports `--dry-run` to print payloads without writing).

## Prerequisites

- Owning profile: `procurement-manager`
- Procurement agent gateway must be **up** for MCP tools to respond. If the
  gateway is down, the skill stays on mock fallback (acceptable degradation —
  it does not crash; it writes empty/zero snapshots).
- MCP tools: `proc_list_inventory`, `proc_get_item`, `proc_list_purchase_orders`,
  `proc_list_vendors`, `proc_check_reorder_alerts`, `proc_list_stock_movements`
  (built in Phase 2.5.2 of `TO-DO-PD.md`).
- For the accounting-bridge snapshot: env vars `ENABLE_ACCOUNTING_SYNC`,
  `ACCT_PROVIDER`; `procurement/reports/gl-sync-*.md` for last_sync;
  `acct_get_balance_sheet` probe for `connected`.

## Snapshot Slugs Written

Exactly the contract in `recipes/DASHBOARD_SNAPSHOT_CONTRACT.md`:

| Slug | Tab |
|---|---|
| `procurement/snapshots/inventory.json` | 1 (Pulse) + 2 (Inventory Catalog) |
| `procurement/snapshots/purchase-orders.json` | 4 (PO & Vendors) |
| `procurement/snapshots/vendors.json` | 4 |
| `procurement/snapshots/stock-movements.json` | 3 (Stock Movement Audit) |
| `procurement/snapshots/accounting-bridge.json` | 5 (Accounting Bridge) |

ABC Pareto is **not** written here — it is computed client-side from
`sku_catalog` in the UI (Phase 1).

## Computation Notes

- `total_inventory_valuation = Σ current_qty × unit_cost` (per Concern 7 of
  `TO-DO-PD.md`, `unit_cost` is the sole price field; no `selling_price`).
- `sku_catalog[]` field mapping from `proc_list_inventory` raw frontmatter:
  `current_stock → current_qty`, `reorder_point → safety_reorder_point`,
  `location_id → location_bin`, `name → item_name`. **No `selling_price`**.
- Dead/slow stock: `>180d no movement OR >8 months cover` (reuse logic from
  `dead-slow-stock-detector`), valued at `unit_cost`.
- `executive_approval_queue[]`: rows with `total_amount > 10000` from
  `proc_list_purchase_orders`, status `Pending Executive Approval` / `Approved`
  / `Rejected` / `Clarification Requested` as recorded.
- `bridge_status` is **assembled in the writer** (Choice A, Concern 6): `enabled`
  ← `ENABLE_ACCOUNTING_SYNC`; `provider` ← `ACCT_PROVIDER`; `last_sync` ←
  newest `procurement/reports/gl-sync-*.md` frontmatter timestamp;
  `connected` ← probe `acct_get_balance_sheet` (success → true). No dedicated
  tool is built for this — status is read-once at snapshot time.

## Idempotency & Empty-Brain Safety

Every run overwrites each snapshot page with a full recomputed payload. An
empty brain (no items / POs / movements) writes snapshots with zeros and empty
arrays and exits 0 — it never crashes or writes partial data (Karpathy: empty
input → zeros, exit 0).