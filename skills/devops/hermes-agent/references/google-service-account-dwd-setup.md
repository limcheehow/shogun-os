# Google Workspace Service Account — Domain-Wide Delegation

Allows the agent to impersonate ANY user on the domain for Gmail, Calendar, Drive, Docs, Sheets — no per-user OAuth needed.

## Admin Setup (one-time, Google Workspace admin required)

### Google Cloud Console

1. https://console.cloud.google.com/apis/credentials
2. Create Credentials → Service Account → name: `hermes-agent`
3. Skip "Grant access" → Done
4. Click service account → Keys → Add Key → Create New Key → JSON
5. Download the JSON key file
6. Enable APIs at https://console.cloud.google.com/apis/library:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Sheets API
   - Google Docs API
   - People API

### Google Workspace Admin Console

1. https://admin.google.com → Security → API Controls → Domain-wide Delegation
2. Add new → paste the service account's `client_id` (from JSON key)
3. Scopes (one per line):

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/calendar
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/documents
https://www.googleapis.com/auth/contacts
```

4. Authorize

## Agent-Side (to be built after admin setup)

The existing `google_api.py` uses OAuth user credentials — doesn't support service accounts. A thin wrapper is needed:

```python
from google.oauth2.service_account import Credentials

def get_impersonated_credentials(user_email):
    return Credentials.from_service_account_file(
        'service-account-key.json',
        scopes=['https://www.googleapis.com/auth/calendar', ...],
        subject=user_email  # impersonate ANY @example.com user
    )
```

Then build Google API services with `subject=<user@domain.com>` to act as that user.

## Priority

1. **Drive** — view docs for any team member
2. **Calendar** — create events on anyone's calendar
3. **Gmail** — send as any user

## Profile Mapping

Each Hermes profile gets the same service account key. The impersonated user is determined at API call time, not at auth time.

| Profile | Imports as |
|---------|-----------|
| marketing-manager (Haiku) | marketing-lead@example.com for Drive/Calendar |
| hr-manager (Kizuna) | hr@example.com for Drive/Calendar |
| product-manager (Taiko) | cheehow@example.com for Drive/Calendar |