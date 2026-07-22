---
name: production-oee
description: "Calculates OEE (Availability × Performance × Quality), generates daily OEE reports with trend analysis and top loss identification. Configurable target OEE (default 85%)."
version: 1.0.0
tags: [manufacturing, oee, production, metrics, reporting]
triggers:
  - "calculate oee"
  - "oee report"
  - "production efficiency"
  - "overall equipment effectiveness"
  - "oee trend"
---

# Production OEE

Calculates Overall Equipment Effectiveness (OEE) from availability, performance, and quality data. Generates daily reports with trend analysis, top loss identification, and configurable target tracking.

## Overview

OEE is calculated as: **Availability × Performance × Quality**

| Component | Formula | Description |
|-----------|---------|-------------|
| Availability | Run Time / Planned Production Time | Uptime percentage |
| Performance | (Ideal Cycle Time × Total Count) / Run Time | Speed efficiency |
| Quality | Good Count / Total Count | Quality yield |

## Usage

### Generate OEE Report

```
oee report --date YYYY-MM-DD [--plant PLANT_ID] [--line LINE_ID]
```

### Calculate OEE for a Shift

```
oee calculate --shift SHIFT_ID --date YYYY-MM-DD
```

### View OEE Trend

```
oee trend --days 30 [--plant PLANT_ID]
```

### Identify Top Losses

```
oee top-losses --date YYYY-MM-DD [--limit 5]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OEE_TARGET` | Target OEE percentage | `85` |
| `OEE_DATA_SOURCE` | Data source adapter (csv, api, database) | `csv` |
| `OEE_DATA_PATH` | Path to OEE data files | `./data/oee/` |
| `OEE_REPORT_PATH` | Output path for reports | `./reports/oee/` |
| `OEE_SHIFT_CALENDAR` | Shift pattern definition file | `./config/shifts.yaml` |
| `OEE_PLANT_IDS` | Comma-separated plant identifiers | `plant-01` |

### Shift Configuration (shifts.yaml)

```yaml
shifts:
  - name: "Morning"
    start: "06:00"
    end: "14:00"
  - name: "Afternoon"
    start: "14:00"
    end: "22:00"
  - name: "Night"
    start: "22:00"
    end: "06:00"
```

## Scripts

### `scripts/calculate-oee.py`

Main calculation script. Accepts date, shift, and plant parameters.

### `scripts/generate-oee-report.py`

Generates OEE report with charts for availability, performance, quality, and trend lines.

### `scripts/top-losses.py`

Identifies top 5 loss categories (breakdown, setup, idling, speed loss, defects) with Pareto analysis.

## Related Skills

- [maintenance-downtime](../maintenance-downtime/SKILL.md) — Detailed downtime event logging
- [maintenance-pm](../maintenance-pm/SKILL.md) — Preventive maintenance schedule
- [quality-ncr](../quality-ncr/SKILL.md) — Non-Conformance Report management
- [mes-connector](../mes-connector/SKILL.md) — MES/SCADA data ingestion

## Pitfalls

- **Data quality**: OEE is only as good as the underlying data. Ensure cycle times are validated and downtime events are properly categorized.
- **Ideal cycle time drift**: Review and update ideal cycle times quarterly. Stale values produce misleading performance scores.
- **Shift boundaries**: Events near shift boundaries may be double-counted or missed. Use a 5-minute grace period for handover events.
- **Target setting**: The default 85% target (World-Class OEE) may not be appropriate for all equipment types. Set per-line targets for new or heavily customized equipment.
- **Partial data**: Running OEE calculation on partial shifts (machine still running) produces incomplete results. Always use full shift data or flag partial reports.