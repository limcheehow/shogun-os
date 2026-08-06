---
name: location-binning
description: "Use when managing warehouse locations, storage bins, and shelf assignments for inventory items. Creates and updates procurement/locations/ pages and assigns items to bins."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [procurement, inventory, warehouse, bin, location, shelf, storage]
    category: procurement
    related_skills: [inventory-item-management, stock-movement-audit]
---

# Location & Bin Management

## Overview

Manages warehouse location and bin pages under `procurement/locations/<LOC-ID>.md` in the gbrain procurement source. Each location page records the location ID (e.g., `LOC-MAIN-A1`), display name, zone (Main Warehouse / Office Store Room / Edge Deployment), capacity, and current occupancy. The skill links items to locations via the `location_id` frontmatter field on inventory item pages, supporting bin-to-item and item-to-bin lookups.

## When to Use

- A new warehouse zone, bin, or shelf needs to be set up in gbrain
- An item is relocated to a different bin or shelf
- Capacity utilisation for a storage zone needs to be reported
- User says: "Create a new bin location", "Move SKU-XXX to shelf B2", "Show me the capacity of the main warehouse"

Don't use for: recording stock movements — see [stock-movement-audit](../stock-movement-audit/SKILL.md).

## Prerequisites

- Owning profile: `procurement-manager`
- MCP / tools: `mcp_gbrain_save_page`, `mcp_gbrain_query`
- gbrain `procurement` source (location pages at `procurement/locations/`)

## Workflows

### "Create a new location / bin"

1. Gather: location ID (e.g., `LOC-MAIN-A1`), display name, zone, capacity (unit count or m³).
2. Create gbrain page at `procurement/locations/<LOC-ID>.md` with frontmatter:
   ```yaml
   ---
   location_id: LOC-MAIN-A1
   name: Main Warehouse — Aisle A, Shelf 1
   zone: main-warehouse
   capacity: 500
   current_items: []
   status: active
   ---
   ```
3. Confirm location created with ID and zone.

### "Assign / move an item to a bin"

1. Retrieve item page via `proc_get_item(sku=SKU)`.
2. Retrieve old and new location pages via `mcp_gbrain_query`.
3. Update `location_id` on the item's frontmatter page.
4. Update `current_items` list on both old and new location pages.
5. Confirm relocation with SKU, old bin, and new bin.

### "Bin capacity utilisation report"

1. Query all `procurement/locations/` pages.
2. For each location, count items assigned (via gbrain `location_id` reverse lookup).
3. Format as table: Location ID | Zone | Capacity | Items Assigned | Utilisation %.
4. Flag any locations at > 85% capacity.

## Common Pitfalls

1. **Location ID uniqueness** — always check if a location ID already exists before creating; IDs must be unique across all zones.
2. **Stale current_items lists** — when moving items, update both the old and new location pages atomically to prevent stale occupancy data.
3. **Capacity unit mismatch** — agree on a single capacity unit (item count vs. volume) at setup; mixing units produces meaningless utilisation %.

## Verification Checklist

- [ ] Skill installed at `skills/procurement/location-binning/SKILL.md`
- [ ] Frontmatter parses (no YAML errors)
- [ ] Location page appears at `procurement/locations/<LOC-ID>.md` after creation
- [ ] Item page `location_id` field updates correctly after a bin assignment
