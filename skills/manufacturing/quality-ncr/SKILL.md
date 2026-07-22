---
name: quality-ncr
description: "Non-Conformance Report management. Create, disposition (use-as-is / rework / scrap / RTV), track closure. Defect Pareto, aging report."
version: 1.0.0
tags: [manufacturing, quality, ncr, non-conformance, defects, pareto]
triggers:
  - "create ncr"
  - "non-conformance report"
  - "quality issue"
  - "defect tracking"
  - "ncr aging"
  - "defect pareto"
---

# Quality NCR (Non-Conformance Report)

Manages the complete Non-Conformance lifecycle: identification, containment, disposition, and closure. Includes defect Pareto analysis and aging reports to drive continuous improvement.

## Overview

| Disposition | Description |
|-------------|-------------|
| Use-as-is | Product accepted with deviation, customer notified |
| Rework | Product returned to production for correction |
| Scrap | Product cannot be salvaged, marked for disposal |
| RTV | Return to vendor for supplier-managed non-conformance |

## NCR Lifecycle

```
Identified → Contained → Investigated → Dispositioned → Corrected → Closed
```

## Usage

### Create NCR

```
ncr create --product PRODUCT_ID --defect DEFECT_CODE --quantity 5
         --disposition rework --source inspection
```

### List NCRs

```
ncr list --status open [--plant PLANT_ID] [--priority high]
```

### View NCR Detail

```
ncr show NCR-2024-001234
```

### Update NCR Status

```
ncr update NCR-2024-001234 --status closed --closed-by OPERATOR_ID
```

### Generate Defect Pareto

```
ncr pareto --from YYYY-MM-DD --to YYYY-MM-DD [--plant PLANT_ID]
```

### NCR Aging Report

```
ncr aging --days-open 7 [--department dept_name]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NCR_DATA_PATH` | Path to NCR data storage | `./data/ncr/` |
| `NCR_AUTO_ESCALATE_DAYS` | Days before automatic escalation | `14` |
| `NCR_ESCALATION_LEVELS` | Comma-separated escalation levels | `supervisor,manager,director` |
| `NCR_DEFECT_CODES_PATH` | Path to defect code catalog | `./config/defect-codes.yaml` |
| `NCR_CLOSURE_TIMEOUT_DAYS` | Target closure time in days | `30` |

### Defect Code Catalog (defect-codes.yaml)

```yaml
defect_codes:
  - code: "DIM-001"
    description: "Dimension out of tolerance"
    category: "dimensional"
  - code: "FIN-001"
    description: "Surface finish defect"
    category: "cosmetic"
  - code: "MAT-001"
    description: "Material contamination"
    category: "material"
  - code: "FUNC-001"
    description: "Functional test failure"
    category: "functional"
  - code: "PACK-001"
    description: "Packaging damage"
    category: "packaging"
```

## Scripts

### `scripts/ncr-create.py`

Create NCR with defect details, disposition, and containment actions.

### `scripts/ncr-pareto.py`

Generate Pareto chart by defect code, product, line, or shift.

### `scripts/ncr-aging.py`

Age analysis showing NCRs grouped by days open, with escalation recommendations.

### `scripts/ncr-closure-rate.py`

Calculate closure rate by disposition type and average closure time by department.

## Related Skills

- [quality-capa](../quality-capa/SKILL.md) — CAPA workflow for root cause analysis
- [production-oee](../production-oee/SKILL.md) — Quality component of OEE
- [erp-connector](../erp-connector/SKILL.md) — Sync NCR dispositions to ERP inventory
- [hse-incident](../hse-incident/SKILL.md) — Quality incidents with safety implications

## Pitfalls

- **Duplicate NCRs**: Multiple inspectors may report the same issue. De-duplicate before analysis.
- **Disposition completeness**: A disposition without a responsible person and due date is not actionable. Enforce these fields.
- **Defect code granularity**: Too many codes makes Pareto analysis noisy. Too few hides root causes. Review code catalog quarterly.
- **Containment vs. correction**: Ensure containment actions (immediate) are separate from corrective actions (permanent). Mixing them causes confusion.
- **RTV tracking**: RTV items must be tracked separately from scrap. Ensure RTV dispositions trigger supplier claim workflows.