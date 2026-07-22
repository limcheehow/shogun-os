---
name: hse-incident
description: "Incident types: Near-miss, First Aid, Medical Treatment, LTI, Fatality. Severity matrix. Investigation workflow. Leading/lagging indicators."
version: 1.0.0
tags: [manufacturing, hse, safety, incident, near-miss, lti, investigation]
triggers:
  - "report incident"
  - "hse incident"
  - "safety incident"
  - "near miss"
  - "lost time injury"
  - "safety metrics"
  - "leading indicators"
  - "lagging indicators"
---

# HSE Incident Management

Manages Health, Safety, and Environment (HSE) incidents from reporting through investigation and closure. Covers all incident types with severity classification, investigation workflow, and leading/lagging indicator tracking.

## Incident Types

| Type | Description | Severity |
|------|-------------|----------|
| Near-miss | Unsafe event with no injury or damage | Low |
| First Aid | Minor injury treated on-site | Low |
| Medical Treatment | Injury requiring professional medical care | Medium |
| Restricted Work | Injury limiting work activities | Medium |
| LTI (Lost Time Injury) | Injury causing lost work time | High |
| Fatality | Work-related death | Critical |
| Environmental | Spill, release, or environmental violation | Variable |
| Property Damage | Equipment or facility damage | Variable |

## Severity Matrix

| Likelihood ↓ / Consequence → | Minor | Moderate | Major | Critical |
|------------------------------|-------|----------|-------|----------|
| Almost Certain | Medium | High | Critical | Critical |
| Likely | Medium | High | High | Critical |
| Possible | Low | Medium | High | High |
| Unlikely | Low | Low | Medium | High |
| Rare | Low | Low | Medium | Medium |

## Usage

### Report Incident

```
hse report --type near_miss --description "Slippery floor near line 3"
          --location "Plant A, Line 3" --reporter "John Doe"
```

### Incident Investigation

```
hse investigate INC-2024-001234 --root-cause "Inadequate spill response training"
```

### Record Leading Indicator

```
hse leading --indicator "safety_training_completed" --value 42 --month 2024-01
```

### Safety Dashboard

```
hse dashboard --from YYYY-MM-DD --to YYYY-MM-DD
```

### LTI Rate Calculation

```
hse lti-rate --from YYYY-MM-DD --to YYYY-MM-DD [--plant PLANT_ID]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HSE_DATA_PATH` | Path to incident data storage | `./data/hse/` |
| `HSE_REPORTING_HOURS` | Hours to report after incident (regulatory) | `24` |
| `HSE_LTI_BASE_HOURS` | Base hours for LTI rate calculation | `200000` |
| `HSE_AUTO_ESCALATE_DAYS` | Days before investigation auto-escalation | `7` |
| `HSE_ESCALATION_CONTACTS` | Escalation contact list | `hse_manager,plant_manager,regional_hse` |
| `HSE_REGULATORY_BODY` | Applicable regulatory standard | `OSHA` |

### Leading & Lagging Indicators

| Indicator | Type | Description |
|-----------|------|-------------|
| Total Recordable Incident Rate (TRIR) | Lagging | Standard industry safety metric |
| Lost Time Injury Frequency (LTIF) | Lagging | LTI per million hours worked |
| Near-miss Reporting Rate | Leading | Near-misses reported per period |
| Safety Training Completion | Leading | Percentage of required training completed |
| Safety Observation Rate | Leading | Observations submitted per person per month |
| Hazard Closure Rate | Leading | Percentage of hazards closed within target |

## Scripts

### `scripts/hse-report.py`

Report new incidents with type, severity, location, and description.

### `scripts/hse-investigate.py`

Investigation workflow with root cause, corrective actions, and closure.

### `scripts/hse-dashboard.py`

Safety dashboard with TRIR, LTIF, near-miss trends, and leading indicators.

### `scripts/hse-metrics.py`

Calculate and report HSE KPIs by period and plant.

## Related Skills

- [quality-capa](../quality-capa/SKILL.md) — Safety incidents may trigger CAPA
- [quality-ncr](../quality-ncr/SKILL.md) — Quality incidents with safety implications
- [maintenance-pm](../maintenance-pm/SKILL.md) — Equipment safety-related PMs

## Pitfalls

- **Underreporting**: Near-misses are frequently underreported due to fear of blame. Foster a no-blame reporting culture.
- **Classification disputes**: Whether an injury is "First Aid" vs. "Medical Treatment" affects regulatory reporting. Use a clear decision tree.
- **Investigation delay**: Delayed investigations lose evidence and witness memory. Enforce the `HSE_REPORTING_HOURS` window.
- **Leading indicator gaming**: Teams may inflate leading indicators (e.g., reporting trivial observations). Validate indicator quality.
- **Regulatory drift**: HSE regulations change. Periodically review incident classification against current regulatory requirements.
- **LTI rate small numbers**: With small workforces, a single LTI causes large rate swings. Use rolling averages for trend analysis.