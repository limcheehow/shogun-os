# IRM/DRM-Restricted Google Drive Files

## Overview

Google Workspace organizations can apply **Information Rights Management (IRM)** policies to files, blocking export, download, print, and copy operations while still allowing in-browser viewing. This creates a situation where the user can see the file but all API-based export/download endpoints return `403`.

## Detection

### Response headers

When an export endpoint returns 403, check for:

```
access-disabled-code: '2'
```

This is the strongest signal that the file has IRM restrictions.

### Response body

The 403 HTML page contains a `ppConfig` JavaScript object:

```javascript
window['ppConfig'] = {
  productName: '26981ed0d57bbad37e728ff58134270c',
  deleteIsEnforced: false,
  sealIsEnforced: false,
  heartbeatRate: 0.5,
  ...
};
```

The presence of `productName`, `sealIsEnforced`, and `heartbeatRate` indicates Google's DRM infrastructure is in play.

### COMPASS cookie

The 403 response sets a `COMPASS` cookie scoped to the file's path:

```
Set-Cookie: COMPASS=apps-spreadsheets=...; Domain=.docs.google.com; Path=/spreadsheets/d/{FILE_ID}/...; Secure; HttpOnly; SameSite=none
```

## Endpoint Behavior

| Endpoint | Status | Meaning |
|----------|--------|---------|
| `sheets.googleapis.com/v4/spreadsheets/{ID}` | `400` | File exists but is an XLSX (not native Sheet) |
| `sheets.googleapis.com/v4/spreadsheets/{ID}/values/...` | `400` | Same — Sheets API can't process Office files |
| `drive.googleapis.com/drive/v3/files/{ID}` | `404` | **False negative** — Drive API can't find files owned by other accounts |
| `drive.googleapis.com/drive/v3/files/{ID}?alt=media` | `404` | Same false negative |
| `drive.googleapis.com/drive/v3/files/{ID}/export` | `404` | Same false negative |
| `docs.google.com/spreadsheets/d/{ID}/export?format=csv` | `403` | Blocked by IRM |
| `docs.google.com/spreadsheets/d/{ID}/gviz/tq?tqx=out:csv` | `403` | Blocked by IRM |
| `docs.google.com/spreadsheets/d/{ID}/pub?output=csv` | `403` | Blocked by IRM |
| `docs.google.com/spreadsheets/d/{ID}/edit` | `200` (sign-in page) | Browser redirect — needs interactive session |
| OAuth Bearer to `/edit` | `302` → sign-in | Redirected because non-API endpoint doesn't accept Bearer tokens |
| `drive.googleapis.com/drive/v3/files?q=sharedWithMe=true` | `200` | Lists shared files including IRM-protected ones — confirms file exists |

## Workarounds

### 1. IMPORTRANGE (recommended)

IRM restrictions typically block **API export** but allow **server-to-server data sharing** within Google's infrastructure. `IMPORTRANGE()` is a view operation, not an export operation, and runs on Google's servers — so it can bypass the restriction.

**Step-by-step:**

1. **Create a new native Google Sheet** via the Sheets API
2. **Write `=IMPORTRANGE()` formula** referencing the restricted file
3. **User authorizes** — open the new sheet and click "Allow access"
4. **Read the data** via Sheets API

```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import json, os, time

tp = os.path.expanduser("~/.hermes/google_token.json")
with open(tp) as f:
    token_data = json.load(f)
creds = Credentials.from_authorized_user_info(token_data)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(tp, "w") as f:
        f.write(creds.to_json())

SOURCE_ID = "THE_RESTRICTED_FILE_ID"
sheets = build("sheets", "v4", credentials=creds)

# Step 1: Create new sheet
new_sheet = sheets.spreadsheets().create(
    body={
        "properties": {"title": "Imported from restricted file"},
        "sheets": [{"properties": {"title": "Data"}}]
    }
).execute()
new_id = new_sheet["spreadsheetId"]

# Step 2: Write IMPORTRANGE formula
# Try "Sheet1!A:Z" first; if sheet name unknown, try alternatives
formula = f'=IMPORTRANGE("https://docs.google.com/spreadsheets/d/{SOURCE_ID}", "Sheet1!A:Z")'
sheets.spreadsheets().values().update(
    spreadsheetId=new_id,
    range="Data!A1",
    valueInputOption="USER_ENTERED",
    body={"values": [[formula]]}
).execute()

# Step 3: Ask user to open and authorize
print(f"Open and authorize: https://docs.google.com/spreadsheets/d/{new_id}/edit")

# Step 4: After user authorizes, read
time.sleep(5)
result = sheets.spreadsheets().values().get(
    spreadsheetId=new_id, range="Data!A:Z"
).execute()
rows = result.get('values', [])
```

**Caveats:**
- Try multiple sheet names if "Sheet1" returns `#REF!` — the XLSX might use different tab names
- The `#REF!` error persists until the user clicks "Allow access" in the new sheet
- Write multiple formulas with different sheet names in parallel cells to discover the right one

### 2. Direct file copy (if permitted)

If the IRM policy allows copying:

```python
copied = service.files().copy(
    fileId=FILE_ID,
    body={"name": "Copy.xlsx"},
    supportsAllDrives=True
).execute()
```

This returns `404` if the Drive API can't see the file.

### 3. Ask user to export manually

If both workarounds fail, ask the user to open the file in their browser and do File → Download as Microsoft Excel (.xlsx), then share the file directly.

## Pitfalls

1. **Drive API 404 is NOT conclusive.** The Drive API returns 404 for files owned by other Google accounts even when the file is shared with you. Always try the Sheets API first for diagnostic value, and check `sharedWithMe=true` in your Drive search.

2. **Export 403 with COMPASS cookie means AUTH IS WORKING.** If you get a 403 that sets a COMPASS cookie, your OAuth token is authenticating correctly — the policy is the blocker, not the credentials.

3. **Re-authorizing doesn't fix IRM.** The IRM restriction is on the file, not on your token. Re-running OAuth setup won't help.

4. **IMPORTRANGE scope:** The formula accesses data from within Google's internal infrastructure, which means it can read data that API export endpoints can't. But it requires the user's one-time authorization click — there's no programmatic way to authorize it via API.