---
name: inventory-item-management
description: "Use when creating, reading, or updating inventory item brain pages — SKU master data, current stock levels, reorder points, preferred vendor, and bin/location assignment."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, sku, stock, reorder, vendor, location]
    category: procurement
    related_skills: [stock-movement-audit, reorder-alert-watchdog, location-binning, procurement-provider]
---

# Inventory Item Management

## Overview

Creates and maintains inventory item brain pages under `procurement/items/<SKU>.md` in the `procurement` gbrain source. Each page records SKU, item name, category, current stock, unit cost, reorder point, safety stock, preferred vendor ID, and bin/location ID as YAML frontmatter. The skill calls `proc_get_item` and `proc_update_stock` against the brain inventory provider and ensures frontmatter compliance via `brain_compliance_helper.py`.

## When to Use

- A new SKU is onboarded and its master record must be created in gbrain
- Stock level, reorder point, or vendor assignment on an existing SKU needs updating
- An inventory audit requires verifying SKU master data against physical stock count
- User says: "Add a new inventory item", "Update the reorder point for SKU-XXX", "Show me the master record for item X"

Don't use for: recording stock movements (receives/issues/damage) — see [stock-movement-audit](../stock-movement-audit/SKILL.md); generating reorder POs — see [reorder-alert-watchdog](../reorder-alert-watchdog/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- MCP / tools: `proc_get_item`, `proc_update_stock`, `proc_list_inventory` (brain inventory provider)
- gbrain `procurement` source (item pages at `procurement/items/`)
- `brain_compliance_helper.py` available in the profile's path

## Workflows

### "Create a new inventory item"

1. Gather from user: SKU, item name, category, unit cost, initial stock, reorder point, safety stock, preferred vendor name/ID, and location/bin ID.
2. Call `proc_get_item(sku=SKU)` to verify it does not already exist.
3. Create the gbrain page at `procurement/items/<SKU>.md` with the following frontmatter:
   ```yaml
   ---
   sku: <SKU>
   name: <Item Name>
   category: <Category>
   unit_cost: <cost>
   current_stock: <qty>
   reorder_point: <qty>
   safety_stock: <qty>
   preferred_vendor_id: <vendor-id>
   location_id: <location-id>
   last_movement_date: <YYYY-MM-DD>
   status: active
   ---
   ```
4. Confirm creation with SKU and current stock.

### "Update an existing inventory item"

1. Call `proc_get_item(sku=SKU)` to retrieve current record.
2. Apply changes to the relevant frontmatter fields.
3. Call `proc_update_stock` if stock quantity is changing.
4. Save updated page via `mcp_gbrain_save_page`.
5. Confirm the fields updated and new values.

### "List / search inventory items"

1. Call `proc_list_inventory` with optional `search`, `category`, or `below_reorder` filters.
2. Format output as table: SKU | Item Name | Category | Qty | Unit Cost | Reorder Point | Status.

## Common Pitfalls

1. **Duplicate SKU creation** — always call `proc_get_item` before creating; abort if item already exists.
2. **Stock vs. cost confusion** — `proc_update_stock` changes quantity only; unit cost is updated directly on the frontmatter page.
3. **Missing location_id** — every item must have a `location_id` for bin-to-item linking; prompt user if omitted.
4. **Orphaned pages** — use `brain_compliance_helper.py` to ensure all required frontmatter fields are present before saving.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/inventory-item-management/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] `proc_get_item` resolves correctly for a test SKU
- [ ] New item page appears at `procurement/items/<SKU>.md` in gbrain after creation
