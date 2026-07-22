# Manufacturing Vertical — Implementation Plan

> **Goal:** Reorganize Company OS into shared + industry vertical architecture, then build the manufacturing vertical with 5 new profiles, 10 new skills, and ERP/MES connectors.

**Architecture:** `shared/` profiles (every company needs them) + `industries/{general,manufacturing,...}/` (pick one or more). The installer prompts for industry type and deploys the right set.

**Current state:** 10 flat profiles in `PROFILE_CATALOG.md`, all skills in `skills/`, all recipes in `recipes/`.
**Target state:** Profiles split into `shared/` and `industries/manufacturing/`. Skills split the same way.

---

## Phase 1: Reorganize Existing Repo Structure

### Task 1: Create industry directory structure

```bash
mkdir -p industries/general/profiles
mkdir -p industries/manufacturing/profiles
mkdir -p industries/manufacturing/skills
mkdir -p industries/manufacturing/recipes
mkdir -p profiles/shared
```

### Task 2: Move shared profiles into profiles/shared/

Move the 8 universal profiles:
- `hr-manager` → `profiles/shared/hr-manager/`
- `finance-manager` → `profiles/shared/finance-manager/`
- `crm-manager` → `profiles/shared/crm-manager/`
- `marketing-manager` → `profiles/shared/marketing-manager/`
- `compliance-manager` → `profiles/shared/compliance-manager/`
- `coding-agent` → `profiles/shared/coding-agent/`
- `support-manager` → `profiles/shared/support-manager/`
- `procurement-manager` → `profiles/shared/procurement-manager/`

### Task 3: Move general-industry profiles into industries/general/

Move the 2 profiles specific to general/services companies:
- `project-manager` → `industries/general/profiles/project-manager/`
- `product-manager` → `industries/general/profiles/product-manager/`

### Task 4: Update SOUL.md files

Update each SOUL.md to reference the new profile directory structure. No persona changes — just path references.

---

## Phase 2: Create Manufacturing Profiles

### Task 5: Create production-manager profile (Kōjō — 工場)

**Files:**
- Create: `industries/manufacturing/profiles/production-manager/SOUL.md`
- Create: `industries/manufacturing/profiles/production-manager/config.example.yaml`
- Create: `industries/manufacturing/profiles/production-manager/.env.example`
- Create: `industries/manufacturing/profiles/production-manager/SETUP.md`

**SOUL.md persona:**
```
Kōjō (工場 — "Factory"). The one who runs the production floor.
Every work order, every machine, every shift — Kōjō knows the status.
Not an engineer who designs — the one who makes.

Role: Production Manager — factory floor operations, OEE tracking,
work order management, production scheduling, yield monitoring.

Voice: Direct, data-driven, shift-aware. Talks in OEE percentages,
work order counts, and bottleneck alerts. "Line 3 down 14 min.
OEE at 72%. Need maintenance on the conveyor."

Brain source: production/
Skills: production-oee, work-order-tracking, erp-connector, mes-connector
```

### Task 6: Create quality-manager profile (Kensa — 検査)

**SOUL.md persona:**
```
Kensa (検査 — "Inspection"). The one who guards the standard.
Every batch, every defect, every NCR — Kensa tracks it.
Not the one who makes — the one who decides if it ships.

Role: Quality Manager — QC inspections, NCR management, CAPA,
lot traceability, ISO compliance.

Voice: Precise, standards-first, escalation-aware. "Batch 4045:
3% defect rate. NCR-2026-089 opened. Hold pending disposition."

Brain source: quality/
Skills: quality-ncr, quality-capa, inspection-dashboard
```

### Task 7: Create maintenance-manager profile (Shūri — 修理)

**SOUL.md persona:**
```
Shūri (修理 — "Repair"). The one who keeps the factory running.
Every breakdown, every PM, every spare part — Shūri owns it.
The factory runs through Shūri's tools.

Role: Maintenance Manager — preventive maintenance, breakdown
response, spare parts, MTBF/MTTR, equipment lifecycle.

Voice: Urgency-aware, metric-driven. "Compressor #3: 2,400 hrs
since last PM. Schedule next Thursday. 2 spare belts in stock."

Brain source: maintenance/
Skills: maintenance-pm, maintenance-downtime, cmms-connector
```

### Task 8: Create warehouse-manager profile (Sōko — 倉庫)

**SOUL.md persona:**
```
Sōko (倉庫 — "Warehouse"). The one who knows what's where.
Every pallet, every bin, every shipment — Sōko tracks it.
Nothing moves in or out without Sōko knowing.

Role: Warehouse Manager — inventory, raw materials, WIP,
finished goods, shipping, receiving, cycle counts.

Voice: Quantity-aware, location-specific. "RM-4422: 124 units
at Bin A-12. Reorder at 50. Lead time 7 days."

Brain source: warehouse/
Skills: warehouse-inventory, shipment-tracking, wms-connector
```

### Task 9: Create hse-manager profile (Anzen — 安全)

**SOUL.md persona:**
```
Anzen (安全 — "Safety"). The one who protects.
Every near-miss, every permit, every incident — Anzen tracks it.
Safety is not a priority — it's a precondition.

Role: HSE Manager — incident reporting, safety walks, permit
to work, environmental monitoring, regulatory compliance.

Voice: Serious, compliance-first, preventative. "Near-miss
2026-07-21: unguarded conveyor at Line 2. CAPA opened.
Safety walk scheduled for Friday."

Brain source: hse/
Skills: hse-incident, hse-permit, hse-environmental
```

---

## Phase 3: Create Manufacturing Skills

### Task 10: production-oee skill

**Files:**
- Create: `industries/manufacturing/skills/production-oee/SKILL.md`
- Create: `industries/manufacturing/skills/production-oee/scripts/calculate-oee.py`

**SKILL.md content:**
- Calculates OEE = Availability × Performance × Quality
- Reads machine counters from MES connector or manual entry
- Generates daily OEE report with trend, top losses, recommendations
- Configurable target OEE (default 85%)

### Task 11: work-order-tracking skill

**Files:**
- Create: `industries/manufacturing/skills/work-order-tracking/SKILL.md`
- Create: `industries/manufacturing/skills/work-order-tracking/scripts/track-orders.py`

**SKILL.md content:**
- Reads work orders from ERP connector
- Tracks status: Released → In Progress → Completed → Closed
- Reports WIP, backlog, on-time delivery rate
- Alerts on overdue orders

### Task 12: quality-ncr skill

**Files:**
- Create: `industries/manufacturing/skills/quality-ncr/SKILL.md`
- Create: `industries/manufacturing/skills/quality-ncr/scripts/manage-ncr.py`

**SKILL.md content:**
- NCR creation with defect type, severity, disposition
- Disposition options: Use-as-is, Rework, Scrap, Return-to-vendor
- Closure tracking with root cause and corrective action
- NCR aging report, top defect Pareto

### Task 13: quality-capa skill

**Files:**
- Create: `industries/manufacturing/skills/quality-capa/SKILL.md`
- Create: `industries/manufacturing/skills/quality-capa/scripts/manage-capa.py`

**SKILL.md content:**
- CAPA lifecycle: Open → Investigation → Action Plan → Implementation → Effectiveness Check → Closed
- Root cause analysis (5 Whys, Fishbone)
- Effectiveness check with verification steps
- CAPA aging and closure rate dashboard

### Task 14: maintenance-pm skill

**Files:**
- Create: `industries/manufacturing/skills/maintenance-pm/SKILL.md`
- Create: `industries/manufacturing/skills/maintenance-pm/scripts/pm-schedule.py`

**SKILL.md content:**
- PM schedule generation from equipment database
- Due/overdue PM tracking
- Work order generation for each PM task
- PM compliance rate (done on time / total due)

### Task 15: maintenance-downtime skill

**Files:**
- Create: `industries/manufacturing/skills/maintenance-downtime/SKILL.md`
- Create: `industries/manufacturing/skills/maintenance-downtime/scripts/downtime-tracking.py`

**SKILL.md content:**
- Unplanned downtime event logging
- Pareto analysis by equipment, reason, shift
- MTBF and MTTR calculation
- Downtime cost estimation

### Task 16: warehouse-inventory skill

**Files:**
- Create: `industries/manufacturing/skills/warehouse-inventory/SKILL.md`
- Create: `industries/manufacturing/skills/warehouse-inventory/scripts/inventory-status.py`

**SKILL.md content:**
- Inventory levels by category (raw, WIP, finished)
- Aging analysis (slow-moving, dead stock)
- Reorder point alerts
- Cycle count scheduling and variance reporting

### Task 17: hse-incident skill

**Files:**
- Create: `industries/manufacturing/skills/hse-incident/SKILL.md`
- Create: `industries/manufacturing/skills/hse-incident/scripts/incident-report.py`

**SKILL.md content:**
- Incident types: Near-miss, First Aid, Medical Treatment, Lost Time Injury, Fatality
- Severity matrix (Probability × Consequence)
- Investigation workflow with root cause and corrective actions
- Leading/lagging indicator dashboard

### Task 18: erp-connector skill

**Files:**
- Create: `industries/manufacturing/skills/erp-connector/SKILL.md`
- Create: `industries/manufacturing/skills/erp-connector/scripts/odoo-connector.py`
- Create: `industries/manufacturing/skills/erp-connector/scripts/erpnext-connector.py`
- Create: `industries/manufacturing/skills/erp-connector/scripts/erp-interface.py`

**SKILL.md content:**
- Generic ERP connector framework
- Adapters for Odoo (XML-RPC), ERPNext (Frappe REST), SAP B1 (Service Layer)
- Reads: work orders, BOMs, inventory levels, production orders, purchase orders
- Writes: work order status updates, inventory adjustments, quality results
- All credentials via env vars (never hardcoded)

### Task 19: mes-connector skill

**Files:**
- Create: `industries/manufacturing/skills/mes-connector/SKILL.md`
- Create: `industries/manufacturing/skills/mes-connector/scripts/ignition-connector.py`
- Create: `industries/manufacturing/skills/mes-connector/scripts/modbus-reader.py`

**SKILL.md content:**
- MES/SCADA data ingestion
- Adapters for Ignition/Inductive Automation (MQTT + REST)
- Modbus TCP for direct PLC reads
- Reads: machine states, production counts, downtime events, quality metrics
- Data format: standardized JSON schema for all connectors

---

## Phase 4: Update Installer & Documentation

### Task 20: Update PROFILE_CATALOG.md

Restructure into:
- Shared profiles (8)
- General industry profiles (2)
- Manufacturing industry profiles (5)

### Task 21: Update CRON_INVENTORY.md

Add manufacturing cron jobs:
- Daily production schedule (Kōjō — 6am)
- OEE tracking (Kōjō — hourly)
- PM schedule (Shūri — 6am)
- Inventory status (Sōko — 6am)
- HSE incident report (Anzen — daily)

### Task 22: Update install.sh

Add industry selection prompt:
```bash
echo "Select your industry:"
echo "  1) General (services, consulting, software)"
echo "  2) Manufacturing (factory, production, OEM)"
read -p "Choice [1]: " INDUSTRY
INDUSTRY=${INDUSTRY:-1}
```

### Task 23: Update verify-install.sh

Add verification for manufacturing profiles, skills, and connectors.

### Task 24: Update README.md

Add manufacturing section to the quick start, contents, and skills tables.

---

## Phase 5: Execution Order

```
Phase 1 (reorg):
  Task 1 → Task 2 → Task 3 → Task 4

Phase 2 (profiles):
  Task 5 → Task 6 → Task 7 → Task 8 → Task 9

Phase 3 (skills):
  Task 10 → Task 11 → Task 12 → Task 13 → Task 14
  Task 15 → Task 16 → Task 17 → Task 18 → Task 19

Phase 4 (docs + installer):
  Task 20 → Task 21 → Task 22 → Task 23 → Task 24
```

Tasks within each phase are independent (parallelizable).
Tasks across phases have dependencies (Phase 1 before Phase 2 before Phase 3 before Phase 4).

---

## Verification

1. `cd /home/tapway/company-os && python3 -m pytest tests/ -v` — all tests pass
2. `ls industries/manufacturing/profiles/` — 5 profiles exist
3. `ls industries/manufacturing/skills/` — 10 skills exist
4. `python3 scripts/verify-install.sh --quick` — no errors
5. Each SKILL.md has valid YAML frontmatter
6. No Tapway-specific references in any new files