# Shared Drive / Google Drive API Patterns

## Overview
When accessing files and folders in Google Shared Drives (team drives), standard Drive API calls fail with `404 File not found` even when the folder is shared with the authenticated account. You MUST use Shared Drive-specific parameters.

## Required Parameters for Shared Drives

Every Drive API call to a shared drive needs these extra parameters:

```python
# Python googleapiclient
drive.files().list(
    q="'FOLDER_ID' in parents and trashed=false",
    corpora="allDrives",                    # REQUIRED — search all drives, not just My Drive
    includeItemsFromAllDrives=True,         # REQUIRED — include shared drive items
    supportsAllDrives=True,                 # REQUIRED — acknowledge shared drive access
    pageSize=50,
    fields="files(id, name, mimeType, modifiedTime)"
).execute()

# Getting a file's metadata
drive.files().get(
    fileId="FILE_ID",
    fields="id, name, owners, mimeType",
    supportsAllDrives=True                  # REQUIRED
).execute()
```

## Without These Parameters

| Missing param | Error |
|--------------|-------|
| No params | `404 File not found: FOLDER_ID` |
| `supportsAllDrives=True` only | Works for `.get()` but not `.list()` |
| All three | ✅ Works |

## Reading Google Docs from Shared Drives

### Method 1: Google Docs API (REST, works)
Use direct HTTP calls with the access token — the googleapiclient Python library's `Docs API` doesn't support `supportsAllDrives` as a kwarg, but the raw REST API doesn't need it since the file access is authorized by the token:

```python
import urllib.request, json

access_token = creds.token  # from google.oauth2.credentials.Credentials
doc_id = "DOCUMENT_ID"

url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json"
})
with urllib.request.urlopen(req) as resp:
    doc_data = json.loads(resp.read())
```

### Method 2: Drive Export (works but some APIs don't support shared drive flag)
```python
# The googleapiclient export_media() doesn't accept supportsAllDrives
# Use direct REST instead:
url = f"https://www.googleapis.com/drive/v3/files/{doc_id}/export?mimeType=text/plain&supportsAllDrives=true"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
with urllib.request.urlopen(req) as resp:
    text = resp.read().decode("utf-8")
```

### Extracting text from Google Docs
```python
content = doc_data.get("body", {}).get("content", [])
text_parts = []
for elem in content:
    if "paragraph" in elem:
        for run in elem["paragraph"].get("elements", []):
            if "textRun" in run:
                text_parts.append(run["textRun"].get("content", ""))
full_text = "".join(text_parts)
```

## Common Pitfalls

1. **`googleapiclient` Docs API doesn't support `supportsAllDrives`** — Using `docs_service.documents().get(documentId=doc_id, supportsAllDrives=True)` throws `TypeError: Got an unexpected keyword argument supportsAllDrives`. Use raw REST calls instead.

2. **`drive.files().export_media()` also doesn't accept `supportsAllDrives`** — Same TypeError. Use raw REST via `urllib.request` with the export endpoint.

3. **Finding a shared folder** — `drive.files().get(fileId=id)` fails with 404 for shared drives unless you pass `supportsAllDrives=True`. Always use it when working with folders shared from another account.

4. **Listing files in a shared folder** — Must use all three: `corpora="allDrives"`, `includeItemsFromAllDrives=True`, `supportsAllDrives=True`.

## Detecting if a Folder is in a Shared Drive

If `drive.files().get()` returns a `driveId` field, it's a shared drive. You can also check by listing:

```python
results = drive.files().list(
    q="name contains 'Meeting' and mimeType='application/vnd.google-apps.folder'",
    corpora="allDrives",
    includeItemsFromAllDrives=True,
    supportsAllDrives=True,
    fields="files(id, name, owners, driveId)"
).execute()
```

## Slack Channel ID Resolution
To find a Slack channel ID by name when the messaging system's `send_message` doesn't return the raw ID, use the Slack API directly:
```python
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
url = "https://slack.com/api/conversations.list"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())
for ch in data["channels"]:
    if ch["name"] == "channel-name":
        print(ch["id"])  # e.g., C0B2Q32E60M
```
Note: Slack API calls may time out in restricted environments. Use short timeouts.
