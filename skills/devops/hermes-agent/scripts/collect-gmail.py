#!/usr/bin/env python3
"""
Collect recent Gmail into ~/brain/data/email/ as gbrain-indexable markdown.
Reads from the same OAuth token as gmail-triage.py.
"""
import json, os, sys, datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN = os.getenv("GMAIL_TOKEN", os.path.expanduser("~/.hermes/gmail_token.json"))
OUTDIR = os.getenv("EMAIL_OUTDIR", os.path.expanduser("~/brain/data/email"))
MAX_EMAILS = int(os.getenv("EMAIL_MAX", "50"))
MAX_AGE_HOURS = int(os.getenv("EMAIL_MAX_AGE_HOURS", "168"))  # 7 days

def get_service():
    with open(TOKEN) as f:
        creds = Credentials.from_authorized_user_info(json.load(f))
    if not creds.valid:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)

def clean(text):
    if not text:
        return ""
    import re
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", text)
    text = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]", text)
    return text[:2000]

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    service = get_service()
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=MAX_AGE_HOURS)
    cutoff_epoch = int(cutoff.timestamp())

    results = service.users().messages().list(
        userId="me", maxResults=MAX_EMAILS,
        q=f"after:{cutoff_epoch}",
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        print("No recent emails found.")
        return

    written = 0
    for msg in messages:
        try:
            detail = service.users().messages().get(
                userId="me", id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
        except Exception as e:
            print(f"  skip {msg['id']}: {e}", file=sys.stderr)
            continue

        headers = {}
        for h in detail.get("payload", {}).get("headers", []):
            headers[h["name"].lower()] = h["value"]

        from_addr = headers.get("from", "unknown")
        subject = headers.get("subject", "(no subject)")
        date_str = headers.get("date", "")
        snippet = detail.get("snippet", "")

        ts = int(detail.get("internalDate", 0)) // 1000
        ts_str = datetime.datetime.utcfromtimestamp(ts).strftime("%Y%m%d%H%M")
        snippet_short = "".join(c if c.isalnum() else "-" for c in (snippet[:20] or "email"))
        slug = f"email-{ts_str}-{snippet_short.lower()}"

        md = f"""---
title: "{subject}"
type: email
date: {date_str}
from: {from_addr}
gmail_id: {msg["id"]}
tags: [email, gmail]
---

# {subject}

**From:** {from_addr}
**Date:** {date_str}
**Labels:** {', '.join(detail.get('labelIds', []))}

{clean(snippet)}
"""
        outpath = os.path.join(OUTDIR, f"{slug}.md")
        with open(outpath, "w") as f:
            f.write(md)
        written += 1

    print(f"Collected {written} emails -> {OUTDIR}")

if __name__ == "__main__":
    main()