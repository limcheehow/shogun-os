---
id: drive-to-brain
name: Drive-to-Brain
version: 1.0.0
description: Google Drive documents (meeting notes, proposals, reports) sync into brain knowledge pages with entity extraction via Google DWD.
category: ingest
requires:
  - google-dwd
secrets: []
health_checks:
  - type: script
    command: "test -f ~/.hermes/drive-sync-state.json && echo 'STATE_OK' || echo 'STATE_MISSING'"
    label: "Drive sync state"
setup_time: 20 min
cost_estimate: "$0"
---

# Drive-to-Brain: Google Docs → Knowledge Base Sync

Google Drive documents become brain pages. Meeting notes, proposals, reports — all ingested into gbrain with entity extraction, deduplication, and full-text search.

## IMPORTANT: Instructions for the Agent

**You are the installer.** Follow these steps precisely.

**The core pattern: code for data, LLMs for judgment.**
The sync script handles all deterministic work (listing files, reading content, writing pages, tracking state). The agent (you) handles judgment work (entity extraction, person/company page updates).

## Architecture

```
Google DWD (impersonate your-user@your-domain.com)
  ↓ Drive API + Docs API
Sync Script (deterministic Python)
  ↓ Creates:
  brain/{doc-type}/{date}-{slug}.md
    - Frontmatter: type, source_id, date, title
    - Full document text (or truncated)
  ↓ Updates:
  state.json (tracks doc_id → modified_time for dedup)
  ↓
Agent reads new pages → extracts entities
  ↓ Updates people/ + companies/ pages
  ↓
gbrain import + embed + sync
```

## Opinionated Defaults

**Document types and destinations:**

| Document type | Brain directory | Frontmatter type |
|---------------|----------------|-----------------|
| Meeting notes | `~/brain/meetings/` | `type: meeting` |
| Proposals | `~/brain/proposals/` | `type: proposal` |
| Reports | `~/brain/reports/` | `type: report` |
| Technical docs | `~/brain/docs/` | `type: doc` |

**State tracking:** JSON file at `~/.hermes/drive-sync-state.json` — stores `{doc_id: {modified, local_path}}`.

## Prerequisites

1. `google-dwd` recipe completed
2. Google Drive API + Google Docs API enabled in the Google Cloud project
3. The sync folder(s) are shared with `your-user@your-domain.com` (accessible to the DWD subject)

## Setup Flow

### Step 1: Create the Sync Script

Write to `~/.hermes/scripts/drive-sync.py`:

```python
#!/usr/bin/env python3
"""Drive Sync — DWD variant. Deterministic Drive folders → brain pages."""
import os, json, sys, re, urllib.request
from datetime import datetime, timezone
from google.oauth2 import service_account
import google.auth.transport.requests
from googleapiclient.discovery import build

# ── Config ──────────────────────────────────
SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
SUBJECT = "your-user@your-domain.com"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]
# Add folders to monitor: { "name": "folder-id", "target": "brain-subdir" }
FOLDERS = {
    # "meeting-notes": {"id": "FOLDER_ID", "target": "meetings"},
    # "proposals": {"id": "FOLDER_ID", "target": "proposals"},
}
STATE_FILE = os.path.expanduser("~/.hermes/drive-sync-state.json")
BRAIN_DIR = os.path.expanduser("~/brain")
MAX_DOC_LENGTH = 15000  # truncate long docs

# ── Auth ────────────────────────────────────
creds = service_account.Credentials.from_service_account_file(
    SA_PATH, scopes=SCOPES, subject=SUBJECT
)
creds.refresh(google.auth.transport.requests.Request())
drive = build("drive", "v3", credentials=creds)

# ── State ────────────────────────────────────
state = {}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        state = json.load(f)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
updated = 0

for folder_name, config in FOLDERS.items():
    target_dir = f"{BRAIN_DIR}/{config['target']}"
    os.makedirs(target_dir, exist_ok=True)

    # List Google Docs in the folder
    results = drive.files().list(
        q=f"'{config['id']}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false",
        corpora="allDrives",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name, modifiedTime, webViewLink)"
    ).execute()

    for file in results.get("files", []):
        doc_id = file["id"]
        modified = file["modifiedTime"]
        local_path = f"{target_dir}/{today}-{slugify(file['name'])}.md"

        # Check if unchanged
        if doc_id in state:
            if state[doc_id]["modified"] == modified and os.path.exists(state[doc_id].get("local_path", "")):
                continue

        # Read document content via REST API (bypasses client library shared-drive limitation)
        access_token = creds.token
        url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        })

        try:
            with urllib.request.urlopen(req) as resp:
                doc_data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"  ⚠️  Error reading '{file['name']}': {e}")
            continue

        # Extract text content
        text = extract_text(doc_data)[:MAX_DOC_LENGTH]
        if not text.strip():
            continue

        # Write brain page
        frontmatter = f"""---
type: {config['target'].rstrip('s')}
source_id: "{doc_id}"
date: {today}
title: "{file['name']}"
drive_link: "{file.get('webViewLink', '')}
---\n"""
        content = frontmatter + "\n" + text

        with open(local_path, "w") as f:
            f.write(content)

        state[doc_id] = {"modified": modified, "local_path": local_path}
        updated += 1
        print(f"  ✅ '{file['name']}' → {local_path}")

# ── Save state ────────────────────────────────
with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

print(f"Synced {updated} new/updated documents")

def slugify(name):
    s = name.lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    return s[:60]

def extract_text(doc_data):
    """Extract plain text from Google Docs API response."""
    text_parts = []
    for item in doc_data.get("body", {}).get("content", []):
        if "paragraph" in item:
            for elem in item["paragraph"].get("elements", []):
                if "textRun" in elem:
                    text_parts.append(elem["textRun"].get("content", ""))
        elif "table" in item:
            for row in item["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    for content in cell.get("content", []):
                        if "paragraph" in content:
                            for elem in content["paragraph"].get("elements", []):
                                if "textRun" in elem:
                                    text_parts.append(elem["textRun"].get("content", ""))
    return "".join(text_parts)
```

Make it executable:
```bash
chmod +x ~/.hermes/scripts/drive-sync.py
```

**Before running**, edit the `FOLDERS` dict at the top with actual Google Drive folder IDs.

### Step 2: Configure Folders

For each Google Drive folder to monitor:
1. Open the folder in Drive
2. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/{FOLDER_ID}`
3. Add to the `FOLDERS` dict in the script

### Step 3: Run First Sync

```bash
~/.hermes/scripts/drive-sync.py
```

Verify:
```bash
ls ~/brain/meetings/
cat ~/brain/meetings/$(ls ~/brain/meetings/ | tail -1)
```

### Step 4: Import to gbrain

```bash
gbrain import ~/brain/meetings/ ~/brain/proposals/ ~/brain/reports/ --no-embed
gbrain embed --stale
```

### Step 5: Create the Cron Jobs

In the **default** profile:

**Drive sync** (weekdays at 12PM, 4PM, 8PM):
```bash
hermes cron create \
  --name "Drive Sync" \
  --schedule "0 12,16,20 * * 1-5" \
  --script drive-sync.py \
  --no-agent \
  --deliver local
```

**Drive enrichment** (weekdays at 1PM, 5PM):
```bash
hermes cron create \
  --name "Drive Enrichment" \
  --schedule "0 13,17 * * 1-5" \
  --prompt "$(cat <<'PROMPT'
## Drive Enrichment — Extract Entities from New Documents

Read ~/.hermes/drive-sync-state.json to see what was synced recently.
For each NEW document (check by modified time in state):

1. Read the brain page
2. Extract people names, company names, job titles
3. Check ~/brain/people/ for existing files — create new ones if needed
4. Append timeline entries to person/company pages
5. Run gbrain sync: gbrain import ~/brain/people/ ~/brain/companies/ --no-embed
6. Deliver a summary: "Synced N documents. Extracted M entities."
PROMPT
)" \
  --skills "gbrain-operations" \
  --enabled-toolsets "terminal,file,search" \
  --deliver origin
```

### Step 6: Log Setup Completion

```bash
mkdir -p ~/.gbrain/integrations/drive-to-brain-dwd
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","event":"setup_complete","version":"1.0.0","status":"ok"}' >> ~/.gbrain/integrations/drive-to-brain-dwd/heartbeat.jsonl
```

## Cost

$0 — Drive and Docs APIs are free within quotas.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Drive API returns 404 | Missing `supportsAllDrives=True`. All 3 shared drive params required. |
| Docs API fails on shared drive | Use `urllib.request` REST call instead of client library (pattern in script). |
| Token expired mid-sync | The script refreshes once at start. For long syncs, add token refresh between docs. |
| No new files detected | Check state.json — the `modified` field is compared exactly. Google updates it on every edit. |
| Large documents truncated | `MAX_DOC_LENGTH` caps at 15K chars. Full doc stays in Drive. |