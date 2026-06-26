# Calendar-to-Brain via Direct OAuth

A standalone Node.js script that fetches Google Calendar events and creates daily markdown files in the brain directory — using the same `~/.hermes/google_token.json` from the Hermes Google Workspace OAuth setup.

## Why This Exists

The `google_api.py` CLI is good for one-off queries, but a dedicated sync script is better for:
- **Bulk historical backfill** — sync years of calendar data with smart chunking
- **Deterministic output** — daily markdown files, raw JSON preservation
- **Merge-with-existing** — update calendar data without overwriting manual notes
- **Scheduled runs** — cron-friendly, no interactive prompts

## Prerequisites

- Google OAuth already set up via `google-workspace` skill's `setup.py`
- Token at `~/.hermes/google_token.json` with `calendar` scope
- Node.js 18+

## The Script

**Location**: `~/brain/calendar-sync.mjs`

### Usage

```bash
# Sync last 7 days (default)
node ~/brain/calendar-sync.mjs

# Specific range
node ~/brain/calendar-sync.mjs --start 2026-01-01 --end 2026-06-30

# Specific calendar (shared work calendar)
node ~/brain/calendar-sync.mjs --calendar "cheehow@gotapway.com"
```

## How It Works

### Token Management
- Reads `~/.hermes/google_token.json`
- Auto-refreshes if token expires within 5 minutes
- Writes refreshed token back to the same file

### Smart Chunking
- Pre-2023: monthly chunks (sparse periods, fewer API calls)
- Post-2023: weekly chunks (dense periods, more granular)

### Attendee Filtering
- Filters out: conference rooms (`@resource.calendar.google.com`), mailing lists (`@group.calendar.google.com`), internal distros (`YC-SF-...`)
- Falls back to email prefix when display name is missing

### Pagination
- Max 250 events per API call
- Follows `nextPageToken` for large calendars

### Daily File Output
```markdown
## Calendar

# 2026-05-05 (Tuesday)

- **all-day** Home
- 9:00 AM-9:30 AM **Team Standup** — with Alice, Bob
- 2:00 PM-3:00 PM **Board Meeting** 📍 Office — with Diana, Eduardo
```

### Merge Logic
- If `## Calendar` section exists in the file → **replace only that section**, preserve all manual notes below `---`
- If no calendar section → **prepend** the calendar block
- If file doesn't exist → **create** fresh

### Raw Data
- Saved to `daily/calendar/.raw/Work-{start}-to-{end}.json`
- Contains full event objects including attendees, descriptions, locations

## Cron Setup

```bash
# Daily at 8 AM - sync yesterday
cd ~/brain && node calendar-sync.mjs --start $(date -d "yesterday" +%Y-%m-%d) --end $(date +%Y-%m-%d) --calendar "cheehow@gotapway.com"
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pure Node.js, no npm deps | Zero dependency management, works everywhere |
| Reads Hermes token directly | No duplicate OAuth setup, token stays in one place |
| `module` style Node.js (`import`/`export`) | Modern JS, matches gbrain conventions |
| Raw JSON alongside markdown | Enables re-processing without re-fetching |

## Pitfalls

- **Token scopes**: The token must include `https://www.googleapis.com/auth/calendar` scope. If running `setup.py --check` shows calendar scope missing, re-run OAuth setup with all scopes.
- **Work calendar sharing**: For non-primary calendars (e.g. work email), the calendar must be shared with the authenticated Google account. Use `--calendar "email@domain.com"`.
- **Rate limiting**: The script includes a 0.5s delay between API calls. For backfilling 5+ years, expect ~100-200 API calls over 2-3 minutes.
- **Date format**: All dates use the calendar owner's timezone for display. The raw data preserves full ISO 8601 timestamps.
