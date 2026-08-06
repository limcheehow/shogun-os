---
name: reorder-alert-report
description: "Use when generating a formatted reorder alert report listing all SKUs at or below their reorder threshold, with recommended order quantities and preferred vendor. Standalone script: scripts/reorder_alerts.py."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, reorder, alert, report, vendor, po]
    category: procurement
    related_skills: [reorder-alert-watchdog, inventory-valuation-report, procurement-provider]
---

# Reorder Alert Report

## Overview

Generates a formatted low-stock reorder alert report by calling `proc_check_reorder_alerts` against the brain inventory provider. The report lists all items at or below their reorder point, sorted by severity (critical first), with recommended order quantity and preferred vendor per SKU. The standalone script `scripts/reorder_alerts.py` can be run directly or invoked by the Mon–Fri 8AM cron. Output is saved to `procurement/reports/` and posted to `#procurement` via the `department-scrum` comm layer.

## When to Use

- Mon–Fri 8AM reorder watchdog cron triggers the report
- Procurement executive wants a current low-stock list
- User says: "Generate the reorder alert report", "Show me items that need restocking", "/reorder-report"

Don't use for: full inventory valuation — see [inventory-valuation-report](../inventory-valuation-report/SKILL.md); dead stock — see [dead-slow-stock-detector](../dead-slow-stock-detector/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- Script: `skills/procurement/reorder-alert-report/scripts/reorder_alerts.py`
- MCP / tools: `proc_check_reorder_alerts`, `proc_list_vendors`
- gbrain `procurement` source
- Comm layer: `skills/department-scrum/scripts/comm/` for Slack delivery

## Output Format

```
🚨 REORDER ALERT REPORT (<date>)
Prepared by: Kura (Procurement Manager)

Status: <N> items require reordering
  Critical (stock ≤ safety stock): <N> SKUs
  Warning (stock ≤ reorder point): <N> SKUs

Critical Items:
SKU       | Item Name     | Qty | Reorder Pt | Rec. Order | Vendor
---------------------------------------------------------------------
SKU-001   | Widget A      | 5   | 50         | 200 units  | Vendor X
...

Warning Items:
SKU       | Item Name     | Qty | Reorder Pt | Rec. Order | Vendor
---------------------------------------------------------------------
SKU-042   | Cable B       | 120 | 150        | 100 units  | Vendor Y
...
```

## Workflows

### Generate Reorder Alert Report

1. Run `reorder_alerts.py` (or invoke manually) — done when: `proc_check_reorder_alerts` returns response.
2. If no alerts: print "✅ No reorders needed — all stock levels healthy" and exit 0.
3. Format output per template above — done when: report renders cleanly by severity tier.
4. Save report to `procurement/reports/reorder-<YYYY-MM-DD>.md` — done when: archive file is written.
5. Post to `#procurement` — done when: message confirmed sent.

## Common Pitfalls

1. **Missing preferred vendor** — if an item has no `preferred_vendor_id`, show "TBC" in the Vendor column; do not crash.
2. **Zero recommended qty** — if `recommended_order_qty` from the API is 0, compute a fallback: `(reorder_point × 2) - current_stock`.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/reorder-alert-report/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] `python skills/procurement/reorder-alert-report/scripts/reorder_alerts.py` prints "No reorders needed" and exits 0 with empty brain
- [ ] Report saved to `procurement/reports/reorder-<date>.md` in gbrain
