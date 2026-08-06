---
name: accounting-bridge-sync
description: "Optional P2 bridge skill: documents how procurement events trigger accounting entries — PO-received to Purchase Bill, inventory cost sync, and GL valuation variance — via acct_* tools. Gated on ENABLE_ACCOUNTING_SYNC env flag."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, accounting, bridge, sync, gl, bill, cost, integration]
    category: procurement
    related_skills: [weekly-inventory-valuation, ap-vendor-management]
---

# Accounting Bridge Sync (P2)

## Overview

Documents the integration layer between `procurement-manager` and `finance-manager` for three trigger flows: (1) PO-received → Purchase Bill creation via `acct_*` tools, (2) inventory cost sync to GL, and (3) GL valuation variance flag. All flows are **gated on `ENABLE_ACCOUNTING_SYNC=true`** in the procurement profile's `.env`. The actual bridge implementation lives in `recipes/procurement/bridges/accounting_bridge.py`.

This is a **P2 (optional) skill** — the procurement inventory layer functions fully without it. Enable only when the organisation uses both Shogun OS procurement and a connected accounting system (Bukku / QuickBooks / Xero).

## When to Use

- `ENABLE_ACCOUNTING_SYNC=true` in the deployment environment
- A GRN (goods received note) against a PO needs to auto-generate a supplier bill in the accounting system
- Inventory revaluation needs to be synced to the GL Inventory Asset account
- User says: "Sync the PO receipt to accounting", "Create a supplier bill for PO-XXX", "Check GL inventory variance"

Don't activate if: the organisation uses procurement-only without an accounting integration — leave `ENABLE_ACCOUNTING_SYNC=false` and skip this skill.

## Prerequisites

- Owning profile: `procurement-manager`
- `ENABLE_ACCOUNTING_SYNC=true` in `.env`
- MCP / tools: `acct_list_purchase_bills`, `acct_create_purchase_bill`, `acct_get_balance_sheet` (from `finance-manager` accounting provider)
- `recipes/procurement/bridges/accounting_bridge.py` deployed
- Federated gbrain read enabled: `GBRAIN_FEDERATED_READ=true`

## Trigger Flows

### Flow 1: PO-Received → Purchase Bill

**Trigger:** Goods received against a PO (GRN recorded via `stock-movement-audit`)

1. Detect GRN movement entry with `movement_type=receive` in `proc_record_stock_movement` response.
2. If `ENABLE_ACCOUNTING_SYNC=true`: call `acct_create_purchase_bill` with:
   - `vendor_id` from PO preferred vendor
   - `bill_date = today`
   - `line_items` from PO line items × quantities received
3. Confirm bill created with bill number and total.

### Flow 2: Inventory Cost Sync

**Trigger:** Weekly inventory valuation run (Fri 5PM cron)

1. Retrieve total stock valuation from `weekly-inventory-valuation` output.
2. Call `acct_get_balance_sheet` to get current GL Inventory Asset balance.
3. Compute variance; if outside tolerance → flag for manual journal entry review.
4. Write sync status to `procurement/reports/gl-sync-<YYYY-MM-DD>.md`.

### Flow 3: GL Valuation Variance Flag

**Trigger:** Variance exceeds threshold during Flow 2

1. Post variance alert to `#procurement` and `#finance`:
   ```
   ⚠️ GL INVENTORY VARIANCE DETECTED — <date>
   Stock Valuation:  MYR <amount>
   GL Inventory GL:  MYR <amount>
   Variance:         MYR <amount> (<pct>%)
   Action: Review stock adjustments or GL journal for the period.
   ```
2. Save discrepancy report to `procurement/reports/valuation-discrepancy-<YYYY-MM-DD>.md`.

## Common Pitfalls

1. **Circular tool calls** — `procurement-manager` calls `acct_*` via federated MCP; ensure `GBRAIN_FEDERATED_READ=true` and the accounting MCP server is reachable from the procurement profile.
2. **Duplicate bills** — check if a bill for the same PO reference already exists via `acct_list_purchase_bills(reference=PO_number)` before creating.
3. **Disabled by default** — this skill is inactive when `ENABLE_ACCOUNTING_SYNC=false`; the profile will log a warning and skip all bridge flows gracefully.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/accounting-bridge-sync/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] `ENABLE_ACCOUNTING_SYNC=false` → all bridge flows skip with a clear log message
- [ ] `ENABLE_ACCOUNTING_SYNC=true` → `acct_create_purchase_bill` is called after a test GRN
- [ ] GL variance flag posts to both `#procurement` and `#finance`
