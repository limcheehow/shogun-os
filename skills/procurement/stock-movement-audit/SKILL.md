---
name: stock-movement-audit
description: "Use when recording or auditing inventory movements — goods received, issued, adjusted, returned, or damaged. Appends immutable movement entries to procurement/stock-movements/ and updates running stock levels."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, stock, movement, audit, receive, issue, damage, adjustment]
    category: procurement
    related_skills: [inventory-item-management, location-binning, reorder-alert-watchdog]
---

# Stock Movement Audit

## Overview

Appends immutable stock movement log entries to `procurement/stock-movements/` in the gbrain procurement source. Each movement records the SKU, movement type (receive / issue / adjustment / return / damage), quantity, reference ID (PO number or support ticket), location ID, and actor. After logging, the skill calls `proc_update_stock` to atomically adjust the running stock level on the item's master page. This creates a complete, tamper-evident audit trail for inventory shrinkage control.

## When to Use

- Goods are received against a Purchase Order (GRN)
- Stock is issued to a department or project
- An inventory adjustment is made after a physical stock count
- Items are returned to vendor or from internal use
- Damaged or scrapped goods need to be logged
- User says: "Record a stock receipt for PO-XXX", "Log damage for SKU-YYY", "Adjust stock count for item Z"

Don't use for: creating or editing SKU master records — see [inventory-item-management](../inventory-item-management/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- MCP / tools: `proc_record_stock_movement`, `proc_update_stock`, `proc_get_item`
- gbrain `procurement` source (movement log at `procurement/stock-movements/`)

## Workflows

### "Record a stock receipt (GRN)"

1. Gather: PO number (reference_id), SKU list with quantities received, location/bin ID, date.
2. For each SKU: call `proc_get_item(sku=SKU)` to verify item exists.
3. Call `proc_record_stock_movement(sku=SKU, movement_type="receive", quantity=qty, reference_id=PO, location_id=loc, actor=agent_name)`.
4. Call `proc_update_stock(sku=SKU, delta=+qty)` to update running total.
5. Confirm receipt with movement ID and new stock level per SKU.

### "Record a stock issue"

1. Gather: requester/department, SKU, quantity, reference ticket/project ID, location.
2. Verify sufficient stock via `proc_get_item`; reject if stock would go negative.
3. Call `proc_record_stock_movement(movement_type="issue", ...)` then `proc_update_stock(delta=-qty)`.
4. Confirm issue with movement ID and remaining stock.

### "Log damage or scrap"

1. Gather: SKU, quantity damaged, location, note (reason for damage).
2. Call `proc_record_stock_movement(movement_type="damage", quantity=qty, note=reason, ...)`.
3. Call `proc_update_stock(delta=-qty)`.
4. Flag if cumulative damage for this SKU exceeds 2% of total stock in 30 days.

### "Audit recent movements"

1. Query gbrain for `procurement/stock-movements/` pages in the requested date range.
2. Format as table: Timestamp | SKU | Movement Type | Quantity | Reference ID | Location | Actor.
3. Highlight any damage/adjustment entries for management review.

## Common Pitfalls

1. **Double-counting receipts** — check if `reference_id` (PO number) has already been logged to avoid duplicate GRN entries.
2. **Negative stock** — always verify current stock before issuing; `proc_update_stock` does not block negative values at the API level.
3. **Missing reference_id** — always require a PO number or ticket reference for traceability; do not log movements with a blank reference.
4. **Batch receipts** — when a PO covers multiple SKUs, log each SKU as a separate movement entry (not a single combined entry).

## Verification Checklist

- [ ] Skill installed at `skills/procurement/stock-movement-audit/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] Movement entry appears at `procurement/stock-movements/<ISO-date>-<SKU>.md` after a test receipt
- [ ] Running stock on the item's master page is updated correctly after each movement
