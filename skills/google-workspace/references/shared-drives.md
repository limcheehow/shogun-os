# Google Drive Shared Drives (Team Drives)

The `google_api.py` CLI does **not** support Shared Drives — none of the `drive`
subcommands pass `supportsAllDrives=True`. Files/folders residing in a Shared
Drive will return **404 Not Found** from `drive get`, `drive search`, `drive
upload`, etc.

## Quick detection

If `drive get FOLDER_ID` returns 404 but the folder URL works in a browser where
you can see it, it's almost certainly a Shared Drive folder.

Verify programmatically:

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json

with open(Path.home() / ".hermes" / "google_token.json") as f:
    data = json.load(f)

creds = Credentials(
    token=data["token"],  # Hermes uses 'token', not 'access_token'
    refresh_token=data["refresh_token"],
    token_uri="https://oauth2.googleapis.com/token",
    client_id=data["client_id"],
    client_secret=data["client_secret"],
)
service = build("drive", "v3", credentials=creds)

# The fix: supportsAllDrives=True
result = service.files().get(
    fileId="FOLDER_ID",
    fields="id,name,mimeType,driveId,parents,webViewLink",
    supportsAllDrives=True
).execute()

print(f"Name: {result['name']}")
print(f"Drive ID: {result.get('driveId')}")  # Non-None = Shared Drive
```

## Required flags per operation

| Operation | Flag needed | Notes |
|-----------|-------------|-------|
| `files().get()` | `supportsAllDrives=True` | Single-file metadata |
| `files().list()` | `supportsAllDrives=True`, `includeItemsFromAllDrives=True` | Listing/searching |
| `files().create()` | `supportsAllDrives=True` | Upload to shared drive |
| `files().update()` | `supportsAllDrives=True` | Modify shared drive file |
| `files().delete()` / trash | `supportsAllDrives=True` | Delete from shared drive |
| `drives().list()` | None needed | List available shared drives |

## Listing available Shared Drives

```python
drives = service.drives().list(pageSize=10).execute()
for d in drives.get("drives", []):
    print(f"  {d['name']} (id: {d['id']})")
```

## Sync script pattern

For recurring folder sync to a Shared Drive, see `scripts/isms-drive-sync.py` in
the Hermes scripts directory for a complete example:
- One-way mirror (local → Drive) with MD5-based change detection
- Auto-creates subfolder structure
- Prunes stale files from Drive
- State file for incremental sync tracking

Key pattern: always use `supportsAllDrives=True` on every API call, and
`includeItemsFromAllDrives=True` on `files().list()` calls.

## Pitfall: Token key name

The Hermes `google_token.json` uses `"token"` for the access token, **not**
`"access_token"` as the google-auth-library docs suggest. When building
`Credentials` objects manually, use:

```python
Credentials(token=data["token"], ...)  # ✓ correct
Credentials(token=data["access_token"], ...)  # ✗ KeyError
```