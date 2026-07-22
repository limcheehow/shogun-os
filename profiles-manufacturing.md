# Shogun OS — Manufacturing Industry

> **5 dedicated department agents for factory, production, and OEM environments. Deployed alongside the 8 shared profiles for a total of 13 autonomous AI agents.**

---

## Overview

The manufacturing vertical adds 5 Samurai-themed department agents on top of the shared profiles (HR, Finance, Procurement, CRM, Marketing, Compliance, Support, Engineering). Together they cover the full manufacturing value chain: production, quality, maintenance, warehouse, and HSE.

**Deploy:**
```bash
./scripts/install.sh --deploy all --industry manufacturing
```

---

## Manufacturing Profiles

### Production — Kojo (工場 — "Factory")

| Field | Value |
|-------|-------|
| **Role** | Factory floor operations, OEE tracking, work order management |
| **gbrain source** | `production/` |
| **Skills** | `production-oee`, `work-order-tracking`, `erp-connector`, `mes-connector` |
| **Crons** | Daily production schedule (6AM), OEE tracking (hourly) |

**Persona:** Kojo runs the factory floor. Every work order, every machine, every shift — Kojo knows the status. Not the engineer who designs — the one who makes, at scale, on time.

### Quality — Kensa (検査 — "Inspection")

| Field | Value |
|-------|-------|
| **Role** | QC inspections, NCR management, CAPA, lot traceability |
| **gbrain source** | `quality/` |
| **Skills** | `quality-ncr`, `quality-capa`, `erp-connector` |
| **Crons** | Inspection dashboard (7AM) |

**Persona:** Kensa guards the standard. Every batch, every defect, every non-conformance — tracked, dispositioned, closed. Not the one who makes — the one who decides if it ships.

### Maintenance — Shuri (修理 — "Repair")

| Field | Value |
|-------|-------|
| **Role** | Preventive maintenance, breakdown response, spare parts |
| **gbrain source** | `maintenance/` |
| **Skills** | `maintenance-pm`, `maintenance-downtime`, `mes-connector` |
| **Crons** | PM schedule (6AM), real-time breakdown alerts |

**Persona:** Shuri keeps the factory running. Every breakdown, every PM, every spare part — owned. The factory runs through Shuri's tools.

### Warehouse — Soko (倉庫 — "Storehouse")

| Field | Value |
|-------|-------|
| **Role** | Inventory management, receiving/shipping, cycle counts |
| **gbrain source** | `warehouse/` |
| **Skills** | `warehouse-inventory`, `erp-connector` |
| **Crons** | Inventory status (6AM), reorder alerts |

**Persona:** Soko knows what's where and how much. Every pallet, every bin, every shipment — tracked. Nothing moves in or out without Soko knowing.

### HSE — Anzen (安全 — "Safety")

| Field | Value |
|-------|-------|
| **Role** | Incident reporting, safety inspections, permits, environmental |
| **gbrain source** | `hse/` |
| **Skills** | `hse-incident` |
| **Crons** | Safety walk schedule (weekly Mon) |

**Persona:** Anzen protects people and the environment. Every near-miss, every permit, every incident — tracked, investigated, closed. Safety is a precondition, not a priority.

---

## Manufacturing Skill Library

| Skill | Profile | What It Does |
|-------|---------|-------------|
| `production-oee` | Kojo | Calculates OEE (Availability x Performance x Quality). Daily reports with trend analysis, top 5 loss identification. Configurable target (default 85%). |
| `work-order-tracking` | Kojo | Work order lifecycle from release to completion. WIP, backlog, on-time delivery rate. ERP-connected. |
| `quality-ncr` | Kensa | NCR lifecycle with 4 dispositions (use-as-is / rework / scrap / RTV). Defect Pareto, aging report. |
| `quality-capa` | Kensa | CAPA lifecycle: Open → Investigate → Plan → Implement → Verify → Close. 5 Whys root cause analysis. Severity matrix. |
| `maintenance-pm` | Shuri | PM schedule with due/overdue tracking. Auto-generates work orders. PM compliance rate dashboard. |
| `maintenance-downtime` | Shuri | Unplanned downtime logging. Pareto by equipment/reason/shift. MTBF/MTTR calculation. |
| `warehouse-inventory` | Soko | Inventory levels by category (raw/WIP/finished). Aging analysis, reorder alerts, cycle counting. |
| `hse-incident` | Anzen | Incident types from near-miss to fatality. Severity matrix. Leading/lagging indicator dashboard. |
| `erp-connector` | All | Generic ERP framework. Adapters for Odoo (XML-RPC) and ERPNext (Frappe REST). Reads work orders, BOMs, inventory. |
| `mes-connector` | All | MES/SCADA ingestion. Adapters for Ignition (REST) and Modbus TCP (PLC registers). Reads machine states, counts, downtime. |

---

## Integrations

| System | Adapter | Technology | Dependencies |
|--------|---------|-----------|-------------|
| **Odoo** | `odoo_connector.py` | XML-RPC API | stdlib only |
| **ERPNext** | `erpnext_connector.py` | Frappe REST API | stdlib only |
| **Ignition SCADA** | `ignition_connector.py` | Gateway Script + REST API | stdlib only |
| **Modbus TCP PLC** | `modbus_reader.py` | Holding register reads | optional: pymodbus |

---

## Daily Workflow

```
6:00 AM  Kojo   → Daily production schedule from ERP, shift plan, materials verified
Hourly   Kojo   → OEE calculated from MES, bottlenecks flagged, yield checked
7:00 AM  Kensa  → Inspection dashboard, pending NCRs aged, CAPA effectiveness due
Realtime Shuri  → PM due flagged, breakdown alerts, spare parts low warning
6:00 AM  Soko   → Inventory snapshot, reorder alerts, cycle count assignments
Weekly   Anzen  → Incident review, safety walk closure, permit expiry checks
```

---

## ROI Impact

| Metric | Improvement | How |
|--------|:-----------:|-----|
| OEE | 20-35% | Real-time tracking identifies top 5 losses. Every 1% OEE gain = significant annual savings. |
| NCR Resolution | 40-60% faster | Automated disposition routing cuts from 2 days to 2 hours. |
| Unplanned Downtime | 30-50% less | Predictive PM scheduling + real-time alerts reduce emergency repairs. |
| Inventory | 15-25% reduction | Real-time visibility + reorder alerts eliminate stockouts and excess. |
| Incident Reporting | 50-70% faster | Automated workflow captures near-misses in minutes, tracks to closure. |
| Management Span | 3-5x increase | Each agent handles 3-5x the monitoring workload. 24/7 coverage. |

---

## Related Pages

- [Shared Profiles (Every Company)](README.md#shared-profiles-every-company)
- [General Industry Profiles](profiles-general.md)
- [PROFILE_CATALOG.md](PROFILE_CATALOG.md) — Full profile catalog
- [CRON_INVENTORY.md](CRON_INVENTORY.md) — All cron jobs
- [SETUP.md](SETUP.md) — Deployment playbook