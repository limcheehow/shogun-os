---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Time Tracking Provider Contract

> **Standard tool names and response shapes for time tracking integrations.**
> Any provider that implements these tools can be plugged into any Hermes Agent profile.

## Tools

### tt_clock_in

Clock in a member with GPS location.

**Input:**
```json
{
  "memberId": "string (required)",
  "timestamp": "string (ISO 8601, default: now)",
  "latitude": "number (required)",
  "longitude": "number (required)",
  "note": "string (optional)"
}
```

**Output:**
```json
{
  "entryId": "string",
  "memberId": "string",
  "clockIn": "ISO 8601 timestamp",
  "status": "active"
}
```

### tt_clock_out

Clock out a member.

**Input:**
```json
{
  "memberId": "string (required)",
  "timestamp": "string (ISO 8601, default: now)"
}
```

**Output:**
```json
{
  "entryId": "string",
  "memberId": "string",
  "clockIn": "ISO 8601 timestamp",
  "clockOut": "ISO 8601 timestamp",
  "totalMinutes": "number",
  "status": "completed"
}
```

### tt_current_status

Who's currently clocked in.

**Input:**
```json
{}
```

**Output:**
```json
{
  "active": [
    {
      "memberId": "string",
      "name": "string",
      "clockIn": "ISO 8601 timestamp",
      "elapsedMinutes": "number"
    }
  ]
}
```

### tt_get_entries

Get time entries for a date range.

**Input:**
```json
{
  "from": "string (YYYY-MM-DD, required)",
  "to": "string (YYYY-MM-DD, default: from)",
  "memberId": "string (optional)",
  "projectId": "string (optional)",
  "limit": "number (optional, default: 100)"
}
```

**Output:**
```json
{
  "entries": [
    {
      "entryId": "string",
      "memberId": "string",
      "memberName": "string",
      "projectId": "string",
      "projectName": "string",
      "clockIn": "ISO 8601",
      "clockOut": "ISO 8601",
      "totalMinutes": "number",
      "status": "active | completed | absent",
      "gpsLatitude": "number",
      "gpsLongitude": "number"
    }
  ],
  "total": "number"
}
```

### tt_get_members

List team members.

**Input:**
```json
{
  "status": "string (optional: active | inactive, default: active)"
}
```

**Output:**
```json
{
  "members": [
    {
      "memberId": "string",
      "name": "string",
      "email": "string",
      "role": "string",
      "status": "active | inactive",
      "hourlyRate": "number"
    }
  ]
}
```

### tt_get_projects

List projects.

**Input:**
```json
{
  "status": "string (optional: active | archived, default: active)"
}
```

**Output:**
```json
{
  "projects": [
    {
      "projectId": "string",
      "name": "string",
      "description": "string",
      "status": "active | archived",
      "budget": "number",
      "billable": "boolean"
    }
  ]
}
```

### tt_create_project

Create a new project.

**Input:**
```json
{
  "name": "string (required)",
  "description": "string (optional)",
  "budget": "number (optional)",
  "billable": "boolean (default: true)"
}
```

**Output:**
```json
{
  "projectId": "string",
  "name": "string",
  "status": "active"
}
```

### tt_update_project

Update an existing project.

**Input:**
```json
{
  "projectId": "string (required)",
  "name": "string (optional)",
  "description": "string (optional)",
  "budget": "number (optional)",
  "billable": "boolean (optional)",
  "status": "string (optional: active | archived)"
}
```

**Output:**
```json
{
  "projectId": "string",
  "name": "string",
  "status": "active | archived"
}
```

### tt_delete_project

Archive/disable a project.

**Input:**
```json
{
  "projectId": "string (required)"
}
```

**Output:**
```json
{
  "projectId": "string",
  "status": "archived"
}
```

## Error Response Shape

All tools return this on error:

```json
{
  "error": "string description",
  "code": "MISSING_FIELD | AUTH_FAILED | RATE_LIMITED | NOT_FOUND | PROVIDER_ERROR"
}
```

## Provider Requirements

To support this contract, a provider MUST implement:

| Tool | Priority | Required for MVP |
|------|----------|-----------------|
| `tt_current_status` | P0 | ✅ |
| `tt_get_entries` | P0 | ✅ |
| `tt_get_members` | P0 | ✅ |
| `tt_clock_in` | P1 | ❌ (client mobile app usually handles this) |
| `tt_clock_out` | P1 | ❌ |
| `tt_get_projects` | P1 | ❌ |
| `tt_create_project` | P2 | ❌ |
| `tt_update_project` | P2 | ❌ |
| `tt_delete_project` | P2 | ❌ |

Missing tools return `{"error": "Not implemented", "code": "NOT_FOUND"}`.