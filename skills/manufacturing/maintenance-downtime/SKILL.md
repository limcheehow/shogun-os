---
name: maintenance-downtime
description: "Unplanned downtime event logging. Pareto by equipment/reason/shift. MTBF and MTTR calculation. Downtime cost estimation."
version: 1.0.0
tags: [manufacturing, maintenance, downtime, mtbf, mttr, pareto]
triggers:
  - "log downtime"
  - "downtime report"
  - "mtbf calculation"
  - "mttr calculation"
  - "downtime pareto"
  - "unplanned downtime"
---

# Maintenance Downtime

Tracks unplanned downtime events, performs Pareto analysis by equipment, reason, and shift. Calculates MTBF (Mean Time Between Failures) and MTTR (Mean Time To Repair) with downtime cost estimation.

## Overview

| Metric | Formula | Description |
|--------|---------|-------------|
| MTBF | Total Operating Time / Number of Failures | Average time between failures |
| MTTR | Total Repair Time / Number of Repairs | Average time to repair |
| Downtime Cost | Downtime Hours × Cost Per Hour | Estimated production loss |

## Usage

### Log Downtime Event

```
downtime log --equipment EQ-001 --reason mechanical_failure
            --start "2024-01-15 08:30" --end "2024-01-15 09:45"
            --shift morning --operator OPR-001
```

### Create Downtime Pareto

```
downtime pareto --from YYYY-MM-DD --to YYYY-MM-DD
               [--group-by equipment|reason|shift]
```

### Calculate MTBF/MTTR

```
downtime metrics --equipment EQ-001 --from YYYY-MM-DD --to YYYY-MM-DD
```

### Cost Estimation

```
downtime cost --from YYYY-MM-DD --to YYYY-MM-DD [--plant PLANT_ID]
```

### Downtime Summary Report

```
downtime summary --date YYYY-MM-DD [--plant PLANT_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DT_DATA_PATH` | Path to downtime data storage | `./data/maintenance/downtime/` |
| `DT_COST_PER_HOUR` | Estimated cost of downtime per hour | `1000` |
| `DT_PLANT_CURRENCY` | Currency code for cost estimation | `USD` |
| `DT_REASON_CODES_PATH` | Path to reason code catalog | `./config/downtime-reasons.yaml` |
| `DT_AUTO_CLOSE_DAYS` | Days after which unclosed events are auto-closed | `7` |

### Reason Code Catalog (downtime-reasons.yaml)

```yaml
reason_codes:
  - code: "mechanical_failure"
    description: "Mechanical component failure"
    category: "equipment"
  - code: "electrical_failure"
    description: "Electrical/electronic failure"
    category: "equipment"
  - code: "changeover"
    description: "Product changeover"
    category: "process"
  - code: "material_shortage"
    description: "Raw material unavailable"
    category: "supply"
  - code: "no_operator"
    description: "Operator unavailable"
    category: "labor"
  - code: "quality_hold"
    description: "Quality issue escalation"
    category: "quality"
```

## Scripts

### `scripts/downtime-log.py`

Log downtime events with start/end time, equipment, reason, and shift.

### `scripts/downtime-pareto.py`

Pareto analysis by equipment, reason, shift, or operator.

### `scripts/downtime-metrics.py`

Calculate MTBF, MTTR, and availability by equipment over a date range.

### `scripts/downtime-cost.py`

Estimate downtime cost with breakdown by reason category.

## Related Skills

- [maintenance-pm](../maintenance-pm/SKILL.md) — PM gaps revealed by downtime analysis
- [production-oee](../production-oee/SKILL.md) — Downtime feeds the Availability component of OEE
- [mes-connector](../mes-connector/SKILL.md) — Automated downtime event ingestion from MES/SCADA
- [quality-capa](../quality-capa/SKILL.md) — Chronic downtime issues may trigger CAPA

## Pitfalls

- **Event overlap**: Multiple downtime events for the same equipment at the same time double-counts. Enforce single active event per equipment.
- **Short stops**: Events under 5 minutes are often noise. Set a minimum duration threshold, but track them separately for performance analysis.
- **Reason code consistency**: Operators may select the wrong code under pressure. Provide clear code descriptions and review reason code usage monthly.
- **Partial shifts**: A downtime event spanning a shift boundary counts against both shifts. Decide on a handover policy (event belongs to the shift where it started).
- **Cost estimation accuracy**: The `DT_COST_PER_HOUR` is a rough estimate. Actual cost depends on product margin, downstream delays, and customer impact. Use as directional, not financial.