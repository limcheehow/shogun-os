# Shared Drive / Shared Folder Access Patterns

Google Drive folders owned by another account or in a shared drive require special API parameters. Without these, the Drive API returns `404 File not found` even though the folder is visible to the user in the UI.

## The Problem

```python
# ❌ Fails for shared drives/folders
drive.files().get(fileId="SOME_FOLDER_ID").execute()
# → HttpError 404: File not found

drive.files().list(q="'FOLDER_ID' in parents").execute()
# → Returns [] (empty) even though files exist

drive.files().export_media(fileId=DOC_ID, mimeType="text/plain").execute()
# → TypeError: unexpected keyword arg
```

## The Fix: 3 Required Parameters

Every Drive API call against shared content needs all three:

```python
drive = build("drive", "v3", credentials=creds)

drive.files().list(
    q="'FOLDER_ID' in parents and trashed=false",
    corpora="allDrives",              # Search ALL drives, not just "My Drive"
    includeItemsFromAllDrives=True,    # Include shared drive items in results
    supportsAllDrives=True,            # Acknowledge the API supports this
    fields="files(id, name, mimeType, modifiedTime)"
).execute()

drive.files().get(
    fileId=FILE_ID,
    supportsAllDrives=True             # Required for individual file access too
).execute()
```

## The Docs API Exception

The Google Docs API (`docs.googleapis.com`) **does not** accept `supportsAllDrives` as a parameter — it raises a `TypeError`. To read Google Docs from shared drives, use one of these workarounds:

### Option A: Direct REST call (recommended)

Use the `urllib.request` library with the access token instead of the client library:

```python
import urllib.request, json

# Get token from credentials
access_token = creds.token  # or creds.token if using google.oauth2

# Read a document
url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
req = urllib.request.Request(url, headers={
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json"
})
with urllib.request.urlopen(req) as resp:
    doc_data = json.loads(resp.read())

# Extract text from the response body content
content = doc_data.get("body", {}).get("content", [])
text_parts = []
for elem in content:
    if "paragraph" in elem:
        for run in elem["paragraph"].get("elements", []):
            if "textRun" in run:
                text_parts.append(run["textRun"].get("content", ""))
full_text = "".join(text_parts)
```

### Option B: Drive export

Export the doc as plain text (this also works with shared drives since supportsAllDrives is accepted by the Drive API's export endpoint when called via REST):

```python
url2 = f"https://www.googleapis.com/drive/v3/files/{doc_id}/export?mimeType=text/plain&supportsAllDrives=true"
req2 = urllib.request.Request(url2, headers={"Authorization": f"Bearer {access_token}"})
with urllib.request.urlopen(req2) as resp:
    text = resp.read().decode("utf-8")
```

## Detecting Shared vs Personal Folders

```python
# List ONLY personal files (no shared drives)
drive.files().list(pageSize=10, orderBy="modifiedTime desc").execute()

# List files shared with the authenticated account
drive.files().list(q="sharedWithMe=true", pageSize=10).execute()

# Search across ALL drives including shared
drive.files().list(
    q="name contains 'Meeting'",
    corpora="allDrives",
    includeItemsFromAllDrives=True,
    supportsAllDrives=True
).execute()
```

## Common Failures

| Error | Cause | Fix |
|-------|-------|-----|
| `404 File not found` on a folder the user can see | Shared drive without proper params | Add `supportsAllDrives=True` |
| Empty results from `list()` when files exist | Missing `includeItemsFromAllDrives` | Add all 3 params |
| `TypeError: Got an unexpected keyword argument supportsAllDrives` | Using Docs API (not Drive API) | Use direct REST call (Option A above) |
| `HttpError 403 Insufficient Permission` | Missing `drive.readonly` or `drive` scope | Re-run OAuth with Drive scope added |

## Use Cases

- **Meeting minutes folder** shared from work account → sync to brain
- **Project docs** in shared drive → periodic review and summarization
- **Shared templates** → read and use for generation
- **Client-facing materials** in partner shared drives → monitor for updates
