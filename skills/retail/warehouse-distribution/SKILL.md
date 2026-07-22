---
name: warehouse-distribution
description: "Inbound receiving, putaway, pick-pack-ship, cross-docking, wave planning, and carrier dispatch. Manages end-to-end warehouse and distribution center operations."
version: 1.0.0
tags: [retail, warehouse, distribution, logistics, fulfillment, inbound, outbound]
triggers:
  - "warehouse distribution"
  - "inbound receiving"
  - "putaway"
  - "pick pack ship"
  - "cross docking"
  - "wave planning"
  - "carrier dispatch"
---

# Warehouse Distribution

Inbound receiving and putaway, pick-pack-ship operations, cross-docking execution, wave planning, and carrier dispatch management. End-to-end warehouse logistics.

## Overview

The Warehouse Distribution skill manages the core operations of a distribution center. It covers the complete material flow from inbound receipt of goods through to outbound shipment to stores or customers, including cross-docking and wave-based picking.

| Operation | Description | SLA |
|-----------|-------------|-----|
| Inbound Receiving | Receive, verify, and record incoming goods | < 4 hours from arrival |
| Putaway | Move goods to storage locations | < 8 hours from receipt |
| Picking | Retrieve items for orders | < 2 hours per wave |
| Packing | Package items for shipment | < 1 hour per order |
| Cross-docking | Direct transfer from inbound to outbound | < 2 hours |
| Dispatch | Load and release to carrier | Per carrier schedule |

## Usage

### Process Inbound Receipt

```
warehouse receive --po PO_NUMBER [--verify]
```

### Generate Pick Wave

```
warehouse pick-wave --type store-replenishment [--wave-size 500]
```

### Manage Cross-Dock

```
warehouse crossdock --po PO_NUMBER --store STORE_ID
```

### Dispatch Shipments

```
warehouse dispatch --carrier DHL [--wave WAVE_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WAREHOUSE_DB_URL` | Database connection for warehouse data | `postgresql://localhost:5432/warehouse` |
| `WAREHOUSE_IDS` | Comma-separated warehouse identifiers | `WH-01,WH-02` |
| `WAREHOUSE_WAVE_CUTOFF_TIME` | Daily wave cutoff time (HH:MM) | `14:00` |
| `WAREHOUSE_MAX_WAVE_SIZE` | Maximum picks per wave | `500` |
| `WAREHOUSE_CARRIER_API_KEY` | Carrier integration API key | — |
| `WAREHOUSE_CROSSDOCK_ENABLED` | Enable cross-docking functionality | `true` |
| `WAREHOUSE_REPORT_PATH` | Output path for reports | `./reports/warehouse/` |

### Warehouse Layout (layout.yaml)

```yaml
warehouses:
  - id: "WH-01"
    zones:
      - name: "Receiving"
        dock_doors: 5
      - name: "Bulk Storage"
        locations: 1000
      - name: "Picking"
        locations: 2000
      - name: "Cross-Dock"
        staging_lanes: 10
      - name: "Shipping"
        dock_doors: 8
    carriers:
      - name: "DHL"
        pickup_times: ["10:00", "14:00", "18:00"]
      - name: "SF Express"
        pickup_times: ["09:00", "13:00", "17:00"]
```

## Scripts

### `scripts/inbound-receiving.py`

Manages the inbound receipt process. Verifies PO quantities, records received items, and generates discrepancy reports for damaged or short shipments.

### `scripts/pick-wave-planner.py`

Generates optimized pick waves based on order priority, zone proximity, and carrier cutoff times. Supports batch picking and zone routing.

### `scripts/cross-dock-manager.py`

Identifies cross-dock opportunities where inbound shipments match open store replenishment orders. Manages staging lane allocation and direct loading.

### `scripts/dispatch-scheduler.py`

Assigns outbound shipments to carriers based on destination, service level, cost, and pickup schedules. Generates manifests and labels.

## Related Skills

- [store-replenishment](../store-replenishment/SKILL.md) — Store replenishment orders from warehouse
- [ecommerce-order-management](../ecommerce-order-management/SKILL.md) — Ecommerce fulfillment routing
- [vendor-negotiation](../vendor-negotiation/SKILL.md) — Inbound carrier performance tracking

## Pitfalls

- **Slotting optimization**: Putaway location assignment affects picking efficiency. Review slotting at least quarterly and put fast-moving SKUs in prime picking locations.
- **Wave capacity**: Picking waves that exceed zone capacity create congestion. Set wave size limits per zone, not per warehouse.
- **Cross-dock timing**: Cross-docking requires precise timing between inbound and outbound schedules. A 30-minute delay can miss the outbound wave.
- **Carrier cutoff alignment**: Missing a carrier pickup window means a 24-hour delay. Align wave planning with carrier schedules down to the minute.
- **Inventory accuracy**: Warehouse operations depend on accurate bin-level inventory. Cycle count high-value and fast-moving SKUs more frequently than slow movers.