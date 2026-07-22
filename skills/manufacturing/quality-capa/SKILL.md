---
name: quality-capa
description: "CAPA lifecycle: Open → Investigation → Action Plan → Implementation → Effectiveness Check → Closed. Root cause analysis (5 Whys). Aging and closure rate dashboard."
version: 1.0.0
tags: [manufacturing, quality, capa, corrective-action, root-cause, 5-whys]
triggers:
  - "create capa"
  - "corrective action"
  - "preventive action"
  - "root cause analysis"
  - "5 whys"
  - "capa aging"
---

# Quality CAPA (Corrective and Preventive Action)

Manages the full CAPA lifecycle from identification through effectiveness verification. Uses 5 Whys methodology for root cause analysis and provides aging and closure rate dashboards.

## CAPA Lifecycle

```
Open → Investigation → Action Plan → Implementation → Effectiveness Check → Closed
```

| Phase | Activities | Responsible |
|-------|-----------|-------------|
| Open | Identify issue, classify severity, assign owner | Initiator |
| Investigation | Root cause analysis (5 Whys, fishbone), impact assessment | Quality Engineer |
| Action Plan | Define corrective/preventive actions, assign owners, set due dates | Cross-functional team |
| Implementation | Execute actions, verify completion, attach evidence | Action Owners |
| Effectiveness Check | Verify actions prevent recurrence, sample data, close loop | Quality Manager |
| Closed | Final approval, documentation, lessons learned | Quality Manager |

## Usage

### Create CAPA

```
capa create --source ncr --source-id NCR-2024-001234
           --severity major --description "Recurring dimension defect on line A"
```

### Run 5 Whys Analysis

```
capa 5whys CAPA-2024-0001 --interactive
```

### Define Action Plan

```
capa action-plan CAPA-2024-0001 --action "Update torque specs" --owner OPS_MGR --due 2024-02-01
```

### Approve Effectiveness

```
capa effectiveness CAPA-2024-0001 --status effective --verified-by QA_MGR
```

### CAPA Dashboard

```
capa dashboard [--aging] [--closure-rate] [--by-department]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CAPA_DATA_PATH` | Path to CAPA data storage | `./data/capa/` |
| `CAPA_AUTO_ESCALATE_DAYS` | Days in phase before escalation | `21` |
| `CAPA_ESCALATION_LEVELS` | Comma-separated escalation recipients | `quality_manager,plant_manager,quality_director` |
| `CAPA_EFFECTIVENESS_WAIT_DAYS` | Days to wait before effectiveness check | `90` |
| `CAPA_CLOSURE_TARGET_DAYS` | Target closure time | `60` |
| `CAPA_5WHYS_TEMPLATE_PATH` | Path to 5 Whys worksheet template | `./templates/5whys-template.md` |

### Severity Classification

| Severity | Description | Closure Target |
|----------|-------------|----------------|
| Critical | Safety risk, regulatory non-compliance | 14 days |
| Major | Significant quality impact, customer complaint | 30 days |
| Minor | Internal process deviation, low impact | 60 days |
| Observation | Improvement opportunity, no immediate risk | 90 days |

## Scripts

### `scripts/capa-create.py`

Create CAPA with source linkage, severity, and initial investigation assignment.

### `scripts/capa-5whys.py`

Interactive 5 Whys analysis with guided questioning and root cause capture.

### `scripts/capa-dashboard.py`

Dashboard showing aging distribution, closure rate by severity, and department performance.

### `scripts/capa-effectiveness.py`

Track effectiveness check results with pass/fail rate by action type.

## Related Skills

- [quality-ncr](../quality-ncr/SKILL.md) — NCRs trigger CAPA workflows
- [maintenance-pm](../maintenance-pm/SKILL.md) — CAPA may result in PM changes
- [hse-incident](../hse-incident/SKILL.md) — Combined quality-safety CAPA investigations

## Pitfalls

- **CAPA without root cause**: Jumping to action planning before completing root cause analysis leads to recurring issues. Enforce 5 Whys completion before action plan phase.
- **Effectiveness window**: Checking effectiveness too early (before enough data accumulates) or too late (after drift) invalidates the check. Respect the configured wait period.
- **Action ownership**: Actions assigned to groups ("Engineering") are rarely completed. Always assign to a named individual.
- **Cascading CAPAs**: A single root cause may generate multiple CAPAs. Link related CAPAs to avoid duplicated effort.
- **CAPA inflation**: Creating CAPAs for every minor observation dilutes focus. Use severity thresholds to gate CAPA creation.