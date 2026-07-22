---
name: store-replenishment
description: "Auto-reorder from warehouse to stores, min/max by SKU, allocation logic per store cluster, and lead time tracking. Optimizes store inventory levels."
version: 1.0.0
tags: [retail, replenishment, inventory, reorder, allocation, supply-chain]
triggers:
  - "store replenishment"
  - "auto-reorder"
  - "min max inventory"
  - "store allocation"
  - "lead time tracking"
  - "replenishment planning"
---

# Store Replenishment

Auto-reorder from warehouse to stores based on min/max inventory levels, SKU-specific allocation logic per store cluster, and lead time tracking. Ensures optimal stock levels at every store.

## Overview

The Store Replenishment skill automates the flow of inventory from distribution centers to retail stores. It calculates optimal reorder quantities based on consumption rates, lead times, and safety stock targets, then allocates available inventory across store clusters.

| Metric | Description | Target |
|--------|-------------|--------|
| In-Stock Rate | % of SKUs available on shelf | > 95% |
| Stockout Rate | % of SKUs with zero stock | < 2% |
| Inventory Turnover | COGS / Average Store Inventory | 8-12x/year |
| Reorder Accuracy | % of auto-reorders accepted | > 90% |
| Lead Time Variance | Actual vs quoted lead time | ±1 day |
| Allocation Fairness | Fill rate variance across stores | < 10% |

## Usage

### Generate Reorder Proposal

```
replenish reorder --store STORE_ID [--date YYYY-MM-DD] [--dry-run]
```

### View Min/Max Levels

```
replenish minmax --sku SKU_ID [--store STORE_ID]
```

### Allocate Inventory

```
replenish allocate --sku SKU_ID --quantity 500 [--cluster urban]
```

### Check Lead Times

```
replenish lead-times --vendor VENDOR_ID [--sku SKU_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REPLENISH_DB_URL` | Database connection for inventory data | `postgresql://localhost:5432/inventory` |
| `REPLENISH_SAFETY_STOCK_DAYS` | Safety stock coverage in days | `7` |
| `REPLENISH_REORDER_FREQUENCY` | Reorder cadence (daily, twice-weekly, weekly) | `daily` |
| `REPLENISH_MIN_ORDER_QTY` | Minimum order quantity per SKU | `5` |
| `REPLENISH_MAX_STOCK_DAYS` | Maximum stock coverage in days | `30` |
| `REPLENISH_STORE_CLUSTERS` | Comma-separated store cluster names | `urban,suburban,mall` |
| `REPLENISH_REPORT_PATH` | Output path for reports | `./reports/replenishment/` |

### Store Cluster Configuration (clusters.yaml)

```yaml
clusters:
  - name: "Urban"
    stores: [store-01, store-02]
    safety_stock_days: 10
    delivery_frequency: "daily"
    lead_time_days: 1
  - name: "Suburban"
    stores: [store-03, store-04]
    safety_stock_days: 14
    delivery_frequency: "twice-weekly"
    lead_time_days: 2
  - name: "Mall"
    stores: [store-05]
    safety_stock_days: 7
    delivery_frequency: "daily"
    lead_time_days: 1
```

### SKU Min/Max Configuration (minmax.yaml)

```yaml
skus:
  - sku: "SKU001"
    min_store_qty: 10
    max_store_qty: 50
    reorder_point: 20
    multiple_of: 5  # Order in multiples of 5
  - sku: "SKU002"
    min_store_qty: 5
    max_store_qty: 25
    reorder_point: 10
    multiple_of: 1
```

## Scripts

### `scripts/reorder-proposal.py`

Generates daily reorder proposals for each store based on current stock, projected sales, and min/max levels. Supports dry-run mode for review.

### `scripts/allocation-engine.py`

Allocates available warehouse inventory across store clusters based on demand, priority, and fairness rules. Handles constrained allocation when supply is limited.

### `scripts/lead-time-monitor.py`

Tracks actual lead times from order placement to delivery receipt. Calculates lead time variance and adjusts safety stock recommendations.

### `scripts/inventory-health.py`

Assesses store inventory health: in-stock rate, stockout frequency, overstock SKUs, and slow-moving inventory. Generates store-level scorecards.

## Related Skills

- [warehouse-distribution](../warehouse-distribution/SKILL.md) — Warehouse outbound operations
- [assortment-planning](../assortment-planning/SKILL.md) — SKU rationalization impacts replenishment
- [store-sales-dashboard](../store-sales-dashboard/SKILL.md) — Sales data for demand forecasting

## Pitfalls

- **Demand seasonality**: Static min/max levels fail during seasonal peaks. Implement seasonal adjustment factors or dynamic min/max based on rolling 12-week sales.
- **New store ramp**: New stores have no historical data. Use cluster averages for the first 8 weeks, then transition to store-specific parameters.
- **Constrained allocation**: When supply is limited, allocate proportionally to demand rather than equally. Equal allocation penalizes high-volume stores.
- **Promotion impact**: Promotion periods can spike demand 3-5x. Increase min/max levels for promoted SKUs 2 weeks before and during promotions.
- **Phantom inventory**: Inventory records may show stock that isn't physically available (theft, damage, miscount). Reconcile physical counts before reorder decisions.