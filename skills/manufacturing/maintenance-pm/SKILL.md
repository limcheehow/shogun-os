---
name: maintenance-pm
description: "Preventive maintenance schedule. Due/overdue tracking. Work order generation. PM compliance rate."
version: 1.0.0
tags: [manufacturing, maintenance, preventive, pm, schedule, compliance]
triggers:
  - "preventive maintenance"
  - "pm schedule"
  - "pm compliance"
  - "maintenance due"
  - "overdue maintenance"
---

# Maintenance PM (Preventive Maintenance)

Manages preventive maintenance schedules, tracks due and overdue tasks, generates work orders automatically, and calculates PM compliance rates.

## Overview

| PM Type | Frequency | Trigger |
|---------|-----------|---------|
| Daily | Every operating day | Calendar |
| Weekly | Every 7 days | Calendar |
| Monthly | Calendar month | Calendar |
| Quarterly | Every 3 months | Calendar or meter reading |
| Semi-Annual | Every 6 months | Calendar or meter reading |
| Annual | Every 12 months | Calendar |
| Meter-Based | Every N operating hours/cycles | Meter reading |

## Usage

### List PM Schedule

```
pm list --plant PLANT_ID --equipment EQ-001 [--status due]
```

### View PM Detail

```
pm show PM-001234
```

### Generate PM Work Orders

```
pm generate --date YYYY-MM-DD [--plant PLANT_ID]
```

### PM Compliance Report

```
pm compliance --from YYYY-MM-DD --to YYYY-MM-DD
```

### Overdue PM Report

```
pm overdue --days 7 [--plant PLANT_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PM_DATA_PATH` | Path to PM data storage | `./data/maintenance/pm/` |
| `PM_AUTO_GENERATE_DAYS` | Days ahead to auto-generate work orders | `7` |
| `PM_COMPLIANCE_TARGET` | Target PM compliance percentage | `90` |
| `PM_OVERDUE_ESCALATION_DAYS` | Days overdue before escalation | `3` |
| `PM_METER_TYPES` | Comma-separated meter types | `hours,cycles` |
| `PM_ESCALATION_CONTACT` | Escalation contact for overdue PMs | `maintenance_supervisor` |

### PM Schedule Format (YAML)

```yaml
pm_tasks:
  - id: "PM-001"
    equipment: "EQ-001"
    description: "Lubricate bearings"
    frequency: "weekly"
    duration_minutes: 30
    required_skills: ["lubrication"]
    safety_ppe: ["gloves", "safety_glasses"]
  - id: "PM-002"
    equipment: "EQ-002"
    description: "Replace air filters"
    frequency: "monthly"
    meter_type: "hours"
    meter_interval: 500
    duration_minutes: 60
```

## Scripts

### `scripts/pm-list.py`

List PM tasks with due date, equipment, and status filters.

### `scripts/pm-generate-wo.py`

Generate work orders from PM schedule within the configured forward window.

### `scripts/pm-compliance.py`

Calculate PM compliance rate (completed on-time vs. total due) with trend.

### `scripts/pm-overdue.py`

Identify overdue PMs with escalation priority and aging analysis.

## Related Skills

- [maintenance-downtime](../maintenance-downtime/SKILL.md) — Unplanned downtime correlated with PM gaps
- [work-order-tracking](../work-order-tracking/SKILL.md) — PM-generated work order lifecycle
- [production-oee](../production-oee/SKILL.md) — Availability impact of PM scheduling
- [mes-connector](../mes-connector/SKILL.md) — Meter reading ingestion for meter-based PMs

## Pitfalls

- **Meter reading gaps**: Meter-based PMs depend on timely meter readings. If readings don't arrive, PMs go undetected. Set up alerts for stale meter data.
- **PM frequency overload**: Too many PMs on the same machine creates maintenance congestion. Optimize PM intervals during equipment reviews.
- **Compliance gaming**: A PM completed on-time but poorly executed inflates compliance. Track quality metrics alongside compliance.
- **Seasonal variation**: Equipment operating conditions change seasonally. Adjust PM frequency for peak vs. off-peak periods.
- **Deferred PMs**: Operations may defer PMs for production pressure. Enforce a maximum deferral policy with director-level approval.