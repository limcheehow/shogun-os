---
name: planogram-compliance
description: "Store layout audits, shelf compliance scoring, photo validation workflow, and fixture standards enforcement. Ensures consistent product placement across stores."
version: 1.0.0
tags: [retail, planogram, compliance, layout, shelf, merchandising, audit]
triggers:
  - "planogram compliance"
  - "store layout audit"
  - "shelf compliance"
  - "photo validation"
  - "fixture standards"
  - "merchandising audit"
  - "shelf score"
---

# Planogram Compliance

Store layout audits, shelf compliance scoring, photo validation workflow, and fixture standards enforcement. Ensures consistent product placement and merchandising across all stores.

## Overview

The Planogram Compliance skill audits retail stores to ensure shelf layouts match the approved planogram. It uses a photo-based validation workflow, calculates compliance scores, tracks fixture standards, and generates corrective action reports.

| Metric | Description | Target |
|--------|-------------|--------|
| Shelf Compliance Score | % of SKUs in correct position | > 90% |
| Facings Compliance | Correct number of facings per SKU | > 85% |
| Fixture Compliance | Fixtures meet brand standards | > 95% |
| Photo Audit Completion | % of stores submitting photos weekly | > 100% |
| Corrective Action Closure | % of issues resolved within SLA | > 90% |
| Reset Accuracy | Post-reset compliance % | > 95% |

## Usage

### Run Store Audit

```
planogram audit --store STORE_ID [--section BEVERAGES]
```

### Submit Photo Validation

```
planogram photos --store STORE_ID --section BEVERAGES --path ./photos/
```

### View Compliance Score

```
planogram score --store STORE_ID [--date YYYY-MM-DD]
```

### Generate Fixture Report

```
planogram fixtures --store STORE_ID [--fixture-type gondola]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLANOGRAM_DB_URL` | Database connection for planogram data | `postgresql://localhost:5432/planogram` |
| `PLANOGRAM_COMPLIANCE_TARGET` | Target compliance score percentage | `90` |
| `PLANOGRAM_PHOTO_STORAGE` | Path for uploaded audit photos | `./photos/audits/` |
| `PLANOGRAM_VALIDATION_MODEL` | AI model for photo analysis | `default` |
| `PLANOGRAM_AUDIT_FREQUENCY` | Audit frequency per store | `weekly` |
| `PLANOGRAM_STORE_IDS` | Comma-separated store identifiers | `store-01,store-02` |
| `PLANOGRAM_REPORT_PATH` | Output path for reports | `./reports/planogram/` |

### Planogram Template (planogram.yaml)

```yaml
sections:
  - name: "Beverages"
    shelves:
      - shelf_id: "A01"
        shelf_label: "Carbonated Drinks"
        fixture_type: "gondola"
        dimensions: '{"width": 120, "depth": 40, "height": 180}'
        skus:
          - sku: "SKU001"
            product: "Cola 355ml"
            facings: 4
            position: "A01-01"
          - sku: "SKU002"
            product: "Cola Zero 355ml"
            facings: 3
            position: "A01-02"
          - sku: "SKU003"
            product: "Lemonade 355ml"
            facings: 3
            position: "A01-03"
  - name: "Snacks"
    shelves:
      - shelf_id: "B01"
        shelf_label: "Chips & Crackers"
        fixture_type: "gondola"
        dimensions: '{"width": 120, "depth": 40, "height": 150}'
        skus:
          - sku: "SKU010"
            product: "Potato Chips Original"
            facings: 5
            position: "B01-01"
```

## Scripts

### `scripts/store-audit.py`

Generates audit checklist for a store section. Compares actual shelf layout against planogram and calculates compliance scores.

### `scripts/photo-validation.py`

Processes store audit photos through AI validation. Detects SKU placement, facing counts, and fixture condition from uploaded images.

### `scripts/compliance-dashboard.py`

Aggregates compliance scores across all stores. Generates trend reports, identifies consistently non-compliant stores, and highlights top offenders by category.

### `scripts/fixture-standards.py`

Tracks fixture condition and brand compliance. Identifies damaged shelving, outdated signage, and non-standard fixtures requiring replacement.

## Related Skills

- [store-replenishment](../store-replenishment/SKILL.md) — Shelf stock levels affect compliance
- [assortment-planning](../assortment-planning/SKILL.md) — Planogram changes with new product intake
- [promo-planning](../promo-planning/SKILL.md) — Display allocation for promotional items

## Pitfalls

- **Photo quality**: Audit photos must meet minimum resolution and lighting standards. Provide a photography guide and sample images to store staff.
- **Reset fatigue**: Frequent planogram changes reduce compliance. Group resets to no more than once per quarter per section.
- **Fixture availability**: Planogram changes requiring new fixtures may be delayed if fixtures are out of stock. Maintain a fixture inventory buffer.
- **Local adaptation**: Some stores may need local deviations (e.g., smaller shelves, different traffic flow). Document approved deviations rather than forcing 100% compliance.
- **Photo validation accuracy**: AI-based photo validation is not 100% accurate. Implement a manual review queue for low-confidence detections.