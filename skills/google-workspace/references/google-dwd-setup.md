# Google DWD (Domain-Wide Delegation) Setup Playbook

Service account impersonation for automated Google API access — no user OAuth consent screens, no expiring refresh tokens.

## Prerequisites

- Google Workspace Admin Console access (you need to enable DWD)
- A Google Cloud project (free, any project works)

## Step 1: Create the Service Account

```bash
# 1. Go to https://console.cloud.google.com/apis/credentials
# 2. Click "+ CREATE CREDENTIALS" → "Service Account"
# 3. Name: "hermes-agent" (or whatever you like)
# 4. Click "CREATE AND CONTINUE" (no roles needed)
# 5. Click "DONE"
```

The service account gets an email like: `hermes-agent@<project>.iam.gserviceaccount.com`

## Step 2: Download the Service Account Key

```bash
# 1. In the service account list, click the three dots → "Manage keys"
# 2. "ADD KEY" → "Create new key"
# 3. Key type: JSON
# 4. Download and save to:
mkdir -p ~/.hermes/secrets
# Move the downloaded JSON to:
mv ~/Downloads/<project>-<hash>.json ~/.hermes/secrets/google-dwd-sa.json
```

## Step 3: Enable DWD in Google Workspace Admin Console

```bash
# 1. Go to https://admin.google.com → Security → API controls
# 2. Under "Domain-wide delegation", click "Add new"
# 3. Client ID: Copy from the service account page in GCP Console
#    (it's listed as "Unique ID" on the service account details page,
#    or in the downloaded JSON as "client_id")
# 4. OAuth scopes: Add ONLY the scopes you need (least privilege):
#    https://www.googleapis.com/auth/gmail.readonly
#    https://www.googleapis.com/auth/calendar.readonly
#    https://www.googleapis.com/auth/drive.readonly
#    https://www.googleapis.com/auth/spreadsheets
#    https://www.googleapis.com/auth/documents
#    https://www.googleapis.com/auth/contacts.readonly
# 5. Click "AUTHORIZE"
```

> ⚠️ **Minimum scopes per recipe:**
> - email-to-brain: `gmail.readonly`, `gmail.modify`
> - calendar-to-brain: `calendar.readonly`, `calendar.events.readonly`
> - drive-to-brain: `drive.readonly`, `documents.readonly`
> - slides-deck-gen: `presentations`
> Add scopes as you add recipes, don't pre-authorize everything.

## Step 4: Test the Impersonation

```bash
python3 << 'EOF'
import json, os
from google.oauth2 import service_account
import google.auth.transport.requests

key_path = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

creds = service_account.Credentials.from_service_account_file(
    key_path, scopes=SCOPES, subject="cheehow@gotapway.com"
)
creds.refresh(google.auth.transport.requests.Request())

print(f"Access token: {creds.token[:40]}...")
print(f"Expires: {creds.expiry}")
print("DWD setup: ✅ Working")
EOF
```

## Usage Pattern

Every Google API call uses the same pattern — no `google_token.json` needed:

```python
from google.oauth2 import service_account
import google.auth.transport.requests

KEY = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_dwd_creds(user="cheehow@gotapway.com"):
    creds = service_account.Credentials.from_service_account_file(
        KEY, scopes=SCOPES, subject=user
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds
```

The `subject` field controls **which user** you're impersonating. To access a
different user's Gmail/Calendar/Drive, just change the subject:

```python
creds = get_dwd_creds("sarah@gotapway.com")  # Sarah's data
```

## Token Watchdog (for Legacy Scripts That Expect a Static Token File)

If you have scripts that read `~/.hermes/google_token.json` and can't be
rewritten to use the DWD pattern, set up a no_agent cron that pre-populates
the token file from DWD credentials before they expire:

**Script** (`~/.hermes/scripts/google-dwd-refresh.sh`):
```bash
#!/bin/bash
python3 << 'PYEOF'
import json, os
from google.oauth2 import service_account
import google.auth.transport.requests

key_path = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
# If you need all scopes the original OAuth token had, list them here
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/contacts.readonly",
]

creds = service_account.Credentials.from_service_account_file(
    key_path, scopes=SCOPES, subject="cheehow@gotapway.com"
)
creds.refresh(google.auth.transport.requests.Request())

# Write to the file legacy scripts expect
token_path = os.path.expanduser("~/.hermes/google_token.json")
token_data = {
    "token": creds.token,
    "refresh_token": None,  # DWD doesn't use refresh tokens
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": "service-account-dwd",
    "client_secret": None,
    "scopes": SCOPES,
    "expiry": creds.expiry.isoformat()
}
with open(token_path, "w") as f:
    json.dump(token_data, f, indent=2)

print(f"✅ DWD token refreshed — expires {creds.expiry}")
PYEOF
```

**Cron job**:
```bash
hermes cron create \
  --name "Google DWD Token Refresh" \
  --schedule "*/30 * * * *" \
  --script google-dwd-refresh.sh \
  --deliver local \
  --no-agent
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `403: domain-wide delegation disabled` | DWD not enabled in Admin Console → Step 3 |
| `403: Not Authorized to Access This Resource` | Service account's Client ID not in DWD allowlist → Step 3 |
| `invalid_scope` | Scope not authorized for DWD → add it in Step 3 |
| Service account not found | GCP project may be deleted/suspended → check console |
| `impersonation failed` | The `subject` email must be in the same Google Workspace domain |
| Token refresh fails silently | Check `~/.hermes/secrets/google-dwd-sa.json` exists and is valid JSON |