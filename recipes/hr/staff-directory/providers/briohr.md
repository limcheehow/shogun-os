# BrioHR — Staff Directory Provider (Reference Implementation)

## Overview

BrioHR is the first reference implementation of the HR staff directory provider contract. It syncs employee data and leave balances from BrioHR's API.

## Authentication

- Basic Auth with username + password
- Credentials stored in `~/.hermes/credentials/briohr.json`
- Format: `{"username": "...", "password": "...", "company": "..."}`

## API Endpoints

| Endpoint | Method | Returns |
|---|---|---|
| `/v2/api/external/reports/employee-list/download` | GET | CSV of all employees |
| `/v2/api/external/reports/leave-summaries/download` | GET | CSV of leave balances |

## Field Mapping

| BrioHR CSV Column | Contract Field | User Model Field |
|---|---|---|
| `email` | `email` | `User.email` |
| `name` (first + last) | `name` | `User.name` |
| `department` | `department` | `UserDepartment.name` |
| `employee_id` | `employee_id` | `User.employee_id` |
| `phone` | `phone` | `User.phone` |
| `manager_email` | `manager_email` | `User.manager_id` (resolved) |
| `title` / `position` | `title` | `UserDepartment.title` |

## Rate Limiting

BrioHR aggressively rate-limits on 403 responses. Use exponential backoff:
- Initial retry: 60s
- Max retry: 300s
- Max attempts: 3

## Portal Integration

The Shogun OS web portal calls this provider via `POST /api/staff/sync-briohr`. The endpoint:
1. Reads credentials from `~/.hermes/credentials/briohr.json`
2. Fetches employee CSV and leave CSV
3. Upserts Users by email
4. Generates brain pages at `shared/staff/{slug}.md`
5. Returns a summary

For manual sync, use the Staff Directory page → "Sync Now" button.

## Cron

Daily at 3am via Hermes cron or systemd timer:
```
0 3 * * * curl -X POST http://localhost:8787/api/staff/sync-briohr
```