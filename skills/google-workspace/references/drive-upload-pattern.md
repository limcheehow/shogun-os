# Drive Upload Pattern

Uploading a local file to a Google Drive folder via the Drive API.

## When to Use

Any workflow where you need to persist a local file (receipt photo, generated report, exported data) to Google Drive and get back a shareable link.

## Script

The `drive_upload.py` script at `receipt-to-sheet/scripts/drive_upload.py` is a ready-to-use implementation. Reuses the same OAuth token from `google-workspace` setup.

Usage:
```bash
python /path/to/drive_upload.py <local_file_path> --folder-id <FOLDER_ID>
```

Returns JSON: `{id, name, webViewLink}`

## Manual Implementation (if writing a custom script)

```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Authenticate (reuse google-workspace token)
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

creds = Credentials.from_authorized_user_file(
    "~/.hermes/google_token.json",
    ["https://www.googleapis.com/auth/drive.file"]
)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build("drive", "v3", credentials=creds)

# Upload
media = MediaFileUpload("/path/to/file.png", resumable=True)
file = service.files().create(
    body={"name": "filename.png", "parents": ["FOLDER_ID"]},
    media_body=media,
    fields="id, name, webViewLink"
).execute()

drive_link = f"https://drive.google.com/open?id={file['id']}"
```

## Key Details

- **Scope required**: `https://www.googleapis.com/auth/drive.file` (creates files it can manage; cannot list/delete files it didn't create)
- **Folder ID**: From the Drive folder URL — `https://drive.google.com/drive/folders/1ABC123...` the `1ABC123...` part is the folder ID.
- **Resumable upload**: Good for larger files (photos, PDFs) — the `MediaFileUpload` with `resumable=True` handles chunked uploads automatically.
- **webViewLink**: Not always returned on Drive API v3 `files().create()` for all file types. Fallback: construct `https://drive.google.com/open?id={file_id}` manually.
- **Duplicate names**: Drive allows multiple files with the same name in the same folder — no conflict error.