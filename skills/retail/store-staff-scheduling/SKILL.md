---
name: store-staff-scheduling
description: "Shift planning, attendance tracking, break compliance monitoring, and labor cost vs sales ratio analysis. Optimizes staff allocation based on traffic forecasts."
version: 1.0.0
tags: [retail, staffing, scheduling, attendance, labor, hr]
triggers:
  - "staff schedule"
  - "shift planning"
  - "attendance tracking"
  - "labor cost ratio"
  - "break compliance"
  - "staff roster"
---

# Store Staff Scheduling

Shift planning, attendance tracking, break compliance monitoring, and labor cost vs sales ratio analysis. Optimizes staff allocation based on foot traffic forecasts and historical patterns.

## Overview

The Staff Scheduling module balances store coverage with labor cost targets. It generates optimized shift rosters, tracks clock-in/out compliance, monitors break adherence, and calculates the labor cost as a percentage of sales.

| Metric | Description | Target |
|--------|-------------|--------|
| Labor Cost % | Staff wages as % of net sales | 8-12% |
| Coverage Gap | Hours with insufficient staff | < 5% of operating hours |
| Break Compliance | % of staff taking mandated breaks | > 95% |
| Schedule Adherence | Actual vs scheduled hours | ±5% |
| Overtime % | Overtime as % of total hours | < 3% |

## Usage

### Generate Staff Schedule

```
staff schedule --week YYYY-WW [--store STORE_ID] [--optimize]
```

### Track Attendance

```
staff attendance --date YYYY-MM-DD [--store STORE_ID]
```

### Check Break Compliance

```
staff breaks --date YYYY-MM-DD [--store STORE_ID]
```

### Labor Cost Report

```
staff labor-cost --period weekly --date YYYY-MM-DD [--store STORE_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `STAFF_DB_URL` | Database connection for staff data | `postgresql://localhost:5432/staff` |
| `STAFF_LABOR_TARGET_PCT` | Target labor cost as % of sales | `10` |
| `STAFF_MIN_SHIFT_HOURS` | Minimum shift duration in hours | `4` |
| `STAFF_MAX_SHIFT_HOURS` | Maximum shift duration in hours | `10` |
| `STAFF_BREAK_INTERVAL` | Hours worked before mandatory break | `5` |
| `STAFF_BREAK_DURATION` | Minimum break duration in minutes | `30` |
| `STAFF_STORE_IDS` | Comma-separated store identifiers | `store-01,store-02` |
| `STAFF_SCHEDULE_PATH` | Output path for schedules | `./schedules/` |

### Staff Configuration (staff.yaml)

```yaml
stores:
  - id: "store-01"
    roles:
      - name: "Cashier"
        min_per_shift: 2
        max_per_shift: 4
      - name: "Sales Associate"
        min_per_shift: 3
        max_per_shift: 6
      - name: "Supervisor"
        min_per_shift: 1
        max_per_shift: 1
```

## Scripts

### `scripts/generate-schedule.py`

Generates optimized weekly staff schedules based on traffic forecasts, staff availability, and labor cost targets.

### `scripts/attendance-report.py`

Daily attendance report showing clock-in/out times, late arrivals, and early departures per store.

### `scripts/break-compliance.py`

Audits break adherence against local labor regulations. Flags missed or shortened breaks.

### `scripts/labor-cost-analysis.py`

Calculates labor cost as percentage of sales with trend analysis and alerts when exceeding target threshold.

## Related Skills

- [store-sales-dashboard](../store-sales-dashboard/SKILL.md) — Sales data for labor cost ratio calculation
- [customer-segmentation](../customer-segmentation/SKILL.md) — Traffic pattern analysis for staffing forecasts

## Pitfalls

- **Labor law variance**: Break and overtime rules vary by jurisdiction. Always configure store-specific labor law parameters rather than using defaults.
- **Traffic forecast accuracy**: Staffing schedules are only as good as foot traffic predictions. Use 4-week rolling averages rather than single-week comparisons.
- **Schedule publication deadlines**: Post schedules at least 7 days in advance in most jurisdictions. Late schedules increase compliance risk.
- **Shift swapping**: Allow staff-initiated shift swaps but require manager approval to maintain coverage ratios.
- **Part-time vs full-time mix**: Monitor the full-time/part-time ratio to avoid regulatory penalties under healthcare or leave mandates.