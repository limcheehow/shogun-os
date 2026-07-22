#!/usr/bin/env python3
"""
Collect recent/upcoming Google Calendar events into ~/brain/data/calendar/
as gbrain-indexable markdown.
"""
import json, os, sys, datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = os.getenv("GMAIL_TOKEN", os.path.expanduser("~/.hermes/gmail_token.json"))
OUTDIR = os.getenv("CAL_OUTDIR", os.path.expanduser("~/brain/data/calendar"))
LOOKBACK_DAYS = int(os.getenv("CAL_LOOKBACK", "7"))
LOOKAHEAD_DAYS = int(os.getenv("CAL_LOOKAHEAD", "14"))

def get_service():
    with open(TOKEN) as f:
        creds = Credentials.from_authorized_user_info(json.load(f))
    if not creds.valid:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    service = get_service()

    now = datetime.datetime.utcnow()
    time_min = (now - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat() + "Z"
    time_max = (now + datetime.timedelta(days=LOOKAHEAD_DAYS)).isoformat() + "Z"

    events_result = service.events().list(
        calendarId="primary", timeMin=time_min, timeMax=time_max,
        maxResults=100, singleEvents=True, orderBy="startTime",
    ).execute()

    events = events_result.get("items", [])
    if not events:
        print("No upcoming events found.")
        return

    written = 0
    for ev in events:
        start = ev["start"].get("dateTime", ev["start"].get("date", "N/A"))
        end = ev["end"].get("dateTime", ev["end"].get("date", "N/A"))
        summary = ev.get("summary", "(no title)")
        description = ev.get("description", "")
        location = ev.get("location", "")
        attendees = [a.get("email", "") for a in ev.get("attendees", [])]
        hangout = ev.get("hangoutLink", "")
        meeting_link = ev.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri", "")

        if description:
            import re
            description = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", description)
            description = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]", description)
            description = description[:1500]

        slug_start = start[:10].replace("-", "") if start else "nodate"
        slug_title = "".join(c if c.isalnum() else "-" for c in (summary[:30] or "event"))
        slug = f"cal-{slug_start}-{slug_title.lower()}"

        md = f"""---
title: "{summary}"
type: calendar-event
date: {start}
end: {end}
location: {location}
link: {meeting_link or hangout}
tags: [calendar, event]
---

# {summary}

| Field | Value |
|---|---|
| **When** | {start} -> {end} |
| **Location** | {location or 'N/A'} |
| **Link** | {meeting_link or hangout or 'N/A'} |
| **Attendees** | {', '.join(attendees[:10]) if attendees else 'N/A'} |

{description if description else '*(No description)*'}
"""
        outpath = os.path.join(OUTDIR, f"{slug}.md")
        with open(outpath, "w") as f:
            f.write(md)
        written += 1

    print(f"Collected {written} events -> {OUTDIR}")

if __name__ == "__main__":
    main()