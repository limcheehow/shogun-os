---
name: customer-segmentation
description: "RFM analysis (Recency/Frequency/Monetary), churn prediction, lookalike targeting, and campaign response scoring. Segments customers for targeted marketing."
version: 1.0.0
tags: [retail, customer, segmentation, rfm, churn, marketing, analytics]
triggers:
  - "customer segmentation"
  - "rfm analysis"
  - "churn prediction"
  - "lookalike targeting"
  - "campaign response scoring"
  - "customer clusters"
  - "segmentation analysis"
---

# Customer Segmentation

RFM (Recency, Frequency, Monetary) analysis, churn prediction modeling, lookalike targeting for acquisition, and campaign response propensity scoring. Enables data-driven customer marketing.

## Overview

The Customer Segmentation skill divides the customer base into actionable groups based on purchasing behavior. It uses RFM scoring to identify high-value segments, predicts churn risk, generates lookalike audiences for acquisition, and scores campaign response propensity.

| Segment | Description | Recency | Frequency | Monetary | Strategy |
|---------|-------------|---------|-----------|----------|----------|
| Champions | Best customers | < 30 days | High | High | Reward, nurture |
| Loyal | Regular buyers | 30-90 days | Medium-High | Medium | Upsell, cross-sell |
| At Risk | Haven't bought recently | 90-180 days | Medium | Medium | Re-engagement |
| Lost | Churned | > 180 days | Low | Low | Win-back campaign |
| New | First purchase | < 30 days | 1 | Low | Convert to regular |

## Usage

### Run RFM Analysis

```
segment rfm [--period 90d] [--buckets 5]
```

### Predict Churn Risk

```
segment churn-prediction [--model logistic] [--confidence 0.7]
```

### Generate Lookalike Audience

```
segment lookalike --seed SEGMENT_ID --size 10000
```

### Campaign Response Score

```
segment response-score --campaign CAMPAIGN_ID [--customer CUST_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SEGMENT_DB_URL` | Database connection for customer data | `postgresql://localhost:5432/customers` |
| `SEGMENT_RFM_WEIGHTS` | Recency/Frequency/Monetary weights | `0.3,0.3,0.4` |
| `SEGMENT_CHURN_WINDOW_DAYS` | Days without purchase = churned | `180` |
| `SEGMENT_LOOKALIKE_SIZE` | Default lookalike audience size | `10000` |
| `SEGMENT_MIN_CLUSTER_SIZE` | Minimum customers per segment | `500` |
| `SEGMENT_MODEL_PATH` | Path to ML models | `./models/segmentation/` |
| `SEGMENT_REPORT_PATH` | Output path for reports | `./reports/segmentation/` |

### RFM Buckets (rfm.yaml)

```yaml
rfm:
  recency_buckets:
    - score: 5
      days: 30
      label: "Very Recent"
    - score: 4
      days: 90
      label: "Recent"
    - score: 3
      days: 180
      label: "Moderate"
    - score: 2
      days: 365
      label: "Old"
    - score: 1
      days: 9999
      label: "Very Old"
  frequency_buckets:
    - score: 5
      min_orders: 20
    - score: 4
      min_orders: 10
    - score: 3
      min_orders: 5
    - score: 2
      min_orders: 2
    - score: 1
      min_orders: 0
  monetary_buckets:
    - score: 5
      min_spend: 5000
    - score: 4
      min_spend: 2000
    - score: 3
      min_spend: 1000
    - score: 2
      min_spend: 500
    - score: 1
      min_spend: 0
```

## Scripts

### `scripts/rfm-analysis.py`

Computes Recency, Frequency, and Monetary scores for all active customers. Generates segment distribution charts and migration analysis (how customers move between segments over time).

### `scripts/churn-predictor.py`

Trains or applies a churn prediction model using historical purchase patterns, browsing behavior, and support interactions. Outputs a churn risk score per customer.

### `scripts/lookalike-generator.py`

Generates lookalike audiences from a seed segment by identifying customers with similar attributes. Useful for paid acquisition campaigns.

### `scripts/campaign-response.py`

Scores the likelihood of a customer responding to a specific campaign. Uses historical campaign response data and customer attributes.

## Related Skills

- [loyalty-program](../loyalty-program/SKILL.md) — Loyalty tier alignment with customer segments
- [promo-planning](../promo-planning/SKILL.md) — Targeted promotions based on segments
- [marketplace-analytics](../marketplace-analytics/SKILL.md) — Campaign performance measurement

## Pitfalls

- **RFM bucket boundaries**: Fixed bucket boundaries may not suit all categories. Review and adjust bucket thresholds quarterly based on distribution.
- **Churn definition**: 180 days without purchase is a common default but varies by category. Grocery churn is 30 days; furniture churn may be 365 days.
- **Model drift**: Churn prediction models degrade over time. Retrain every 90 days and monitor AUC scores.
- **Lookalike quality**: Lookalike audiences from small seed segments (< 1000 customers) have poor quality. Minimum viable seed size is 5000 customers.
- **Segmentation not strategy**: Segments identify groups but don't prescribe actions. Always pair segmentation with specific campaign strategies and A/B test plans.