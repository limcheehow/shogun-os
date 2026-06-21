---
id: token-watchdog
name: Google DWD Token Watchdog
version: 1.0.0
description: Proactive no-agent cron that refreshes the DWD service account token before expiry. Prevents silent auth failures in downstream cron jobs.
category: auth
requires:
  - google-dwd
secrets: []
health_checks:
  - type: script
    command: "python3 -c \"from google.oauth2 import service_account; import google.auth.transport.requests; import os; c=service_account.Credentials.from_service_account_file(os.path.expanduser('~/.hermes/secrets/google-dwd-sa.json'), scopes=['https://www.googleapis.com/auth/gmail.readonly'], subject='cheehow@gotapway.com'); c.refresh(google.auth.transport.requests.Request()); print('TOKEN_OK')\""
    label: "DWD token generation"
setup_time: 5 min
cost_estimate: "$0"
---

# Google DWD Token Watchdog

DWD tokens expire after 1 hour. However, every Google integration recipe in this directory uses `creds.refresh(google.auth.transport.requests.Request())` before every API call batch. The `google-auth` library auto-refreshes on demand — there's never a stale token.

**This watchdog is OPTIONAL.** It only matters if you have a script that:
- Caches the raw bearer token string in a file and reads it later
- Passes the token via env var to another process
- You've observed "Token expired" errors despite using `google-auth`

If all your scripts use `google-auth` properly (as the recipes do), skip this. The correct refresh happens at call time, every time.

## Architecture

```
default profile (cron)
  ↓ no_agent=true
Watchdog Script (30s execution)
  ↓
Refreshes DWD credentials via google-auth library
  ↓
stdout: "Token refreshed. Expires at HH:MM:SSZ"
  ↓
Delivered to user (optional — can silence via empty stdout)
```

## Prerequisites

- `google-dwd` recipe completed (service account key at `~/.hermes/secrets/google-dwd-sa.json`)

## Setup Flow

### Step 1: Create the Watchdog Script

Write to `~/.hermes/scripts/google-token-watchdog.sh`:

```bash
#!/bin/bash
# Google DWD Token Watchdog
# Refreshes the DWD service account impersonation token.
# Runs as no_agent=true cron — output is delivered verbatim.
# Returns empty stdout on success (silent), error text on failure (alert).

python3 << 'PYEOF'
import os, sys
from google.oauth2 import service_account
import google.auth.transport.requests

SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/contacts.readonly",
]

try:
    creds = service_account.Credentials.from_service_account_file(
        SA_PATH, scopes=SCOPES, subject="cheehow@gotapway.com"
    )
    creds.refresh(google.auth.transport.requests.Request())
    # Silent on success — watchdog pattern
except Exception as e:
    print(f"GOOGLE_DWD_ERROR: {e}", flush=True)
    sys.exit(1)
PYEOF
```

Make it executable:
```bash
chmod +x ~/.hermes/scripts/google-token-watchdog.sh
```

### Step 2: Verify the Script

```bash
~/.hermes/scripts/google-token-watchdog.sh
# Should produce no output (silent watchdog) — exit code 0
```

### Step 3: Create the Cron Job (if opted in)

In the **default** profile (shared infrastructure):

```bash
hermes cron create \
  --name "Google DWD Token Watchdog" \
  --schedule "0 6 * * *" \
  --script google-token-watchdog.sh \
  --no-agent \
  --deliver local
```

| Parameter | Value | Why |
|-----------|-------|-----|
| `--script` | `google-token-watchdog.sh` | Path relative to `~/.hermes/scripts/` |
| `--no-agent` | true | Script-only, no LLM tokens burned |
| `--deliver` | `local` | Silent on success, only alerts on error |
| `--schedule` | `0 6 * * *` | Daily at 6AM — once is enough as belt-and-suspenders |
| Profile | **default** | Shared infrastructure, all profiles benefit |

## What Happens

- **Token still valid**: Script exits 0, no output, no delivery. Silent.
- **Token error**: Script prints `GOOGLE_DWD_ERROR: ...` with exit code 1. Cron delivers the error text so you know auth is broken.

## Cost

$0 — the script runs in under 1 second, no API calls, no LLM tokens.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Script errors on cron but works in terminal | The cron session may not find the Python path. Use absolute path to Hermes venv Python. |
| "Service account key not found" | The cron working directory differs. Use absolute path `os.path.expanduser("~/.hermes/secrets/...")` |