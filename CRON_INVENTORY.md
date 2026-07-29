# Cron Inventory

Every scheduled job across all profiles.

## Infrastructure Crons (Default Profile)

| Name | Schedule | Type | no_agent? | Skills | Purpose |
|------|----------|------|-----------|--------|---------|
| **brain-ingest-gmail** | `*/30 * * * *` | deterministic | ✅ | — | Gmail triage via SA-DWD — label inbox, priority score, batch rotate (3 batches) |
| **brain-ingest-calendar** | `0 6 * * *` | deterministic | ✅ | — | Collect all 10 team members' calendar events via SA-DWD |
| **brain-ingest-pipeline** | `0 9,13,17 * * 1-5` | agent | ❌ | brain-ingest-pipeline, profile-enrichment, gbrain-operations, brain-compliance | 5-phase pipeline: ROUTE → BRIDGE → ENRICH → VALIDATE |
| Drive Sync | `0 12,16,20 * * 1-5` | deterministic | ✅ | — | Pull Drive docs → brain pages |
| Drive Enrichment | `0 13,17 * * 1-5` | agent | ❌ | gbrain-operations | Extract entities from new docs |
| Token Utilization | `0 8 * * 1` | deterministic | ✅ | — | Weekly AI spend report via Tokscale |
| DWD Token Watchdog | `0 6 * * *` | deterministic | ✅ | — | (Optional) Proactive DWD token refresh |

> **Removed:** Old `email-collector`, `calendar-sync`, `email-enrichment`, `calendar-enrichment` — replaced by the unified brain ingest pipeline.
> **Removed:** `Google Token Auto-Refresh` — not needed with SA-DWD (service accounts don't expire like OAuth).

## Department Scrum Crons

Every department profile uses the **3-tier scrum pattern** from `skills/department-scrum/`. Weekdays only.

| Profile | 9am | 11am | 5pm | Holiday Gate |
|---|---|---|---|---|
| **All** | `send-scrum-dms.py --profile <profile>` (no_agent) | `check-scrum-replies.py warn --profile <profile>` (agent) | `check-scrum-replies.py report --profile <profile>` (agent) | `0 0 * * *` (agent) |

Cron templates at `skills/department-scrum/templates/` — copy and fill placeholders for each profile.

## Extra Department Crons (beyond scrum)

| Profile | Extra Cron | Schedule |
|---------|-----------|----------|
| hr-manager | Candidate Pipeline | Mon 10AM |
| hr-manager | Recruitment GDrive Sync | Daily 6AM |
| crm-manager | Deal Activity Sync | Hourly 9-18 weekdays |
| crm-manager | Sales Pipeline | Mon 9AM |
| crm-manager | Weekly Summary | Fri 5PM |
| finance-manager | Daily Burn Rate | Daily 8AM (skill: `cash-runway-forecasting`) |
| finance-manager | Invoice Aging | Mon 8AM (skill: `ar-credit-control`) |
| finance-manager | Weekly Budget / Pulse | Mon 8AM (skill: `weekly-pulse-report`) |
| finance-manager | Monthly P&L / Board Report | 1st of month 8AM (skill: `monthly-board-report`) |
| procurement-manager | Contract Expiry | Mon 9AM |
| product-manager | Sprint Cycle | Bi-weekly Mon |
| hr-manager | Time Tracking Attendance | Weekdays 9:30AM |
| hr-manager | Time Tracking Timesheet | Weekly Mon 10AM |

## Manufacturing Industry Crons

These profiles deploy only when `--industry manufacturing` is selected:

| Profile | Cron | Schedule | Type |
|---------|------|----------|------|
| production-manager (Kojo) | Daily Production Schedule | `0 6 * * *` | deterministic (no_agent) |
| production-manager (Kojo) | OEE Tracking | `0 * * * *` | deterministic (no_agent) |
| quality-manager (Kensa) | Inspection Dashboard | `0 7 * * *` | deterministic (no_agent) |
| maintenance-manager (Shuri) | PM Schedule | `0 6 * * *` | deterministic (no_agent) |
| warehouse-manager (Soko) | Inventory Status | `0 6 * * *` | deterministic (no_agent) |
| hse-manager (Anzen) | Safety Walk Schedule | `0 8 * * 1` | deterministic (no_agent) |

## Retail Industry Crons

These profiles deploy only when `--industry retail` is selected:

| Profile | Cron | Schedule | Type |
|---------|------|----------|------|
| stores-manager (Tenpo) | Daily Sales Report | `0 6 * * *` | deterministic (no_agent) |
| stores-manager (Tenpo) | Staff Scheduling | `0 8 * * 1` | deterministic (no_agent) |
| merchandising-manager (Shohin) | Slow-Movers Report | `0 6 * * 1` | deterministic (no_agent) |
| merchandising-manager (Shohin) | Vendor Contract Expiry | `0 9 * * 1` | deterministic (no_agent) |
| ecommerce-manager (Denshi) | New Orders Check | `0 9-18 * * 1-5` | deterministic (no_agent) |
| ecommerce-manager (Denshi) | Listing Compliance | `0 7 * * *` | deterministic (no_agent) |
| crm-retail-manager (Kokyaku) | Points Expiry Review | `0 6 * * *` | deterministic (no_agent) |
| supplychain-manager (Ryutsu) | Replenishment Orders | `0 6 * * *` | deterministic (no_agent) |
| vm-manager (Hyoji) | Planogram Compliance Audit | `0 7 * * 1` | deterministic (no_agent) |

## Shared Script Crons (from `scripts/`)

These scripts are shared across profiles and run via the default profile's cron infrastructure:

| Script | Schedule | Type | Purpose |
|--------|----------|------|---------|
| **email-classify-cron-run.py** | `*/30 * * * *` | deterministic (no_agent) | Classify new email batches, tag categories, detect high-risk items |
| **gmail-draft.py** | On-demand (CLI) | — | Create Gmail drafts via API (never sends) |
| **support-email-poller.py** | `0 9-18 * * 1-5` | deterministic (no_agent) | Poll support mailbox, create/update tickets, detect customer replies |
| **session-db-health-check.sh** | `0 7 * * *` | deterministic (no_agent) | Check Postgres/SQLite health + gateway processes |
| **brain_compliance_helper.py** | On-demand (imported) | — | Shared module for orphan prevention + compliance enforcement |

> **Note:** `email-classify-cron-run.py` replaces the legacy `classify-emails-batch.sh` and `classify-emails-batch-v2.sh` (archived in `scripts/.archived/`).
> `gmail-draft.py` replaces the legacy `gmail-draft-batch.py` (archived in `scripts/.archived/`).

## Cron Count Summary

| Profile | Deterministic (no_agent) | Agent (LLM) | Total |
|---------|-------------------------|-------------|-------|
| default | **5** (3 pipeline + drive + token) | **3** (1 pipeline + drive enrich + ???) | **8** |
| hr-manager | **2** (1 scrum + 1 extra) | **5** (3 scrum + 2 extra) | **7** |
| finance-manager | **1** (1 scrum) | **6** (3 scrum + 3 extra) | **7** |
| project-manager | **1** (1 scrum) | **3** (3 scrum) | **4** |
| procurement-manager | **1** (1 scrum) | **4** (3 scrum + 1 extra) | **5** |
| product-manager | **1** (1 scrum) | **4** (3 scrum + 1 extra) | **5** |
| crm-manager | **1** (1 scrum) | **6** (3 scrum + 3 extra) | **7** |
| marketing-manager | **1** (1 scrum) | **3** (3 scrum) | **4** |
| compliance-manager | **1** (1 scrum) | **3** (3 scrum) | **4** |
| customer-support | **1** (1 scrum) | **3** (3 scrum) | **4** |
| **Total** | **15** | **39** | **54** |

> **Note:** 3-tier scrum = 9am (no_agent) + 11am (agent) + 5pm (agent). Holiday gate optional via midnight cron.
>
> Default profile counts: 3 pipeline crons (gmail, calendar, pipeline agent) + 2 drive crons + token + watchdog = 8 total.