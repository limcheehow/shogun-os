---
name: marketplace-analytics
description: "Sales by platform/channel, ad spend ROI analysis, competitor pricing monitoring, and customer review sentiment analysis. Provides actionable marketplace intelligence."
version: 1.0.0
tags: [retail, ecommerce, marketplace, analytics, competitors, pricing, sentiment]
triggers:
  - "marketplace analytics"
  - "sales by platform"
  - "ad spend roi"
  - "competitor pricing"
  - "review sentiment"
  - "channel performance"
  - "marketplace intelligence"
---

# Marketplace Analytics

Sales performance by platform and channel, advertising spend ROI analysis, competitor pricing monitoring, and customer review sentiment analysis. Provides actionable intelligence for marketplace strategy.

## Overview

The Marketplace Analytics skill aggregates data from all connected ecommerce platforms to provide a unified view of channel performance. It tracks ad spend efficiency, monitors competitor pricing, and analyzes customer review sentiment to identify opportunities and threats.

| Dimension | Metrics | Source |
|-----------|---------|--------|
| Sales by Platform | GMV, orders, AOV, conversion rate | Shopee, Lazada APIs |
| Advertising ROI | Spend, impressions, clicks, ACOS | Platform ad managers |
| Competitor Pricing | Price gap, stock status, promotions | Scraped data |
| Review Sentiment | Rating distribution, keywords, trends | Platform review APIs |
| Category Trends | Category growth, share, seasonality | Aggregated data |

## Usage

### Platform Sales Report

```
marketplace sales --platform shopee --period weekly --date YYYY-MM-DD
```

### Ad Spend ROI Analysis

```
marketplace ads --platform lazada --date YYYY-MM [--campaign CAMPAIGN_ID]
```

### Competitor Pricing Monitor

```
marketplace competitor-pricing --sku SKU_ID [--competitors 5]
```

### Review Sentiment Report

```
marketplace reviews --sku SKU_ID [--days 30] [--language en]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MARKETPLACE_SHOPEE_API_KEY` | Shopee analytics API key | — |
| `MARKETPLACE_LAZADA_API_KEY` | Lazada analytics API key | — |
| `MARKETPLACE_ADS_API_KEY` | Advertising platform API key | — |
| `MARKETPLACE_DB_URL` | Database connection for analytics | `postgresql://localhost:5432/analytics` |
| `MARKETPLACE_COMPETITOR_SKUS` | Comma-separated competitor SKU patterns | — |
| `MARKETPLACE_PRICE_ALERT_THRESHOLD` | Price gap % to trigger alert | `10` |
| `MARKETPLACE_SENTIMENT_THRESHOLD` | Sentiment score threshold for alerts | `3.5` |
| `MARKETPLACE_REPORT_PATH` | Output path for reports | `./reports/marketplace/` |

### Competitor Tracking (competitors.yaml)

```yaml
competitors:
  - name: "Competitor A"
    sku_prefix: "COMPA-"
    price_alert_threshold: 5
    monitoring_frequency: "daily"
  - name: "Competitor B"
    sku_prefix: "COMPB-"
    price_alert_threshold: 10
    monitoring_frequency: "daily"
```

## Scripts

### `scripts/platform-sales.py`

Aggregates sales data from all connected platforms. Generates comparative reports showing platform share, growth rates, and category performance.

### `scripts/ad-roi-analysis.py`

Pulls advertising spend and performance data from platform ad managers. Calculates ACOS (Advertising Cost of Sales), ROAS (Return on Ad Spend), and trend analysis.

### `scripts/competitor-pricing.py`

Monitors competitor pricing for matched SKUs. Generates alerts when price gaps exceed configured thresholds and recommends pricing adjustments.

### `scripts/sentiment-analysis.py`

Analyzes customer reviews using NLP sentiment scoring. Extracts common themes, tracks rating trends, and flags negative sentiment clusters.

## Related Skills

- [ecommerce-listing](../ecommerce-listing/SKILL.md) — Listing optimization and SEO
- [ecommerce-order-management](../ecommerce-order-management/SKILL.md) — Order fulfillment performance
- [promo-planning](../promo-planning/SKILL.md) — Promotional calendar and performance

## Pitfalls

- **Data freshness**: Marketplace analytics APIs have data latency (typically 24-48 hours). Clearly label data freshness in all reports.
- **Attribution models**: Platform attribution models differ. Shopee and Lazada may credit different touchpoints for the same conversion. Never compare raw attribution numbers across platforms.
- **Competitor scraping legality**: Automated competitor price monitoring may violate platform terms of service. Use platform-provided APIs where available and verify compliance.
- **Sentiment sampling bias**: Only a fraction of customers leave reviews. Sentiment analysis reflects the reviewing population, not the entire customer base.
- **Ad platform attribution windows**: Different attribution windows (7-day click vs 30-day view) produce vastly different ROAS numbers. Standardize on one window and document it.