---
name: promo-planning
description: "Promotional calendar management, display allocation by store cluster, signage generation, and post-promo analysis. Plans, executes, and measures promotional campaigns."
version: 1.0.0
tags: [retail, promotion, marketing, calendar, signage, analysis]
triggers:
  - "promo planning"
  - "promotional calendar"
  - "display allocation"
  - "signage generation"
  - "post promo analysis"
  - "promotion performance"
  - "campaign planning"
---

# Promo Planning

Promotional calendar management, display allocation by store cluster, signage generation, and post-promo analysis. Plans, executes, and measures the effectiveness of retail promotions.

## Overview

The Promo Planning skill manages the full lifecycle of retail promotions from calendar planning through post-promo analysis. It allocates promotional displays across store clusters, generates in-store signage, and measures incremental lift, margin impact, and return on investment.

| Metric | Description | Target |
|--------|-------------|--------|
| Incremental Lift | Sales uplift vs non-promo period | > 20% |
| Margin Impact | Margin % change during promo | < -5% |
| Display Compliance | % of stores with correct display | > 90% |
| Promo ROI | (Incremental profit - Promo cost) / Promo cost | > 3x |
| Redemption Rate | % of promo offers redeemed | Varies |
| Sell-Through | % of promo stock sold | > 80% |

## Usage

### View Promo Calendar

```
promo calendar --quarter Q1-YYYY [--store STORE_ID]
```

### Allocate Displays

```
promo allocate --promo PROMO_ID --cluster suburban [--display qty 10]
```

### Generate Signage

```
promo signage --promo PROMO_ID --format A3 [--language en,ms]
```

### Post-Promo Analysis

```
promo analysis --promo PROMO_ID [--compare prior_period]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROMO_DB_URL` | Database connection for promo data | `postgresql://localhost:5432/promotions` |
| `PROMO_CALENDAR_PATH` | Path to promotional calendar file | `./config/promo-calendar.yaml` |
| `PROMO_SIGNAGE_PATH` | Output path for generated signage | `./signage/` |
| `PROMO_SIGNAGE_LANGUAGES` | Comma-separated signage languages | `en,ms,zh` |
| `PROMO_DISPLAY_TYPES` | Available display types | `endcap,floor-stand,shelf-talker` |
| `PROMO_MIN_MARGIN_IMPACT` | Minimum acceptable margin impact % | `-5` |
| `PROMO_REPORT_PATH` | Output path for reports | `./reports/promotions/` |

### Promotional Calendar (promo-calendar.yaml)

```yaml
promotions:
  - id: "PROMO-2025-Q1-01"
    name: "Chinese New Year Bundle"
    start_date: "2025-01-20"
    end_date: "2025-02-10"
    type: "discount"
    discount_pct: 15
    display_type: "endcap"
    target_clusters: ["urban", "suburban"]
    signage_required: true
    expected_lift_pct: 25
  - id: "PROMO-2025-Q1-02"
    name: "Back to School"
    start_date: "2025-02-15"
    end_date: "2025-03-15"
    type: "bundle"
    bundle_items: ["SKU010", "SKU011", "SKU012"]
    bundle_price: 29.90
    display_type: "floor-stand"
    target_clusters: ["suburban", "mall"]
    signage_required: true
    expected_lift_pct: 30
```

## Scripts

### `scripts/promo-calendar.py`

Manages the promotional calendar. Tracks active, upcoming, and past promotions. Prevents scheduling conflicts and ensures adequate spacing between promotions.

### `scripts/display-allocation.py`

Allocates promotional displays and stock to store clusters based on historical performance, cluster size, and inventory availability.

### `scripts/signage-generator.py`

Generates promotional signage in configured languages and formats. Supports price tags, shelf talkers, banner stands, and endcap headers.

### `scripts/post-promo-analysis.py`

Analyzes promotion performance: incremental sales lift, margin impact, display compliance, ROI, and cannibalization of non-promoted items. Generates a lessons-learned report.

## Related Skills

- [store-sales-dashboard](../store-sales-dashboard/SKILL.md) — Sales data for promo lift measurement
- [planogram-compliance](../planogram-compliance/SKILL.md) — Display placement compliance
- [marketplace-analytics](../marketplace-analytics/SKILL.md) — Online promotion performance
- [assortment-planning](../assortment-planning/SKILL.md) — Promo product selection

## Pitfalls

- **Promotion cannibalization**: Promotions on one SKU can cannibalize sales of non-promoted SKUs in the same category. Track category-level P&L, not just promo SKU sales.
- **Promotion fatigue**: Running promotions too frequently trains customers to wait for discounts. Limit promotions to no more than 30% of selling days per category.
- **Display allocation fairness**: Stores with limited space cannot accommodate all displays. Create a display priority matrix based on store size and traffic.
- **Signage lead time**: In-store signage requires 2-3 weeks for design, approval, printing, and distribution. Factor this into calendar planning.
- **Post-promo dip**: Sales often drop below baseline immediately after a promotion ends. Plan for a 1-2 week recovery period before launching the next category promotion.