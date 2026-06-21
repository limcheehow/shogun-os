---
id: calendar-to-brain
name: Calendar-to-Brain
version: 1.0.0
description: Google Calendar events become searchable brain pages via Google DWD. Daily files with attendees, locations, and meeting prep context.
category: ingest
requires:
  - google-dwd
secrets: []
health_checks:
  - type: file_exists
    path: "$HOME/brain/daily/calendar/$(date +%Y)/$(date +%Y-%m-%d).md"
    label: "Today's calendar file"
setup_time: 20 min
cost_estimate: "$0"
---

# Calendar-to-Brain: Your Schedule Becomes Searchable Memory

Every calendar event becomes a searchable brain page. Your agent knows who you're meeting tomorrow, what you discussed last time, and what context matters. Meeting prep happens automatically because the brain already has the history.

## IMPORTANT: Instructions for the Agent

**You are the installer.** Follow these steps precisely.

**Why this matters:** Calendar data is the richest source of relationship history. Years of calendar data tells you who you've met with, how often, where, and with whom. When someone emails you, the brain already knows your meeting history. When you have a meeting tomorrow, the agent pulls attendee dossiers automatically.

**The output is daily markdown files:** One file per day at `~/brain/daily/calendar/{YYYY}/{YYYY-MM-DD}.md` with all events, attendees, and locations.

## Architecture

```
Google DWD (impersonate cheehow@gotapway.com)
  ↓ Calendar API (paginated)
Calendar Sync Script (deterministic Python)
  ↓ Outputs:
  ├── brain/daily/calendar/{YYYY}/{YYYY-MM-DD}.md   (daily event files)
  ├── brain/daily/calendar/.raw/events-{range}.json  (raw API responses)
  └── brain/daily/calendar/INDEX.md                  (date ranges + event counts)
  ↓
Agent reads daily files (cron enrichment job)
  ↓ Judgment calls:
  ├── Attendee enrichment (create/update brain pages for people)
  ├── Meeting prep (pull context before tomorrow's meetings)
  └── Pattern detection (meeting frequency, relationship temperature)
```

## Opinionated Defaults

**Daily file format:**
```markdown
# 2026-04-10 (Thursday)

- 09:00–09:30 **Team standup** — with Alice, Bob, Carol
- 10:00–11:00 **Board meeting** 📍 Office — with Diana, Eduardo
- 12:00–13:00 **Lunch with Pedro** 📍 Chez Panisse — with Pedro
```

All-day events listed first. Timed events sorted by start time.
Cancelled events skipped. Attendee names extracted (no email addresses in output).
Location with 📍 emoji.

## Prerequisites

1. `google-dwd` recipe completed (service account key at `~/.hermes/secrets/google-dwd-sa.json`)
2. Google Calendar API enabled in the Google Cloud project

## Setup Flow

### Step 1: Create the Calendar Sync Script

Write to `~/.hermes/scripts/calendar-sync.py`:

```python
#!/usr/bin/env python3
"""Calendar Sync — DWD variant. Deterministic Google Calendar → brain pages."""
import os, json, sys
from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
import google.auth.transport.requests
from googleapiclient.discovery import build

# ── Config ──────────────────────────────────
SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SUBJECT = "cheehow@gotapway.com"
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
OUTPUT_DIR = os.path.expanduser("~/brain/daily/calendar")
STATE_FILE = os.path.expanduser("~/.hermes/calendar-sync-state.json")
LOOKBACK_DAYS = 30  # how far back to sync on each run

# ── Auth ────────────────────────────────────
creds = service_account.Credentials.from_service_account_file(
    SA_PATH, scopes=SCOPES, subject=SUBJECT
)
creds.refresh(google.auth.transport.requests.Request())
service = build("calendar", "v3", credentials=creds)

# ── State ────────────────────────────────────
state = {"last_sync": None}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        state = json.load(f)

now = datetime.now(timezone.utc)
if state.get("last_sync"):
    time_min = datetime.fromisoformat(state["last_sync"])
else:
    time_min = now - timedelta(days=LOOKBACK_DAYS)

time_max = now + timedelta(days=30)  # sync upcoming events too

# ── Fetch events ────────────────────────────
events_by_date = {}
page_token = None

while True:
    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        pageToken=page_token,
        showDeleted=False
    ).execute()

    for event in events_result.get("items", []):
        start = event["start"].get("dateTime", event["start"].get("date"))
        date_key = start[:10]
        if date_key not in events_by_date:
            events_by_date[date_key] = []

        attendees = []
        for a in event.get("attendees", []):
            name = a.get("displayName") or a.get("email", "").split("@")[0]
            # Filter out conference rooms and mailing lists
            if not any(s in (a.get("email", "") or "") for s in [
                "@resource.calendar.google.com",
                "@group.calendar.google.com"
            ]):
                attendees.append(name)

        location = event.get("location", "")
        is_all_day = "dateTime" not in event["start"]

        events_by_date[date_key].append({
            "summary": event.get("summary", "(no title)"),
            "start": start,
            "end": event["end"].get("dateTime", event["end"].get("date")),
            "attendees": attendees,
            "location": location,
            "is_all_day": is_all_day,
            "html_link": event.get("htmlLink", ""),
        })

    page_token = events_result.get("nextPageToken")
    if not page_token:
        break

# ── Restore raw ──────────────────────────────
os.makedirs(f"{OUTPUT_DIR}/.raw", exist_ok=True)
with open(f"{OUTPUT_DIR}/.raw/events-{time_min.strftime('%Y%m%d')}-{time_max.strftime('%Y%m%d')}.json", "w") as f:
    json.dump({k: v for k, v in events_by_date.items()}, f, indent=2, default=str)

# ── Write daily files ────────────────────────
from datetime import datetime as dt

def format_time(iso_str):
    if not iso_str or "T" not in iso_str:
        return "all-day"
    try:
        t = dt.fromisoformat(iso_str)
        return t.strftime("%H:%M")
    except:
        return iso_str[:5]

weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

for date_key, events in sorted(events_by_date.items()):
    year = date_key[:4]
    dir_path = f"{OUTPUT_DIR}/{year}"
    os.makedirs(dir_path, exist_ok=True)
    file_path = f"{dir_path}/{date_key}.md"

    try:
        d = dt.strptime(date_key, "%Y-%m-%d")
        day_name = weekdays[d.weekday()]
    except:
        day_name = ""

    lines = [f"# {date_key} ({day_name})\n"]

    # All-day first
    all_day = [e for e in events if e["is_all_day"]]
    timed = [e for e in events if not e["is_all_day"]]

    for e in all_day:
        loc = f" 📍 {e['location']}" if e["location"] else ""
        ppl = f" — with {', '.join(e['attendees'])}" if e["attendees"] else ""
        lines.append(f"- **{e['summary']}**{loc}{ppl}")

    for e in sorted(timed, key=lambda x: x["start"]):
        time_str = f"{format_time(e['start'])}–{format_time(e['end'])}"
        loc = f" 📍 {e['location']}" if e["location"] else ""
        ppl = f" — with {', '.join(e['attendees'])}" if e["attendees"] else ""
        lines.append(f"- {time_str} **{e['summary']}**{loc}{ppl}")

    content = "\n".join(lines) + "\n"

    # Merge with existing file (preserve ## Notes sections)
    if os.path.exists(file_path):
        existing = open(file_path).read()
        if "## Notes" in existing or "## Calendar" in existing:
            # Replace ## Calendar section only
            if "## Calendar" in existing:
                before = existing.split("## Calendar")[0]
                after = existing.split("## Calendar")[1]
                if "## " in after[2:]:
                    next_section_idx = after.index("## ", 2)
                    after_part = after[next_section_idx:]
                else:
                    after_part = ""
                content = f"{before}## Calendar\n\n{content}{after_part}"
            else:
                content = f"## Calendar\n\n{content}\n---\n\n{existing}"
        else:
            content = f"## Calendar\n\n{content}\n"

    with open(file_path, "w") as f:
        f.write(content)

# ── Write INDEX.md ────────────────────────────
index_lines = ["# Calendar Index\n", f"Last sync: {now.isoformat()}\n", "\n## Events by Month\n"]
month_counts = {}
for date_key, events in events_by_date.items():
    month = date_key[:7]
    month_counts[month] = month_counts.get(month, 0) + len(events)
for month, count in sorted(month_counts.items()):
    index_lines.append(f"- **{month}**: {count} events")
with open(f"{OUTPUT_DIR}/INDEX.md", "w") as f:
    f.write("\n".join(index_lines) + "\n")

# ── Save state ────────────────────────────────
state["last_sync"] = now.isoformat()
with open(STATE_FILE, "w") as f:
    json.dump(state, f)

print(f"Synced {sum(len(v) for v in events_by_date.values())} events across {len(events_by_date)} days")
```

Make it executable:
```bash
chmod +x ~/.hermes/scripts/calendar-sync.py
```

### Step 2: Run First Sync

```bash
~/.hermes/scripts/calendar-sync.py
```

Verify:
```bash
ls ~/brain/daily/calendar/$(date +%Y)/
cat ~/brain/daily/calendar/$(date +%Y)/$(date +%Y-%m-%d).md
```

**STOP until the daily file shows real events with attendees.**

### Step 3: Historical Backfill

For initial setup, pull years of calendar history:

```bash
# Edit the LOOKBACK_DAYS in the script to 1825 (5 years), then:
~/.hermes/scripts/calendar-sync.py
# Then reset to LOOKBACK_DAYS=30 for ongoing sync
```

### Step 4: Import to gbrain

```bash
gbrain import ~/brain/daily/calendar/ --no-embed
gbrain embed --stale
```

Verify:
```bash
gbrain search "meeting" --limit 3
```

### Step 5: Create the Cron Jobs

Two crons in the **default** profile:

**Calendar sync** (daily at 6AM — catches new events before the day starts):
```bash
hermes cron create \
  --name "Calendar Sync" \
  --schedule "0 6 * * *" \
  --script calendar-sync.py \
  --no-agent \
  --deliver local
```

**Attendee enrichment** (daily at 8AM — enriches before morning briefing):
```bash
hermes cron create \
  --name "Calendar Attendee Enrichment" \
  --schedule "0 8 * * *" \
  --prompt "$(cat <<'PROMPT'
## Calendar Attendee Enrichment

Read today's calendar file at ~/brain/daily/calendar/$(date +%Y)/$(date +%Y-%m-%d).md
Also check tomorrow's file.

For each person appearing as an attendee:
1. Search gbrain: gbrain search "attendee name"
2. If they exist, update their timeline with the meeting
3. If they're notable (appears 2+ times or is a client) and have no page, create one
   with type: person, company: (if known), role: (if known)

Also check for recurring meetings with people you haven't met before.
Deliver a summary: "Enriched N attendees for today. M new person pages created."
PROMPT
)" \
  --skills "gbrain-operations" \
  --enabled-toolsets "terminal,file,search" \
  --deliver origin
```

### Step 6: Log Setup Completion

```bash
mkdir -p ~/.gbrain/integrations/calendar-to-brain-dwd
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","event":"setup_complete","version":"1.0.0","status":"ok"}' >> ~/.gbrain/integrations/calendar-to-brain-dwd/heartbeat.jsonl
```

## What the Agent Should Test After Setup

1. **Daily sync files:** Check that today's file exists and has events
2. **Merge preservation:** Add `## Notes` to a daily file manually. Run sync again. Verify notes preserved.
3. **All-day events:** Create one. Verify it appears first in the daily file.
4. **Cancelled events:** Cancel a meeting. Sync. Verify it doesn't appear.

## Cost

$0 — Calendar API is free within quotas.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No events returned | Check DWD auth. Check that the calendar has events. Check `timeMin`/`timeMax` range. |
| Attendee names missing | Google Calendar sometimes returns email instead of display name. The script extracts prefix after @. |
| Duplicate events | Script is idempotent — same date range = same output. Multiple runs overwrite, not append. |
| IRM-restricted attendees | Some resource calendars are blocked. The filter handles `@resource.calendar.google.com`. |