---
name: loyalty-program
description: "Points accrual rules, tier management, birthday/promotion triggers, rewards catalog, and redemption tracking. Manages end-to-end customer loyalty program lifecycle."
version: 1.0.0
tags: [retail, loyalty, rewards, points, tiers, customer, retention]
triggers:
  - "loyalty program"
  - "points accrual"
  - "tier management"
  - "rewards catalog"
  - "redemption tracking"
  - "customer rewards"
  - "birthday promotion"
---

# Loyalty Program

Points accrual rule configuration, tier management (Silver/Gold/Platinum), automated birthday and promotion triggers, rewards catalog management, and redemption tracking analytics.

## Overview

The Loyalty Program skill manages the full lifecycle of customer loyalty initiatives. It configures points earning rules, manages membership tiers, triggers automated promotions, maintains a rewards catalog, and tracks redemption patterns to measure program effectiveness.

| Component | Description | Target |
|-----------|-------------|--------|
| Points Accrual | Rules for earning points per transaction | 1 point per $1 |
| Tier Progression | Customer advancement between tiers | Tracked quarterly |
| Redemption Rate | % of issued points redeemed | > 30% |
| Program ROI | Incremental revenue from program | > 5x program cost |
| Active Member % | % of enrolled members with recent activity | > 60% |
| Churn Rate | % of members lapsing per period | < 10% |

## Usage

### Configure Points Rules

```
loyalty points-rules --set --rate 1.0 --threshold 100
```

### Manage Tiers

```
loyalty tiers --list
loyalty tiers --promote --customer CUST_ID --tier gold
```

### Trigger Birthday Promotion

```
loyalty trigger --type birthday --date YYYY-MM-DD [--dry-run]
```

### Redemption Report

```
loyalty redemptions --period monthly --date YYYY-MM
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOYALTY_DB_URL` | Database connection for loyalty data | `postgresql://localhost:5432/loyalty` |
| `LOYALTY_POINTS_RATE` | Points earned per currency unit spent | `1.0` |
| `LOYALTY_POINTS_EXPIRY_DAYS` | Points expiry period in days | `365` |
| `LOYALTY_BIRTHDAY_BONUS` | Bonus points on birthday | `100` |
| `LOYALTY_BIRTHDAY_WINDOW_DAYS` | Days before/after birthday for bonus | `7` |
| `LOYALTY_REDEMPTION_MIN_POINTS` | Minimum points for redemption | `500` |
| `LOYALTY_REPORT_PATH` | Output path for reports | `./reports/loyalty/` |

### Tier Configuration (tiers.yaml)

```yaml
tiers:
  - name: "Silver"
    min_points_ytd: 0
    benefits:
      - "1 point per $1 spent"
      - "Birthday bonus: 100 points"
  - name: "Gold"
    min_points_ytd: 5000
    benefits:
      - "1.5 points per $1 spent"
      - "Birthday bonus: 200 points"
      - "Free shipping on orders above $50"
  - name: "Platinum"
    min_points_ytd: 15000
    benefits:
      - "2 points per $1 spent"
      - "Birthday bonus: 500 points"
      - "Free shipping on all orders"
      - "Exclusive member events"
```

## Scripts

### `scripts/points-engine.py`

Core points calculation engine. Applies accrual rules per transaction, handles bonus points for promotions and birthdays, and manages point expiry schedules.

### `scripts/tier-manager.py`

Evaluates customer tier eligibility quarterly. Promotes qualifying members, demotes non-qualifying members, and sends tier change notifications.

### `scripts/redemption-tracker.py`

Tracks reward redemptions across all channels. Generates reports on most popular rewards, redemption patterns, and points liability.

### `scripts/loyalty-roi.py`

Calculates program ROI by comparing incremental revenue from loyalty members against program costs (points liability, marketing, operations).

## Related Skills

- [customer-segmentation](../customer-segmentation/SKILL.md) — RFM analysis for targeted loyalty offers
- [promo-planning](../promo-planning/SKILL.md) — Promotional calendar integration with loyalty triggers
- [store-sales-dashboard](../store-sales-dashboard/SKILL.md) — Sales impact of loyalty program

## Pitfalls

- **Points liability accounting**: Unredeemed points represent a balance sheet liability. Accrue points liability at the time of issuance, not redemption.
- **Tier demotion backlash**: Customers react negatively to tier demotions. Consider a grace period (3 months) before demoting and communicate proactively.
- **Promotion stacking**: Birthday bonuses combined with other promotions can create unexpected discount stacking. Define stacking rules explicitly.
- **Points expiry communication**: Points expiry can trigger customer complaints. Send multiple reminders (30 days, 14 days, 7 days before expiry).
- **Fraud detection**: Monitor for abnormal points earning patterns (e.g., high-value transactions followed by immediate returns). Implement velocity checks on point accrual.