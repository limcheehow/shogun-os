---
name: dead-slow-stock-detector
description: "Use to detect dead and slow-moving stock — SKUs with more than 8 months of inventory cover or no sales movement in 180+ days. Ranks by capital tied up and generates an action-to-flush recommendation per SKU."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, dead-stock, slow-stock, capital, liquidation, flush, sku]
    category: procurement
    related_skills: [inventory-item-management, reorder-alert-watchdog, weekly-inventory-valuation]
---

# Dead & Slow Stock Detector

## Overview

Scans all inventory items in the `procurement` gbrain source to identify **dead stock** (zero sales movement in > 180 days) and **slow-moving stock** (> 8 months of inventory cover based on 90-day average sales velocity). Items are ranked in descending order by total capital tied up (`current_stock × unit_cost`) and each receives an action-to-flush recommendation: *25% Promo Discount*, *Vendor Clearance Return*, *Bundle Promo with Top SKU*, or *Scrap / Write-off*. The output is posted to `#procurement` and saved to `procurement/reports/` for management review.

## When to Use

- Monthly or ad-hoc capital recovery review
- Executive asks: "Which items are dead stock and how much capital is locked up?"
- Dashboard Dead & Slow Stock Capital KPI needs refreshing
- User says: "Run the dead stock scan", "Show me slow-moving inventory", "What stock should we flush?"

Don't use for: active reorder alerts — see [reorder-alert-watchdog](../reorder-alert-watchdog/SKILL.md); inventory valuation totals — see [weekly-inventory-valuation](../weekly-inventory-valuation/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- MCP / tools: `proc_list_inventory`, `proc_get_item`
- gbrain `procurement` source (item pages with `last_movement_date` frontmatter)
- Comm layer: `skills/department-scrum/scripts/comm/` for Slack delivery

## Detection Logic

| Classification | Criteria |
|---------------|----------|
| **Dead Stock** | `days_since_last_movement > 180` OR `avg_monthly_sales_velocity = 0` |
| **Slow-Moving Stock** | `months_of_cover > 8` (cover = `current_stock / avg_monthly_velocity_90d`) |

`months_of_cover` is calculated as: `current_stock ÷ avg_monthly_sales_velocity_90d`. If velocity is 0, cover is treated as ∞ (dead stock).

## Action-to-Flush Recommendation Rules

| Condition | Recommendation |
|-----------|---------------|
| Days since last movement > 365 | *Scrap / Write-off* |
| Has preferred vendor AND is a standard catalog item | *Vendor Clearance Return* |
| High-volume category with complementary top SKU | *Bundle Promo with Top SKU* |
| Default (slow-moving, < 365 days stale) | *25% Promo Discount* |

## Workflows

### "Run dead & slow stock detection scan"

1. Call `proc_list_inventory()` to retrieve all items.
2. For each item: retrieve `last_movement_date` and compute `days_since_last_movement = today - last_movement_date`.
3. Compute `avg_monthly_velocity_90d` from the item's 90-day movement history (query `procurement/stock-movements/` for the SKU).
4. Classify each item:
   - Dead: `days_since_movement > 180` OR `avg_velocity = 0`
   - Slow: `months_of_cover > 8` AND not already dead
5. Rank by `current_stock × unit_cost` descending.
6. Apply action-to-flush recommendation per item using the rules above.
7. Format as capital ranking table:
   ```
   💀 DEAD & SLOW STOCK REPORT — <date>
   Total Capital at Risk: MYR <amount>

   # | SKU | Item Name | Category | Qty | Days Since Movement | Months Cover | Tied-Up Value (MYR) | Action
   1 | SKU-001 | Widget A | IT Hardware | 240 | 320 days | ∞ | MYR 48,000 | Scrap / Write-off
   2 | SKU-042 | Cable B | Consumables | 1,200 | 90 days | 18 months | MYR 12,000 | 25% Promo Discount
   ...
   ```
8. Save report to `procurement/reports/dead-slow-stock-<YYYY-MM-DD>.md`.
9. Post summary to `#procurement` with top 5 by capital value and link to full report.

### "Get action recommendation for a single SKU"

1. Call `proc_get_item(sku=SKU)` to retrieve stock and cost.
2. Compute days since last movement and monthly velocity.
3. Apply recommendation rules and return classification + recommended action.

## Common Pitfalls

1. **Velocity calculation on new items** — items with < 90 days of history should be excluded from slow-stock scoring; flag them as "Insufficient Data" instead.
2. **Seasonal stock misclassification** — items with seasonal demand (e.g., annual campaigns) may appear slow between seasons; check category metadata before recommending write-off.
3. **Cover formula denominator of zero** — when `avg_velocity = 0`, treat cover as ∞ (dead stock) and do not attempt division.
4. **Cost vs. selling price confusion** — tie-up value uses `unit_cost` (what we paid), not selling price; do not mix the two in the ranking table.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/dead-slow-stock-detector/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] Scan returns correct classification for a test SKU with known last_movement_date
- [ ] Capital ranking table sorts correctly by descending tied-up value
- [ ] Action recommendations follow the rules table above
- [ ] Report saved to `procurement/reports/dead-slow-stock-<date>.md`
