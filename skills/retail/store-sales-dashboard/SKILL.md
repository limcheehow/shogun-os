---
name: store-sales-dashboard
description: "Daily sales by store, hourly trends, staff performance, customer count, and sales vs budget variance analysis. Generates interactive dashboards with drill-down capability."
version: 1.0.0
tags: [retail, sales, dashboard, reporting, analytics]
triggers:
  - "sales dashboard"
  - "daily sales report"
  - "store performance"
  - "sales vs budget"
  - "hourly sales trend"
  - "customer count"
---

# Store Sales Dashboard

Daily sales by store with hourly trends, staff performance metrics, customer count tracking, and sales vs budget variance analysis. Generates interactive dashboards for store managers and regional supervisors.

## Overview

The Store Sales Dashboard aggregates transactional data to provide a single-pane view of store performance. Key metrics include total sales, transaction count, average basket size, customer traffic, and budget attainment.

| Metric | Description | Calculation |
|--------|-------------|-------------|
| Gross Sales | Total revenue before discounts | Sum of all sales transactions |
| Net Sales | Revenue after discounts & returns | Gross Sales - Discounts - Returns |
| Customer Count | Unique customer transactions | Count of distinct transaction IDs |
| Average Basket Size | Spend per transaction | Net Sales / Customer Count |
| Sales vs Budget | Variance from target | (Actual - Budget) / Budget × 100 |
| Conversion Rate | Purchasers vs foot traffic | Customer Count / Foot Traffic × 100 |

## Usage

### Generate Daily Dashboard

```
sales dashboard --date YYYY-MM-DD [--store STORE_ID] [--region REGION]
```

### View Hourly Trends

```
sales hourly-trends --date YYYY-MM-DD [--store STORE_ID]
```

### Sales vs Budget Report

```
sales budget-variance --period monthly --date YYYY-MM [--store STORE_ID]
```

### Staff Performance Summary

```
sales staff-performance --date YYYY-MM-DD [--store STORE_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SALES_DB_URL` | Database connection string for sales data | `postgresql://localhost:5432/sales` |
| `SALES_DASHBOARD_PORT` | Dashboard server port | `8080` |
| `SALES_REFRESH_INTERVAL` | Auto-refresh interval in seconds | `300` |
| `SALES_BUDGET_FILE` | Path to budget targets file | `./config/budgets.yaml` |
| `SALES_STORE_IDS` | Comma-separated store identifiers | `store-01,store-02` |
| `SALES_CURRENCY` | Currency code for display | `MYR` |
| `SALES_REPORT_PATH` | Output path for exported reports | `./reports/sales/` |

### Budget Configuration (budgets.yaml)

```yaml
stores:
  - id: "store-01"
    monthly_budget: 500000
    weekly_budget: 125000
    daily_budget: 17857
  - id: "store-02"
    monthly_budget: 350000
    weekly_budget: 87500
    daily_budget: 12500
```

## Scripts

### `scripts/generate-dashboard.py`

Main dashboard generator. Accepts date, store, and region parameters. Outputs HTML dashboard with interactive charts.

### `scripts/hourly-trends.py`

Generates hourly sales breakdown with comparison to prior periods. Useful for identifying peak traffic and staffing needs.

### `scripts/budget-variance.py`

Calculates sales vs budget variance with drill-down to department and category level. Flags stores exceeding or falling below threshold.

### `scripts/staff-performance.py`

Per-staff sales metrics including total sales, transaction count, and average basket size per shift.

## Related Skills

- [store-staff-scheduling](../store-staff-scheduling/SKILL.md) — Shift planning and attendance tracking
- [promo-planning](../promo-planning/SKILL.md) — Promotional calendar and post-promo analysis
- [store-replenishment](../store-replenishment/SKILL.md) — Auto-reorder and stock allocation

## Pitfalls

- **Data latency**: Real-time dashboards may lag behind POS systems by 5-15 minutes. Clearly label data freshness on dashboards.
- **Budget baseline drift**: Budget targets should be reviewed quarterly. Stale budgets produce misleading variance percentages.
- **Holiday effects**: Calendar-driven comparisons (last year same day) are more meaningful than sequential day comparisons during holiday periods.
- **Returns processing**: Same-day returns can distort net sales. Track gross and net separately on dashboards.
- **Multi-currency**: If stores operate in different currencies, apply consistent FX rates and flag the rate date on reports.