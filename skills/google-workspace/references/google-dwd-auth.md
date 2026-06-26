# Google Domain-Wide Delegation (DWD) Auth

Alternative to individual OAuth. A service account impersonates a Workspace user — no user consent screen, no refresh token drift, no 90-day testing expiry.

## When to Use DWD vs Individual OAuth

| Situation | Use |
|-----------|-----|
| Personal Google account | Individual OAuth (DWD requires Workspace) |
| Single user, quick setup | Individual OAuth |
| Production / multi-profile | **DWD** — one key, all profiles |
| Team deployment | **DWD** — just change `subject` |
| Pipelines without user presence | **DWD** — `creds.refresh()` always works |
| Google Workspace org | **DWD** — admin enables once |

## DWD Pattern (vs OAuth)

**Individual OAuth** (what setup.py does):
```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
creds = Credentials.from_authorized_user_file("~/.hermes/google_token.json", SCOPES)
creds.refresh(Request())  # may fail if refresh token expired
```

**DWD** (service account impersonation):
```python
from google.oauth2 import service_account
import google.auth.transport.requests
creds = service_account.Credentials.from_service_account_file(
    "~/.hermes/secrets/google-dwd-sa.json",
    scopes=SCOPES,
    subject="cheehow@gotapway.com"  # Workspace user to impersonate
)
creds.refresh(google.auth.transport.requests.Request())
# creds.token is now valid for ~1 hour
# creds.refresh() always works — no user interaction
```

**Key differences:**
- DWD: `creds.refresh()` never fails (service account has permanent credentials)
- OAuth: `creds.refresh()` may fail if the refresh token was revoked or expired
- DWD: No `~/.hermes/google_token.json` — the SA key file IS the credential
- DWD: Scopes are set at Workspace Admin Console level AND in the Python code

## Setup

See `~/company-os/recipes/google-dwd.md` for the full playbook. Summary:

1. Create service account in Google Cloud Console → download JSON key
2. Enable DWD in Workspace Admin Console → add client ID + scopes
3. Save key to `~/.hermes/secrets/google-dwd-sa.json`
4. Verify: `creds.refresh(google.auth.transport.requests.Request())` returns a token

## Usage in Scripts

```python
import os
from google.oauth2 import service_account
import google.auth.transport.requests

SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

creds = service_account.Credentials.from_service_account_file(
    SA_PATH, scopes=SCOPES, subject="cheehow@gotapway.com"
)
creds.refresh(google.auth.transport.requests.Request())

# Use creds.token directly or pass to googleapiclient
from googleapiclient.discovery import build
service = build("gmail", "v1", credentials=creds)
```

## Multi-Scope Management

The DWD token is scoped to EXACTLY the scopes passed to `from_service_account_file`. If you need different scopes (e.g., gmail in one script, calendar in another), call `from_service_account_file` separately for each — each call generates a token with only those scopes.

For a combined token (all scopes at once):
```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    # etc.
]
```

The Workspace Admin Console DWD entry must have ALL of these scopes authorized, even if a single script only uses a subset.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `invalid_scope` | Scope not authorized in Admin Console | Add scope to DWD entry |
| `403: Not Authorized` | Subject email not in Workspace domain | Check `subject` parameter |
| `Could not determine OAuth client` | Using numeric Unique ID instead of OAuth Client ID | In SA details → Advanced settings → copy OAuth 2.0 Client ID |
| Token works in terminal but not cron | Cron PATH missing google-auth | Use absolute Python path or activate venv in cron script |

## Related

- `~/company-os/recipes/google-dwd.md` — full setup playbook
- `~/company-os/recipes/token-watchdog.md` — optional proactive refresh
- `~/company-os/recipes/email-to-brain.md` — DWD variant example
- `~/company-os/recipes/calendar-to-brain.md` — DWD variant example