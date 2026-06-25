# Time Tracking Skill (Generic)

> **Works with any time tracking provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

This skill teaches the agent how to handle time tracking queries and workflows using standard `tt_*` tool names. It works identically whether the backend is Jibble, Kami, Hubstaff, or a custom provider — the MCP bridge translates.

## Prerequisites

- An MCP server named `time-tracking` configured in the profile's `config.yaml`
- The server exposes tools: `tt_current_status`, `tt_get_entries`, `tt_get_members`, `tt_get_projects`, `tt_clock_in`, `tt_clock_out`, `tt_create_project`, `tt_update_project`, `tt_delete_project`
- API key set in the profile's `.env` as `TT_API_KEY`

## Workflows

### "Who's clocked in today?"

1. Call `tt_current_status` via MCP
2. For each active member, get their name from `tt_get_members`
3. Calculate elapsed time from `clockIn` timestamp
4. Format:

   ```
   ✅ Currently Clocked In (3)
   ┌──────────┬────────────┬──────────┐
   │ Name     │ Since      │ Duration │
   ├──────────┼────────────┼──────────┤
   │ Alice    │ 08:45      │ 2h 15m   │
   │ Bob      │ 09:00      │ 2h 00m   │
   │ Charlie  │ 09:30      │ 1h 30m   │
   └──────────┴────────────┴──────────┘
   ```

5. Cross-reference against expected workforce from gbrain (optional)

### "Show yesterday's timesheet"

1. Calculate yesterday's date: `(today - 1 day)` in YYYY-MM-DD
2. Call `tt_get_entries(from=yesterday, to=yesterday)`
3. Group by member, calculate total hours per member
4. Flag anomalies: missing clock-out, zero hours, overtime (>10h)

### "Weekly attendance summary"

1. Calculate Monday-Sunday of last week
2. Call `tt_get_entries(from=mon, to=sun)`
3. Aggregate by member across the week
4. Expected hours per week: 40h (configurable)
5. Flag:
   - Missing days (no entry on a weekday)
   - Late arrivals (first clock-in after 9AM)
   - Overtime (>10h in a single day)
   - Short days (<4h without notice)

### "Create a new project"

1. Ask user for project name (and optionally description/budget)
2. Call `tt_create_project(name=..., description=..., budget=...)
3. Verify via `tt_get_projects`
4. Log the new project to gbrain under the department's source

### "Track GPS location for {member}"

1. On clock-in, `tt_clock_in` captures GPS coordinates
2. On `tt_get_entries`, GPS data is returned per entry
3. To check location: inspect `gpsLatitude` / `gpsLongitude` fields on entries
4. Cross-reference against known work sites in gbrain for geofence compliance

## Cron Job Template

**Daily attendance check** (weekdays 9:30AM):

```bash
hermes cron create \
  --name "Daily Attendance Check" \
  --schedule "30 9 * * 1-5" \
  --prompt "Run daily attendance check using tt_current_status and tt_get_entries. Report who's active, who's late, any anomalies." \
  --skills "time-tracking" \
  --deliver origin
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Tool tt_current_status not found` | MCP bridge not configured | Check `mcp_servers.time-tracking` in config.yaml |
| Empty member list | API key invalid or no members | Check `TT_API_KEY` in profile .env |
| GPS data missing | Provider doesn't support GPS or entry had no location | Check contract — only P0 tools are guaranteed |

## Adding a New Provider

If you're adding a new provider (not Jibble):

1. Create `~/.hermes/scripts/tt-bridge-<provider>.py`
2. Implement the 9 `tt_*` tools per [CONTRACT.md](CONTRACT.md)
3. Configure MCP:
   ```yaml
   mcp_servers:
     time-tracking:
       command: python3
       args: [~/.hermes/scripts/tt-bridge-<provider>.py]
       env:
         TT_API_KEY: "${TT_API_KEY}"
   ```
4. Set `TT_API_KEY` in the profile's `.env`
5. This skill works immediately — no changes needed