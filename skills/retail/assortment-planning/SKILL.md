---
name: assortment-planning
description: "Category performance analysis (sales, margin, turnover), SKU rationalization, and new product intake calendar management. Optimizes product mix across stores."
version: 1.0.0
tags: [retail, assortment, category, sku, product, planning]
triggers:
  - "assortment planning"
  - "category performance"
  - "sku rationalization"
  - "product mix"
  - "new product intake"
  - "category management"
---

# Assortment Planning

Category performance analysis including sales, margin, and inventory turnover. Manages SKU rationalization and new product intake calendar to optimize product mix across retail stores.

## Overview

Assortment Planning ensures the right products are available in the right stores at the right time. It analyzes category performance, identifies underperforming SKUs for rationalization, and manages the new product introduction pipeline.

| Metric | Description | Target |
|--------|-------------|--------|
| Gross Margin % | (Revenue - COGS) / Revenue | > 40% |
| Inventory Turnover | COGS / Average Inventory | 6-12x/year |
| SKU Productivity | Revenue per SKU per month | Varies by category |
| Sell-Through Rate | Units Sold / Units Received | > 70% |
| Weeks of Supply | Current Stock / Avg Weekly Sales | 4-8 weeks |
| Category Share | Category sales as % of total | Per category target |

## Usage

### Category Performance Report

```
assortment category --period monthly --date YYYY-MM [--store STORE_ID]
```

### SKU Rationalization

```
assortment rationalize --threshold 0.05 --period 90d [--category CATEGORY]
```

### New Product Intake Calendar

```
assortment intake-calendar --quarter Q1-YYYY [--category CATEGORY]
```

### Product Lifecycle Report

```
assortment lifecycle --sku SKU_ID [--days 180]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ASSORTMENT_DB_URL` | Database connection for product data | `postgresql://localhost:5432/assortment` |
| `ASSORTMENT_RATIONALIZATION_THRESHOLD` | Revenue contribution % below which SKUs are flagged | `0.05` |
| `ASSORTMENT_SELL_THROUGH_TARGET` | Target sell-through rate percentage | `70` |
| `ASSORTMENT_TURNOVER_TARGET` | Target inventory turns per year | `8` |
| `ASSORTMENT_NEW_PRODUCT_WINDOW` | Days to evaluate new product performance | `90` |
| `ASSORTMENT_REPORT_PATH` | Output path for reports | `./reports/assortment/` |
| `ASSORTMENT_CATEGORIES` | Comma-separated category list | `apparel,electronics,home` |

### Category Targets (categories.yaml)

```yaml
categories:
  - name: "Apparel"
    margin_target: 50
    turnover_target: 6
    sell_through_target: 75
  - name: "Electronics"
    margin_target: 25
    turnover_target: 10
    sell_through_target: 65
  - name: "Home & Living"
    margin_target: 45
    turnover_target: 4
    sell_through_target: 70
```

## Scripts

### `scripts/category-performance.py`

Category-level sales, margin, and turnover analysis with year-over-year comparison. Generates heatmaps by category and store cluster.

### `scripts/sku-rationalization.py`

Flags underperforming SKUs based on revenue contribution, margin, and sell-through rate. Generates a proposed discontinuation list with impact analysis.

### `scripts/intake-calendar.py`

Manages the new product introduction timeline. Tracks intake by week, identifies shelf space conflicts, and monitors launch performance.

### `scripts/product-lifecycle.py`

Traces a SKU through its lifecycle from introduction to discontinuation. Calculates phase timing and profitability per phase.

## Related Skills

- [store-replenishment](../store-replenishment/SKILL.md) — Auto-reorder based on assortment decisions
- [promo-planning](../promo-planning/SKILL.md) — Promotional calendar for product launches
- [vendor-negotiation](../vendor-negotiation/SKILL.md) — Vendor scorecards for new product sourcing

## Pitfalls

- **Store clustering**: Assortment should vary by store cluster (urban, suburban, mall). A one-size-fits-all assortment plan leads to overstock in some stores and stockouts in others.
- **Seasonal SKUs**: Don't rationalize seasonal SKUs based on off-season performance. Use trailing 12-month data for seasonal products.
- **New product evaluation**: 90 days may not be enough for all categories. Set category-specific evaluation windows based on purchase cycle.
- **Vendor minimums**: SKU rationalization may conflict with vendor minimum order quantities. Factor in vendor commitments before discontinuing.
- **Cannibalization**: Introducing a new SKU can cannibalize existing SKU sales. Track category-level margin impact, not just individual SKU performance.