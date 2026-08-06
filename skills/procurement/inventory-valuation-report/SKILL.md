---
name: inventory-valuation-report
description: "Use when generating a full inventory valuation report — total stock value by SKU and category, with optional GL comparison. Standalone script: scripts/inventory_valuation.py."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, valuation, report, gl, accounting, category]
    category: procurement
    related_skills: [weekly-inventory-valuation, accounting-bridge-sync, dead-slow-stock-detector]
---

# Inventory Valuation Report

## Overview

Generates a detailed inventory valuation report by reading all inventory item pages from the gbrain `procurement` source and computing `sum(current_stock × unit_cost)`. Output includes a per-SKU valuation table and a category-level breakdown. When `ENABLE_ACCOUNTING_SYNC=true`, the total is compared against the GL Inventory Asset balance via `acct_get_balance_sheet` and any variance is flagged. The standalone script `scripts/inventory_valuation.py` can be run directly or invoked by the weekly cron. Report is saved to `procurement/reports/` and delivered via the `department-scrum` comm layer.

## When to Use

- Weekly Friday valuation cron triggers the report
- CPO or CFO requests a current inventory value snapshot
- Period-end close requires a confirmed inventory balance
- User says: "Generate the inventory valuation report", "What is our stock value?", "/inventory-valuation"

Don't use for: reorder alerts — see [reorder-alert-watchdog](../reorder-alert-watchdog/SKILL.md); dead stock analysis — see [dead-slow-stock-detector](../dead-slow-stock-detector/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- Script: `skills/procurement/inventory-valuation-report/scripts/inventory_valuation.py`
- MCP / tools: `proc_list_inventory`; `acct_get_balance_sheet` (if `ENABLE_ACCOUNTING_SYNC=true`)
- gbrain `procurement` source
- Comm layer: `skills/department-scrum/scripts/comm/` for Slack delivery

## Output Format

```
📦 INVENTORY VALUATION REPORT (<date>)
Prepared by: Kura (Procurement Manager)

Total Active SKUs: <N>
Total Inventory Value: MYR <amount>

By Category:
---------------------------------------------------
IT Hardware    | <N> SKUs | MYR <amount> | <pct>%
Consumables    | <N> SKUs | MYR <amount> | <pct>%
Office Suppl.  | <N> SKUs | MYR <amount> | <pct>%
Spare Parts    | <N> SKUs | MYR <amount> | <pct>%
---------------------------------------------------

Top 10 SKUs by Value:
# | SKU       | Item Name     | Qty | Unit Cost | Total Value
1 | SKU-001   | Widget A      | 500 | MYR 96.00 | MYR 48,000
...

GL Reconciliation: [PASSED | VARIANCE MYR <amount>]
```

## Workflows

### Generate Inventory Valuation Report

1. Run `inventory_valuation.py` (or invoke steps manually) — done when: all items retrieved and valuation computed.
2. Format output per the template above — done when: report renders cleanly.
3. If `ENABLE_ACCOUNTING_SYNC=true`: compare to GL and flag variance — done when: GL comparison result is stated.
4. Save report to `procurement/reports/valuation-<YYYY-MM-DD>.md` — done when: archive file is written.
5. Deliver via `department-scrum` comm layer — done when: message confirmed sent to `#procurement`.

## Common Pitfalls

1. **Empty inventory source** — if gbrain has no procurement pages yet, the script must print a header and "No inventory items found" then exit 0 (never crash).
2. **Inactive item inclusion** — skip items with `status: inactive`; they should not contribute to the valuation total.
3. **Rounding** — use 2 decimal places for unit cost and 0 decimal places for total value when formatting MYR amounts in the report.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/inventory-valuation-report/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] `python skills/procurement/inventory-valuation-report/scripts/inventory_valuation.py` prints valuation table and exits 0 with empty brain
- [ ] Report saved to `procurement/reports/valuation-<date>.md` in gbrain
