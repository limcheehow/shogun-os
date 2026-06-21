# Cron Inventory

Every scheduled job across all profiles.

## Infrastructure Crons (Default Profile)

| Name | Schedule | Type | no_agent? | Skills | Purpose |
|------|----------|------|-----------|--------|---------|
| Email Collector | `*/30 * * * *` | deterministic | ✅ | — | Pull Gmail → digest files |
| Email Enrichment | `0 9,13,17 * * 1-5` | agent | ❌ | gbrain-operations | Read digest → update brain pages |
| Calendar Sync | `0 6 * * *` | deterministic | ✅ | — | Pull Calendar → daily files |
| Calendar Enrichment | `0 8 * * *` | agent | ❌ | gbrain-operations | Extract attendees → brain pages |
| Drive Sync | `0 12,16,20 * * 1-5` | deterministic | ✅ | — | Pull Drive docs → brain pages |
| Drive Enrichment | `0 13,17 * * 1-5` | agent | ❌ | gbrain-operations | Extract entities from new docs |
| Token Utilization | `0 8 * * 1` | deterministic | ✅ | — | Weekly AI spend report via Tokscale |
| DWD Token Watchdog | `0 6 * * *` | deterministic | ✅ | — | (Optional) Proactive DWD token refresh |

## Department Crons

### HR Manager (Jinzai)

| Name | Schedule | Type | Skills | Purpose |
|------|----------|------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | agent | task-management | Team standup |
| Candidate Pipeline | `0 10 * * 1` | agent | — | Review open roles, candidates |
| Recruitment GDrive Sync | `0 6 * * *` | deterministic | — | Sync CVs from Drive → brain |
| Jibble Attendance | `30 9 * * 1-5` | agent | jibble-time-tracking | Check late arrivals |
| Jibble Timesheet | `0 10 * * 1` | agent | jibble-time-tracking | Weekly hours roundup |

### Finance Manager (Koku)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |
| Daily Burn Rate | `0 8 * * *` | — | Track daily spend vs budget |
| Invoice Aging | `0 8 * * 1` | — | Review overdue invoices |
| Monthly P&L | `0 8 1 * *` | — | End-of-month profit & loss |
| Weekly Budget | `0 8 * * 1` | — | Weekly budget vs actuals |

### Project Manager (Gorobei)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |

### Procurement Manager (Kura)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |
| Contract Expiry | `0 9 * * 1` | — | Review expiring vendor contracts |

### Product Manager (Shi)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |
| Sprint Cycle | `0 9 * * 1` | task-management | Bi-weekly sprint review & planning |

### CRM Manager (Kizuna)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |
| Deal Activity Sync | `0 9-18 * * 1-5` | crm-deal-pipeline | Hourly deal check |
| Sales Pipeline | `0 9 * * 1` | crm-deal-pipeline | Weekly pipeline review |
| Weekly Summary | `0 17 * * 5` | — | End-of-week deal roundup |

### Marketing Manager (Haiku)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |

### Compliance Manager (Kata)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |

### Customer Support (Bōei)

| Name | Schedule | Skills | Purpose |
|------|----------|--------|---------|
| Daily Standup | `0 9 * * 1-5` | task-management | Team standup |

## Cron Count Summary

| Profile | Deterministic (no_agent) | Agent (LLM) | Total |
|---------|-------------------------|-------------|-------|
| default | 5 | 2 | 7 |
| hr-manager | 1 | 4 | 5 |
| finance-manager | — | 5 | 5 |
| project-manager | — | 1 | 1 |
| procurement-manager | — | 2 | 2 |
| product-manager | — | 2 | 2 |
| crm-manager | — | 4 | 4 |
| marketing-manager | — | 1 | 1 |
| compliance-manager | — | 1 | 1 |
| customer-support | — | 1 | 1 |
| **Total** | **6** | **23** | **29** |