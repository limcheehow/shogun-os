---
name: weekly-inventory-valuation
description: "Use when computing total inventory valuation — sum(current_stock x unit_cost) across all SKUs. Optionally compares to the accounting GL balance if ENABLE_ACCOUNTING_SYNC=true and writes a discrepancy report."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, valuation, gl, accounting, reconciliation, weekly, report]
    category: procurement
    related_skills: [inventory-valuation-report, accounting-bridge-sync, dead-slow-stock-detector]
---

# Weekly Inventory Valuation

## Overview

Computes total inventory valuation by summing `current_stock × unit_cost` across all active SKUs in the procurement gbrain source. When `ENABLE_ACCOUNTING_SYNC=true`, the result is compared against the GL inventory account balance retrieved via `acct_get_balance_sheet`, and any variance above the tolerance threshold is written as a discrepancy report to `procurement/reports/`. Runs automatically every Friday at 5PM via the `{profile}-inventory-valuation` cron job.

## When to Use

- Friday end-of-week inventory valuation sweep
- CFO or CPO requests current inventory value with GL reconciliation
- Monthly period-end close requires inventory balance confirmation
- User says: "What is our total inventory value?", "Run the inventory valuation", "Check GL vs. stock variance"

Don't use for: reorder alerts — see [reorder-alert-watchdog](../reorder-alert-watchdog/SKILL.md); dead/slow stock reporting — see [dead-slow-stock-detector](../dead-slow-stock-detector/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- MCP / tools: `proc_list_inventory` (brain inventory provider); `acct_get_balance_sheet` (if `ENABLE_ACCOUNTING_SYNC=true`)
- gbrain `procurement` source
- Environment: `ENABLE_ACCOUNTING_SYNC` env flag

## Workflows

### "Compute total inventory valuation"

1. Call `proc_list_inventory()` to retrieve all active items.
2. Compute: `total_valuation = sum(item.current_stock × item.unit_cost for each item)`.
3. Format by category breakdown:
   ```
   📦 INVENTORY VALUATION — <date>
   Total Active SKUs: <N>
   Total Inventory Value: MYR <amount>

   By Category:
   - IT Hardware:       MYR <amount> (<N> SKUs)
   - Office Supplies:   MYR <amount> (<N> SKUs)
   - Consumables:       MYR <amount> (<N> SKUs)
   - Spare Parts:       MYR <amount> (<N> SKUs)
   ```

### "GL reconciliation (ENABLE_ACCOUNTING_SYNC=true)"

1. Complete the valuation computation above.
2. Call `acct_get_balance_sheet(as_of_date=today)` to retrieve the GL Inventory account balance.
3. Compute variance: `variance = GL_inventory_balance - total_stock_valuation`.
4. If `abs(variance) > tolerance_threshold` (default: MYR 500 or 1% of total, whichever is greater):
   - Write discrepancy report to `procurement/reports/valuation-discrepancy-<YYYY-MM-DD>.md`.
   - Flag the variance to `#procurement` with recommended investigation action.
5. If variance is within tolerance: confirm reconciliation as passed.

## Common Pitfalls

1. **Inactive SKU inclusion** — exclude items with `status: inactive` or `current_stock: 0` from the valuation total; they inflate the GL comparison.
2. **Currency mismatch** — all unit costs must be in MYR before summing; if a vendor invoices in USD, the cost on the item page must already be MYR-converted.
3. **GL account selection** — confirm the correct GL account code for Inventory Asset before comparing; a misconfigured GL account ID produces false variance flags.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/weekly-inventory-valuation/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] `proc_list_inventory` returns items for valuation computation
- [ ] With `ENABLE_ACCOUNTING_SYNC=false`: valuation report prints and exits 0
- [ ] With `ENABLE_ACCOUNTING_SYNC=true`: GL comparison runs and variance is computed correctly
