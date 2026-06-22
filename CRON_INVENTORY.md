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
| finance-manager | Daily Burn Rate | Daily 8AM |
| finance-manager | Invoice Aging | Mon 8AM |
| finance-manager | Monthly P&L | 1st of month 8AM |
| finance-manager | Weekly Budget | Mon 8AM |
| procurement-manager | Contract Expiry | Mon 9AM |
| product-manager | Sprint Cycle | Bi-weekly Mon |
| hr-manager | Jibble Attendance | Weekdays 9:30AM |
| hr-manager | Jibble Timesheet | Weekly Mon 10AM |

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