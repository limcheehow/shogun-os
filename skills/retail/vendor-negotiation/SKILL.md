---
name: vendor-negotiation
description: "Vendor scorecards (delivery, quality, price), margin analysis, contract expiry alerts, and rebate tracking. Supports procurement negotiations with data-driven insights."
version: 1.0.0
tags: [retail, vendor, procurement, negotiation, supply-chain]
triggers:
  - "vendor scorecard"
  - "supplier performance"
  - "margin analysis"
  - "contract expiry"
  - "rebate tracking"
  - "procurement negotiation"
---

# Vendor Negotiation

Vendor scorecards covering delivery reliability, quality compliance, and price competitiveness. Provides margin analysis, contract expiry alerts, and rebate tracking to support data-driven procurement negotiations.

## Overview

The Vendor Negotiation skill consolidates supplier performance data into actionable scorecards. It tracks delivery timeliness, product quality, pricing trends, and rebate accruals to give buyers leverage in contract negotiations.

| Metric | Description | Target |
|--------|-------------|--------|
| On-Time Delivery % | Orders delivered on or before due date | > 95% |
| Order Fill Rate % | Line items shipped complete | > 98% |
| Quality Acceptance % | Orders passing incoming inspection | > 99% |
| Price Competitiveness | Vendor price vs market benchmark | ≤ 100% |
| Rebate Accrual Rate | Earned rebates as % of spend | > 2% |
| Lead Time Adherence | Actual vs quoted lead time variance | ±2 days |

## Usage

### Generate Vendor Scorecard

```
vendor scorecard --vendor VENDOR_ID [--period YYYY-MM]
```

### Margin Analysis

```
vendor margin-analysis --vendor VENDOR_ID [--sku SKU_ID]
```

### Contract Expiry Alerts

```
vendor expiring-contracts --days 90
```

### Rebate Tracking

```
vendor rebates --vendor VENDOR_ID [--year YYYY]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VENDOR_DB_URL` | Database connection for vendor data | `postgresql://localhost:5432/vendor` |
| `VENDOR_OTD_TARGET` | On-time delivery target percentage | `95` |
| `VENDOR_QUALITY_TARGET` | Quality acceptance target percentage | `99` |
| `VENDOR_FILL_RATE_TARGET` | Order fill rate target percentage | `98` |
| `VENDOR_CONTRACT_ALERT_DAYS` | Days before expiry to trigger alert | `90` |
| `VENDOR_REBATE_THRESHOLD` | Minimum rebate % to flag | `2` |
| `VENDOR_REPORT_PATH` | Output path for scorecards | `./reports/vendor/` |
| `VENDOR_IDS` | Comma-separated vendor identifiers | `VEN001,VEN002,VEN003` |

### Scorecard Weights (scorecard.yaml)

```yaml
scoring:
  on_time_delivery_weight: 0.30
  quality_weight: 0.25
  fill_rate_weight: 0.20
  price_competitiveness_weight: 0.15
  rebate_weight: 0.10
  rating_tiers:
    - name: "Platinum"
      min_score: 90
      label: "Preferred Partner"
    - name: "Gold"
      min_score: 75
      label: "Approved Supplier"
    - name: "Silver"
      min_score: 60
      label: "Conditional Approved"
    - name: "Bronze"
      min_score: 0
      label: "Under Review"
```

## Scripts

### `scripts/vendor-scorecard.py`

Generates comprehensive vendor scorecards with weighted scoring across delivery, quality, price, and rebate dimensions. Includes trend arrows and peer comparison.

### `scripts/margin-analysis.py`

Analyzes gross margin by vendor and SKU. Identifies margin erosion trends and compares vendor pricing against market benchmarks.

### `scripts/contract-expiry-monitor.py`

Scans upcoming contract expirations and generates renewal/termination recommendations with negotiation talking points.

### `scripts/rebate-tracking.py`

Tracks earned vs collected rebates. Generates aging reports for uncollected rebates and identifies short-payments.

## Related Skills

- [assortment-planning](../assortment-planning/SKILL.md) — Category performance for vendor negotiations
- [store-replenishment](../store-replenishment/SKILL.md) — Lead time and fill rate data
- [warehouse-distribution](../warehouse-distribution/SKILL.md) — Inbound receiving performance

## Pitfalls

- **Data recency**: Scorecards should use the most recent 3-6 months of data. Annual averages mask recent performance deterioration.
- **Benchmarking fairness**: Compare vendors against similar categories and volumes. A small apparel vendor should not be scored against a multinational electronics supplier.
- **Rebate complexity**: Rebate structures (tiered, threshold, retroactive) require careful tracking. Use accrual accounting rather than cash basis for accurate rebate visibility.
- **Contract auto-renewal**: Many contracts auto-renew if not cancelled within a notice window. Set alerts well before the notice period, not the expiry date.
- **Vendor concentration**: Track dependency risk. If a single vendor exceeds 30% of category spend, build a diversification strategy alongside the scorecard.