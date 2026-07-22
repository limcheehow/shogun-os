---
name: work-order-tracking
description: "Tracks work orders from release to completion. Reads from ERP connector or manual entry. Reports WIP, backlog, on-time delivery rate."
version: 1.0.0
tags: [manufacturing, work-order, production, wip, backlog, scheduling]
triggers:
  - "work order status"
  - "wip report"
  - "production backlog"
  - "on-time delivery"
  - "work order tracking"
---

# Work Order Tracking

Tracks manufacturing work orders from release through completion. Supports both ERP-connected and manual entry workflows. Provides real-time visibility into WIP, backlog, and on-time delivery performance.

## Overview

| Status | Description |
|--------|-------------|
| Released | Order issued to production floor |
| In Progress | Material issued, production started |
| Hold | Paused (quality issue, material shortage, equipment) |
| Completed | All operations finished |
| Closed | Final inspection passed, order archived |

## Usage

### List Work Orders

```
wo list --status in_progress [--plant PLANT_ID] [--limit 20]
```

### View Work Order Detail

```
wo show WO-2024-001234
```

### Create Work Order

```
wo create --product PRODUCT_ID --quantity 100 --due YYYY-MM-DD
```

### Update Work Order Status

```
wo update WO-2024-001234 --status completed
```

### Generate WIP Report

```
wo wip-report [--plant PLANT_ID] [--line LINE_ID]
```

### Backlog Report

```
wo backlog --days 7 [--sort due_date]
```

### On-Time Delivery Rate

```
wo otd --from YYYY-MM-DD --to YYYY-MM-DD
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WO_ERP_ADAPTER` | ERP adapter name (odoo, erpnext, manual) | `manual` |
| `WO_DATA_PATH` | Path for manual work order data | `./data/work-orders/` |
| `WO_DEFAULT_PLANT` | Default plant identifier | `plant-01` |
| `WO_OTD_TARGET` | On-time delivery target percentage | `95` |
| `WO_BACKLOG_WARNING_DAYS` | Days past due before flagging | `3` |

### Work Order Data Format (CSV)

```csv
wo_id,product,quantity,released_date,due_date,status,plant,line
WO-001,PROD-A,100,2024-01-01,2024-01-10,in_progress,plant-01,line-01
```

## Scripts

### `scripts/wo-list.py`

List and filter work orders by status, plant, and date range.

### `scripts/wo-create.py`

Create new work orders with product, quantity, due date, and routing.

### `scripts/wo-otd.py`

Calculate on-time delivery rate over a date range with trend.

### `scripts/wo-backlog.py`

Identify backlogged orders with aging analysis and escalation recommendations.

## Related Skills

- [erp-connector](../erp-connector/SKILL.md) — ERP integration for work order data
- [production-oee](../production-oee/SKILL.md) — Production efficiency tracking
- [warehouse-inventory](../warehouse-inventory/SKILL.md) — Material availability for work orders
- [quality-ncr](../quality-ncr/SKILL.md) — NCRs linked to work orders

## Pitfalls

- **Status drift**: Work orders left in "In Progress" after completion inflate WIP. Automate status transitions where possible.
- **Split lots**: Partial completions (split lots) need special handling. Track parent-child work order relationships.
- **Holding reason**: Always require a reason code when putting an order on hold. Otherwise hold analysis is meaningless.
- **ERP latency**: When using ERP adapters, sync frequency affects data freshness. Schedule periodic syncs for near-real-time visibility.
- **Unit of measure**: Ensure consistent UOM between work order quantity and inventory issue/return transactions.