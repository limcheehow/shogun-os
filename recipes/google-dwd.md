---
id: google-dwd
name: Google Domain-Wide Delegation
version: 1.0.0
description: Service account impersonation for Google Workspace API access. Auth foundation for all Google integrations — no user-level OAuth tokens, no refresh token drift.
category: auth
requires: []
secrets:
  - name: GOOGLE_DWD_SA_PATH
    description: Absolute path to the DWD service account JSON key file
    where: ~/.hermes/secrets/google-dwd-sa.json — downloaded from Google Cloud Console
  - name: GOOGLE_DWD_SUBJECT
    description: Email address to impersonate via DWD
    where: your-user@your-domain.com — your Workspace account
  - name: GOOGLE_DWD_SCOPES
    description: Comma-separated OAuth scopes the service account is delegated for
    where: Set in Google Workspace Admin Console when enabling DWD
health_checks:
  - type: file_exists
    path: "$GOOGLE_DWD_SA_PATH"
    label: "Service account key file"
  - type: script
    command: "python3 -c \"from google.oauth2 import service_account; import google.auth.transport.requests; c=service_account.Credentials.from_service_account_file('$GOOGLE_DWD_SA_PATH', scopes=['https://www.googleapis.com/auth/gmail.readonly'], subject='$GOOGLE_DWD_SUBJECT'); c.refresh(google.auth.transport.requests.Request()); print('TOKEN_OK')\""
    label: "Token generation"
setup_time: 20 min
cost_estimate: "$0 (DWD is free, no API usage costs for most scopes)"
---

# Google Domain-Wide Delegation

Service account impersonation for Google Workspace. Every Google integration (email, calendar, drive, slides) depends on this being set up first. One-time config, then every recipe just uses `subject` impersonation.

## IMPORTANT: Instructions for the Agent

**You are the installer.** Follow these steps precisely.

**DWD vs Individual OAuth:**

| Aspect | Individual OAuth | DWD Service Account |
|--------|-----------------|---------------------|
| Setup effort | User clicks consent screen every 90 days (testing mode) | Admin enables DWD once, never expires |
| Token lifetime | ~7 days inactivity → dead | Service account never expires |
| Refresh mechanism | Refresh token may itself expire | `creds.refresh()` always works — no user interaction |
| Multiple users | Separate OAuth per user | Just change `subject` field |
| Multiple profiles | Token file per profile | One SA key shared across all profiles |
| Revocation | User revokes in Google Account | Admin revokes in Workspace Admin Console |
| **Winner** | Quick initial setup | **Production** |

**The DWD subject is the Google Workspace user account to impersonate.** All Google integrations impersonate this account.

## Architecture

```
Google Cloud Console:
  Project → Service Account (hermes-agent@your-project.iam.gserviceaccount.com  # Your service account email...)
  ↓
  Service Account Key JSON → ~/.hermes/secrets/google-dwd-sa.json
  ↓
Google Workspace Admin Console:
  Security → API Controls → Domain-Wide Delegation
  Add Client ID (from service account) + Scopes
  ↓
Hermes (any profile):
  python3 -c "
    creds = service_account.Credentials.from_service_account_file(
      SA_PATH, scopes=SCOPES, subject='your-user@your-domain.com'
    )
    creds.refresh(google.auth.transport.requests.Request())
    # Now use creds.token for any Google API call
  "
```

## Prerequisites

1. **Google Workspace admin access** — you need the ability to enable DWD
2. **Google Cloud Project** — any project works (can be shared with gbrain's project)
3. **`google-auth` Python library** — `pip install google-auth` (or it's available in the Hermes venv)

## Setup Flow

### Step 1: Create Service Account

```bash
# Go to Google Cloud Console:
# IAM & Admin → Service Accounts → Create Service Account
# Name: "Hermes Agent"
# Service account ID: hermes-agent (auto-generates email)
# No need to grant any GCP roles — DWD bypasses GCP IAM

# Download the JSON key file
# Service Accounts → Actions → Manage Keys → Add Key → JSON
# Save to:
mkdir -p ~/.hermes/secrets
# Move the downloaded JSON file to ~/.hermes/secrets/google-dwd-sa.json
```

**STOP until the key file is at `~/.hermes/secrets/google-dwd-sa.json`.**

### Step 2: Enable DWD in Google Workspace

1. Go to **Google Workspace Admin Console**: https://admin.google.com
2. Navigate: **Security → API Controls → Domain-wide delegation**
3. Click **"Add new"**
4. **Client ID**: Copy the service account's **OAuth Client ID** (NOT the numeric unique ID — it's under "Advanced settings" or "OAuth 2.0 Client ID" in the service account details)
5. **OAuth scopes**: Add all scopes needed by the recipes you'll use. For full coverage:

```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/documents
https://www.googleapis.com/auth/documents.readonly
https://www.googleapis.com/auth/presentations
https://www.googleapis.com/auth/contacts.readonly
```

**Minimum per recipe:**

| Recipe | Minimum scopes |
|--------|---------------|
| email-to-brain | `gmail.readonly` |
| calendar-to-brain | `calendar.readonly` |
| drive-to-brain | `drive.readonly`, `documents.readonly` |
| slides-deck-gen | `presentations` |
| All together | All of the above |

6. Click **Authorize**

**STOP until the delegation entry shows in Admin Console.**

### Step 3: Verify Token Generation

```bash
python3 << 'EOF'
import os, json
from google.oauth2 import service_account
import google.auth.transport.requests

SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

creds = service_account.Credentials.from_service_account_file(
    SA_PATH, scopes=SCOPES, subject="your-user@your-domain.com"
)
creds.refresh(google.auth.transport.requests.Request())
print(f"✅ Token generated: {creds.token[:20]}...")
print(f"✅ Expires: {creds.expiry}")
print(f"✅ Scopes: {creds.scopes}")
EOF
```

Expected output: `TOKEN_OK`. If this fails:
- **"Could not automatically determine OAuth client"** → You're using the numeric Unique ID instead of the OAuth Client ID. The two are different. Go to Service Account → "Advanced settings" → copy the **OAuth 2.0 Client ID** (looks like `1234567890-xxxxxxxx.apps.googleusercontent.com`)
- **"401 Unauthorized"** → The DWD scopes hasn't been authorized yet in Workspace Admin Console
- **"403 Not authorized to access this resource"** → The `subject` email is not in your Workspace domain, or DWD isn't enabled for this scope

### Step 4: Log Setup Completion

```bash
mkdir -p ~/.gbrain/integrations/google-dwd
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","event":"setup_complete","version":"1.0.0","status":"ok"}' >> ~/.gbrain/integrations/google-dwd/heartbeat.jsonl
```

Tell the user: "Google DWD is set up. The service account `hermes-agent@your-project.iam.gserviceaccount.com  # Your service account email...` can now impersonate `your-user@your-domain.com` for any authorized API scope. No more OAuth popups, no token expiry worries."

## Usage (Once Active)

In any Python script or cron job, the DWD token pattern is always:

```python
from google.oauth2 import service_account
import google.auth.transport.requests

SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SCOPES = ["https://www.googleapis.com/auth/CURRENT_SCOPE"]

creds = service_account.Credentials.from_service_account_file(
    SA_PATH, scopes=SCOPES, subject="your-user@your-domain.com"
)
creds.refresh(google.auth.transport.requests.Request())
# creds.token is a fresh bearer token, creds.expiry tells you when it expires
```

Every recipe in this directory starts with "Prerequisites: `google-dwd` recipe completed" — this is that prerequisite.

## Cron Integration

This recipe is **not a cron job itself** — it's infrastructure. But downstream recipes use this auth. The `token-watchdog` recipe (separate) handles proactive token refresh if needed.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `invalid_scope` | Scope not listed in DWD config in Admin Console. Re-check the scopes string — commas, no spaces. |
| `403: Not Authorized` | The `subject` email must be in your Workspace domain and DWD must be enabled for that scope. |
| Token expires in output sharing | DWD tokens still expire after 1 hour, but `creds.refresh()` always works — no user interaction needed. Just call it before every API call batch. |
| "Service account not found" | Wrong project. The service account exists in one GCP project; DWD must reference its Client ID. |