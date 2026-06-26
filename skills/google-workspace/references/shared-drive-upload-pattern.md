# Uploading Files to Shared Drives (supportsAllDrives)

Google Shared Drives require the `supportsAllDrives=true` parameter on EVERY Drive API call — without it, even folders you can see in the web UI will return `404 File not found`.

This affects: folder lookup, file creation, file metadata reads, and file updates.

## Simple Upload (requests-based, no googleapiclient)

```python
import json, os, requests

FOLDER_ID = "YOUR_FOLDER_ID"
FILE_PATH = "/path/to/file.docx"

with open(os.path.expanduser("~/.hermes/google_token.json")) as f:
    tok = json.load(f)

token = tok["token"]
upload_headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json; charset=UTF-8",
}

metadata = {
    "name": "Filename.docx",
    "parents": [FOLDER_ID],
}

# Step 1: Create resumable upload session WITH supportsAllDrives
resp = requests.post(
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true",
    headers=upload_headers,
    json=metadata
)
resp.raise_for_status()
upload_url = resp.headers.get("Location")

# Step 2: Upload content
with open(FILE_PATH, "rb") as f:
    file_content = f.read()

resp2 = requests.put(
    upload_url,
    data=file_content
)
resp2.raise_for_status()
result = resp2.json()
print(f"✅ Uploaded: {result.get('id')}")
print(f"📎 Link: https://drive.google.com/file/d/{result.get('id')}/view")
```

## Key Details

- **The parameter name is `supportsAllDrives=true`**
- Required on: `files.get`, `files.create`, `files.update`, `files.list`
- If you get `404 File not found` on a folder you can see in the browser, this is the #1 cause
- The resumable upload URL (step 2) does NOT need the parameter