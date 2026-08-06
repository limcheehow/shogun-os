---
name: reorder-alert-watchdog
description: "Use when checking for items at or below their reorder threshold and drafting Purchase Orders for the preferred vendor. Posts a reorder alert summary to #procurement."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, reorder, po, watchdog, alert, vendor]
    category: procurement
    related_skills: [inventory-item-management, dead-slow-stock-detector, weekly-inventory-valuation]
---

# Reorder Alert Watchdog

## Overview

Runs `proc_check_reorder_alerts` to scan all inventory items whose current stock is at or below their configured reorder point. For each alert, the skill groups items by preferred vendor, drafts PO line items, and posts a prioritised reorder summary to the `#procurement` Slack channel. Critical items (stock at or below safety stock) are flagged separately for immediate action. Runs automatically Mon–Fri at 8AM via the `{profile}-reorder-watchdog` cron job.

## When to Use

- Daily/weekly stock health check is triggered by cron
- User asks: "Check stock levels and flag anything that needs reordering", "Run the reorder watchdog"
- A procurement executive wants a reorder PO draft for low-stock items

Don't use for: dead/slow stock detection — see [dead-slow-stock-detector](../dead-slow-stock-detector/SKILL.md); full inventory valuation — see [weekly-inventory-valuation](../weekly-inventory-valuation/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- MCP / tools: `proc_check_reorder_alerts`, `proc_create_purchase_order`, `proc_list_vendors`
- gbrain `procurement` source
- Comm layer: `skills/department-scrum/scripts/comm/` for Slack delivery

## Workflows

### "Run reorder alert watchdog"

1. Call `proc_check_reorder_alerts()` with no filters to get all alerts.
2. If `alerts` is empty, post "✅ All stock levels healthy — no reorders required" to `#procurement` and exit.
3. Separate alerts into `critical` (stock ≤ safety_stock) and `warning` (stock ≤ reorder_point) tiers.
4. Group by `preferred_vendor_id`.
5. For each vendor group: call `proc_create_purchase_order` in draft mode with line items (SKU → recommended_order_qty).
6. Post reorder summary to `#procurement` in format:
   ```
   🚨 REORDER ALERT — <date>
   Critical (stock ≤ safety): <N> SKUs
   Warning (stock ≤ reorder point): <N> SKUs

   Vendor: <Vendor Name>
   - SKU-XXX — <Item Name>: Order <qty> units (Current: <stock>)
   Draft PO: <PO number>
   ```
7. Save alert report to `procurement/reports/reorder-<YYYY-MM-DD>.md`.

## Common Pitfalls

1. **Preferred vendor missing** — if an item has no `preferred_vendor_id`, flag it for manual PO assignment; do not auto-create a PO without a vendor.
2. **Duplicate PO draft** — check if a draft PO for the same vendor already exists today before creating a new one to avoid duplicate orders.
3. **Critical vs. warning confusion** — critical items (≤ safety stock) require same-day escalation; do not treat them the same as warning-level alerts.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/reorder-alert-watchdog/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] `proc_check_reorder_alerts` returns a valid response (or empty alerts list)
- [ ] Cron `{profile}-reorder-watchdog` fires Mon–Fri at 8AM and posts to `#procurement`
