#!/usr/bin/env python3
"""
Collect recent/upcoming Google Calendar events from ALL team members' calendars
into ~/brain/data/calendar/ as gbrain-indexable markdown.

Uses SA-DWD (service account with domain-wide delegation) to access every
team member's primary calendar, matching the same account list as gmail-triage.
"""
import json, os, re, sys, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SA_KEY = os.path.expanduser("~/.hermes/service-account-key.json")
OUTDIR = os.path.expanduser("~/brain/data/calendar")
LOOKBACK_DAYS = 7
LOOKAHEAD_DAYS = 14
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Same account list as gmail-triage.py
ALL_ACCOUNTS = [
    "your-user@your-domain.com",
    "hana@your-domain.com",
    "sarah@your-domain.com",
    "kunna@your-domain.com",
    "anwar@your-domain.com",
    "liyana@your-domain.com",
    "syazwan@your-domain.com",
    "fitri@your-domain.com",
    "iskandar@your-domain.com",
    "ashraf@your-domain.com",
]

def short_name(email: str) -> str:
    name = email.split("@")[0]
    name_map = {
        "user": "Admin", "syazwan": "Syazwan", "fitri": "Fitri",
        "ashraf": "Ashraf", "iskandar": "Iskandar", "liyana": "Liyana",
        "hana": "Hana", "sarah": "Sarah", "kunna": "Kunnasilan",
        "anwar": "Anwar",
    }
    return name_map.get(name, name.capitalize())


def get_service_for(email: str):
    """Build Calendar API client impersonating the given user."""
    creds = service_account.Credentials.from_service_account_file(
        SA_KEY, scopes=SCOPES, subject=email
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def clean_pii(text: str) -> str:
    """Scrub emails and phone numbers from description."""
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", text)
    text = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]", text)
    return text[:1500]


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    now = datetime.datetime.utcnow()
    time_min = (now - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat() + "Z"
    time_max = (now + datetime.timedelta(days=LOOKAHEAD_DAYS)).isoformat() + "Z"

    total_written = 0
    total_accounts = 0
    errors = []

    for email in ALL_ACCOUNTS:
        try:
            service = get_service_for(email)
        except Exception as e:
            errors.append(f"{email}: auth error - {e}")
            continue

        try:
            events_result = service.events().list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
        except Exception as e:
            errors.append(f"{email}: list error - {e}")
            continue

        events = events_result.get("items", [])
        total_accounts += 1

        for ev in events:
            start = ev["start"].get("dateTime", ev["start"].get("date", "N/A"))
            end = ev["end"].get("dateTime", ev["end"].get("date", "N/A"))
            summary = ev.get("summary", "(no title)")
            description = ev.get("description", "")
            location = ev.get("location", "")
            attendees = [a.get("email", "") for a in ev.get("attendees", [])]
            hangout = ev.get("hangoutLink", "")
            meeting_link = ev.get("conferenceData", {}).get("entryPoints", [{}])[0].get("uri", "")

            # Clean PII
            if description:
                description = clean_pii(description)

            # Slug — include email suffix to avoid collisions
            slug_start = start[:10].replace("-", "") if start else "nodate"
            slug_title = "".join(c if c.isalnum() else "-" for c in (summary[:30] or "event"))
            account_tag = email.split("@")[0]
            slug = f"cal-{slug_start}-{slug_title.lower()}-{account_tag}"

            md = f"""---
title: "{summary}"
type: calendar-event
date: {start}
end: {end}
location: {location or 'N/A'}
link: {meeting_link or hangout or 'N/A'}
from: {email}
from_name: {short_name(email)}
attendees: [{', '.join(attendees[:10]) if attendees else ''}]
tags: [calendar, event, {account_tag}]
---

# {summary}

| Field | Value |
|---|---|
| **When** | {start} → {end} |
| **Calendar** | {short_name(email)} ({email}) |
| **Location** | {location or 'N/A'} |
| **Link** | {meeting_link or hangout or 'N/A'} |
| **Attendees** | {', '.join(attendees[:10]) if attendees else 'N/A'} |

{description if description else '*(No description)*'}
"""
            outpath = os.path.join(OUTDIR, f"{slug}.md")
            with open(outpath, "w") as f:
                f.write(md)
            total_written += 1

    print(f"Collected {total_written} events from {total_accounts}/{len(ALL_ACCOUNTS)} accounts → {OUTDIR}")
    if errors:
        print("\n⚠️ Errors:")
        for e in errors:
            print(f"  {e}")

    return total_written


if __name__ == "__main__":
    main()
