---
name: ecommerce-order-management
description: "Cross-platform order consolidation, fulfillment routing, return/refund processing, and delivery tracking. Manages orders from multiple marketplaces in a unified workflow."
version: 1.0.0
tags: [retail, ecommerce, orders, fulfillment, returns, delivery]
triggers:
  - "order management"
  - "order consolidation"
  - "fulfillment routing"
  - "return processing"
  - "refund tracking"
  - "delivery tracking"
  - "cross-platform orders"
---

# Ecommerce Order Management

Cross-platform order consolidation, fulfillment routing decisions, return and refund processing, and end-to-end delivery tracking. Provides a unified view of orders from Shopee, Lazada, and other marketplaces.

## Overview

The Order Management skill centralizes order processing across multiple ecommerce platforms. It routes orders to the optimal fulfillment location, tracks returns and refunds, and provides delivery status visibility to customer service teams.

| Stage | Process | SLA |
|-------|---------|-----|
| Order Intake | Consolidate orders from all platforms | Real-time |
| Fulfillment Routing | Assign to nearest store or warehouse | < 30 min |
| Pick & Pack | Pick items, package, label | < 4 hours |
| Dispatch | Hand off to carrier | < 2 hours |
| Delivery | Track to customer | 1-5 days |
| Returns | Process return requests | < 24 hours |

## Usage

### View Consolidated Orders

```
order list --date YYYY-MM-DD [--status pending] [--platform shopee]
```

### Route Order for Fulfillment

```
order route --order ORDER_ID [--source store-01]
```

### Process Return

```
order return --order ORDER_ID --reason "defective" [--refund full]
```

### Track Delivery

```
order track --order ORDER_ID
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ORDER_SHOPEE_API_KEY` | Shopee order API key | — |
| `ORDER_LAZADA_API_KEY` | Lazada order API key | — |
| `ORDER_DB_URL` | Database connection for order data | `postgresql://localhost:5432/orders` |
| `ORDER_FULFILLMENT_SOURCES` | Comma-separated fulfillment locations | `warehouse-01,store-01,store-02` |
| `ORDER_ROUTING_STRATEGY` | Fulfillment routing logic | `nearest` |
| `ORDER_RETURN_WINDOW_DAYS` | Days allowed for returns | `14` |
| `ORDER_CARRIER_API_KEY` | Shipping carrier API key | — |
| `ORDER_REPORT_PATH` | Output path for reports | `./reports/orders/` |

### Fulfillment Routing (routing.yaml)

```yaml
routing:
  strategy: "nearest"  # nearest | inventory | cost
  rules:
    - if: "order.value > 500"
      source: "warehouse-01"
      reason: "High-value items ship from central warehouse"
    - if: "order.items > 5"
      source: "warehouse-01"
      reason: "Large orders ship from central warehouse"
    - default: "nearest_store"
      reason: "Standard orders fulfilled from nearest store"
```

## Scripts

### `scripts/consolidate-orders.py`

Fetches orders from all connected marketplace platforms and consolidates them into a unified order management system. Deduplicates and flags anomalies.

### `scripts/route-fulfillment.py`

Applies routing rules to assign each order to the optimal fulfillment source. Generates pick lists and packing instructions.

### `scripts/process-returns.py`

Manages the return authorization workflow. Validates return eligibility, generates return labels, and processes refunds upon receipt.

### `scripts/delivery-tracking.py`

Polls carrier APIs for delivery status updates. Generates alerts for delayed shipments and provides tracking links to customer service.

## Related Skills

- [ecommerce-listing](../ecommerce-listing/SKILL.md) — Product catalog and inventory sync
- [marketplace-analytics](../marketplace-analytics/SKILL.md) — Order volume and fulfillment performance analytics
- [warehouse-distribution](../warehouse-distribution/SKILL.md) — Warehouse pick-pack-ship operations

## Pitfalls

- **Platform-specific return policies**: Each marketplace has different return rules. Ensure platform-specific policies are applied, not a single return policy.
- **Carrier integration drift**: Carrier APIs change without notice. Monitor webhook delivery and have fallback tracking via manual upload.
- **Inventory deduction timing**: Deduct inventory at order placement, not fulfillment. Delayed deduction causes overselling on fast-moving items.
- **COD (Cash on Delivery) risk**: Orders with high COD value have higher rejection rates. Monitor COD acceptance rates by region and adjust routing accordingly.
- **Returns fraud**: Implement photo verification for high-value returns. Track return rate by customer and flag accounts exceeding thresholds.