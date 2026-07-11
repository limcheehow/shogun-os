# SA-DWD Usage Examples

Direct Python access via service account + domain-wide delegation. Use this when `google_api.py` doesn't yet support `--subject`, or when you need fine-grained control.

## Pattern

```python
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

KEY_PATH = "~/.hermes/service-account-key.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
]

def get_service(api, version, subject_email):
    creds = Credentials.from_service_account_file(
        KEY_PATH, scopes=SCOPES, subject=subject_email
    )
    return build(api, version, credentials=creds)
```

## Gmail — Read inbox

```python
service = get_service("gmail", "v1", "kunna@your-domain.com")
msgs = service.users().messages().list(
    userId="me", maxResults=5, labelIds=["INBOX"]
).execute()

for m in msgs.get("messages", []):
    msg = service.users().messages().get(
        userId="me", id=m["id"], format="metadata",
        metadataHeaders=["From", "Subject", "Date"]
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    print(f"  {headers.get('From')} — {headers.get('Subject')}")
```

## Gmail — Send

```python
import base64
from email.mime.text import MIMEText

service = get_service("gmail", "v1", "your-user@your-domain.com")

msg = MIMEText("Email body text")
msg["to"] = "recipient@example.com"
msg["subject"] = "Hello from Hermes"
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

service.users().messages().send(
    userId="me", body={"raw": raw}
).execute()
```

## Calendar — List

```python
service = get_service("calendar", "v3", "your-user@your-domain.com")
events = service.events().list(
    calendarId="primary", maxResults=10, singleEvents=True,
    orderBy="startTime"
).execute()
for ev in events.get("items", []):
    print(f"  {ev['summary']} — {ev['start'].get('dateTime', ev['start'].get('date'))}")
```

## Drive — Search

```python
service = get_service("drive", "v3", "your-user@your-domain.com")
results = service.files().list(
    q="mimeType='application/pdf'",
    pageSize=10,
    fields="files(id, name, mimeType, modifiedTime)"
).execute()
for f in results.get("files", []):
    print(f"  {f['name']} ({f['id']})")
```

## Notes

- Only works for domain users (`@your-domain.com`). External `@gmail.com` accounts need their own OAuth flow.
- Scopes are gated by the list authorized in admin.google.com. If a call fails with 403, check the scope list.
- The service account key at `~/.hermes/service-account-key.json` must exist.