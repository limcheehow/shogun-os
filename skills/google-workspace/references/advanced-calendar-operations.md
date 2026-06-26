# Advanced Calendar Operations

This reference covers calendar operations beyond the basic CRUD in `google_api.py`. These require direct Google Calendar API calls using the existing OAuth token.

## Writing to Shared / Secondary Calendars

The `--calendar CALENDAR_EMAIL` flag works for both read and write operations, **but the shared calendar must have sufficient permissions**:

| Permission Level | Read | Write |
|-----------------|------|-------|
| See only free/busy | ✅ | ❌ |
| See all event details | ✅ | ❌ |
| Make changes to events | ✅ | ✅ |
| Make changes and manage sharing | ✅ | ✅ |

**Error signal**: `HttpError 403: "You need to have writer access to this calendar."`

**Fix**: Ask the user to upgrade the share permission in Google Calendar Settings → Share with specific people → change from "See all event details" to "Make changes to events".

### Creating events on a shared calendar

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
$GAPI calendar create \
  --summary "Meeting Title" \
  --start "2026-05-06T15:00:00+07:00" \
  --end "2026-05-06T18:00:00+07:00" \
  --calendar "work@company.com" \
  --location "199 Street, City" \
  --description "Details here"
```

## Declining Events (Not Just Deleting)

The `google_api.py` wrapper has create/delete/list but **no update/decline**. To decline events (set your response status to "No" without removing the event):

```python
import json, os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

token_path = os.path.expanduser("~/.hermes/google_token.json")
with open(token_path) as f:
    token_data = json.load(f)

creds = Credentials.from_authorized_user_info(
    token_data, scopes=["https://www.googleapis.com/auth/calendar"]
)

if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(token_path, "w") as f:
        json.dump(json.loads(creds.to_json()), f)

service = build("calendar", "v3", credentials=creds)
calendar_id = "target-calendar@email.com"  # or "primary"

# Get event, set responseStatus, update
event = service.events().get(calendarId=calendar_id, eventId=EVENT_ID).execute()
for att in event.get("attendees", []):
    if att.get("email") == "user@email.com":
        att["responseStatus"] = "declined"
        service.events().update(calendarId=calendar_id, eventId=event["id"], body=event).execute()
        break
```

**What this does**: Sets the user's response to "No" so the organizer sees the decline. The event stays on the calendar (normal Google behavior for group events).

**For events the user created**: Use the `delete` action or remove themselves as organizer first.

## Cross-Timezone Events

When the authenticated account is in one timezone (e.g., MYT +08:00) but events are in another (e.g., THA +07:00):

```bash
# THA timezone event
$GAPI calendar create \
  --summary "Client Meeting" \
  --start "2026-05-06T15:00:00+07:00" \
  --end "2026-05-06T18:00:00+07:00"

# MYT timezone event
$GAPI calendar create \
  --summary "Local meeting" \
  --start "2026-05-06T09:30:00+08:00" \
  --end "2026-05-06T10:30:00+08:00"
```

Always use explicit timezone offsets (`+08:00`, `+07:00`, or `Z` for UTC). The API stores the event with the given offset; Google Calendar displays it in the viewer's local time.

## Out of Office Events

Google Calendar has a special "Out of office" event type. These events:
- **Cannot have a description** — the API returns `400 malformedOutOfOfficeEvent: An out of office event must not have a description.`
- **Cannot have a location** set
- Appear with a special OOO indicator in the UI

If you need to update a multi-day OOO event with details, create separate events alongside it instead.

## Pitfalls

1. **Declined events still show in calendar list queries** — They remain visible because the event itself still exists; only the attendee's response status changed. This is correct behavior.
2. **Recurring event instances** — The event ID for a specific instance of a recurring event has the original event ID with a `_YYYYMMDDTHHMMSSZ` suffix. Declining an instance declines only that occurrence.
3. **Querying date-only vs datetime events** — The `start` field in JSON can be either a string (for all-day events: `"2026-05-06"`) or an object with `dateTime`/`timeZone` (for timed events). Always handle both:
   ```python
   start = event.get("start", "")
   time = start if isinstance(start, str) else start.get("dateTime", start.get("date", ""))
   ```
4. **Calendar ID from event data** — When listing events from a shared calendar, the `id` field is scoped to that calendar. Don't mix event IDs between calendars.
