---
name: warehouse-inventory
description: "Inventory levels by category (raw, WIP, finished). Aging analysis (slow-moving, dead stock). Reorder point alerts. Cycle count scheduling."
version: 1.0.0
tags: [manufacturing, warehouse, inventory, stock, cycle-count, reorder]
triggers:
  - "inventory levels"
  - "stock aging"
  - "slow moving stock"
  - "reorder point"
  - "cycle count"
  - "inventory report"
---

# Warehouse Inventory

Tracks inventory levels across raw materials, work-in-progress (WIP), and finished goods. Provides aging analysis, reorder point alerts, and cycle count scheduling.

## Overview

| Category | Description | Turning |
|----------|-------------|---------|
| Raw Materials | Unprocessed inputs | Fast to medium |
| WIP | Partially completed products | Variable |
| Finished Goods | Completed products ready for shipment | Medium to slow |
| MRO | Maintenance, repair, and operations supplies | Slow |
| Consumables | Single-use items | Fast |

## Usage

### View Inventory Levels

```
inv levels --category raw [--plant PLANT_ID] [--sort stock_qty]
```

### Aging Analysis

```
inv aging --days 90 [--category finished] [--threshold 30]
```

### Reorder Point Alert

```
inv reorder-alert [--plant PLANT_ID]
```

### Schedule Cycle Count

```
inv cycle-count create --area AISLE-01 --date YYYY-MM-DD
```

### Inventory Snapshot

```
inv snapshot --plant PLANT_ID [--output json|csv]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `INV_DATA_PATH` | Path to inventory data storage | `./data/inventory/` |
| `INV_ERP_ADAPTER` | ERP adapter for inventory sync | `manual` |
| `INV_SLOW_MOVING_DAYS` | Days without movement to classify as slow-moving | `90` |
| `INV_DEAD_STOCK_DAYS` | Days without movement to classify as dead stock | `365` |
| `INV_CYCLE_COUNT_FREQ` | Default cycle count frequency | `monthly` |
| `INV_SAFETY_STOCK_DEFAULT` | Default safety stock days | `14` |
| `INV_PLANT_CURRENCY` | Currency for inventory valuation | `USD` |

### Reorder Point Configuration

```yaml
reorder_points:
  - sku: "RM-001"
    description: "Steel plate 3mm"
    reorder_point: 500
    reorder_qty: 2000
    lead_time_days: 14
    safety_stock_days: 7
  - sku: "RM-002"
    description: "Copper wire 1.5mm"
    reorder_point: 1000
    reorder_qty: 5000
    lead_time_days: 21
    safety_stock_days: 14
```

## Scripts

### `scripts/inv-levels.py`

Query inventory levels by category, location, and SKU with valuation.

### `scripts/inv-aging.py`

Aging analysis with slow-moving and dead stock identification.

### `scripts/inv-reorder.py`

Reorder point alerts with suggested purchase order quantities.

### `scripts/inv-cycle-count.py`

Schedule and track cycle counts with count completion monitoring.

## Related Skills

- [erp-connector](../erp-connector/SKILL.md) — ERP inventory data sync
- [work-order-tracking](../work-order-tracking/SKILL.md) — Material availability for work orders
- [production-oee](../production-oee/SKILL.md) — Material shortages affecting OEE

## Pitfalls

- **Inventory valuation method**: FIFO, LIFO, and weighted average produce different valuations. Standardize on one method per plant.
- **Phantom inventory**: System shows stock that physically isn't there (or vice versa). Cycle counts are essential to reconcile.
- **Negative inventory**: Negative quantities indicate data entry errors or unposted transactions. Investigate and resolve immediately.
- **ABC classification**: Not all items need the same counting frequency. Classify by value (A=high, B=medium, C=low) and count accordingly.
- **Reservation vs. allocation**: A reserved item is not necessarily allocated. Understand the difference to avoid double-counting available stock.
- **Unit of measure conversion**: Bulk units (kg) vs. piece units (pcs) require conversion factors. Validate conversions regularly.