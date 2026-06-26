#!/bin/bash
# Meeting Minutes Sync Script
# Reads Google Docs from a shared "Meeting Minutes" Drive folder
# and creates gbrain meeting pages at ~/brain/meetings/
#
# Usage: bash ~/.hermes/scripts/meeting-sync.sh
# Set up as daily cron: hermes cron create --name "Meeting Minutes Sync" \
#   --schedule "0 8 * * *" --script meeting-sync.sh \
#   --prompt "Run the meeting sync and propagate entities" \
#   --deliver slack:C0123456789

cd ~/brain

FOLDER_ID="1lJ_WRHjUj6vxQUmApGHqrmS3mZ9EIwfK"
STATE_FILE="$HOME/.hermes/meeting-sync-state.json"

if [ ! -f "$STATE_FILE" ]; then
  echo '{}' > "$STATE_FILE"
fi

python3 << 'PYEOF'
import json, os, re, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import urllib.request

HOME = os.path.expanduser("~")
STATE_FILE = os.path.join(HOME, ".hermes", "meeting-sync-state.json")
BRAIN_DIR = os.path.join(HOME, "brain", "meetings")
FOLDER_ID = "1lJ_WRHjUj6vxQUmApGHqrmS3mZ9EIwfK"
GBRAIN_DIR = os.path.join(HOME, "gbrain")

os.makedirs(BRAIN_DIR, exist_ok=True)

with open(STATE_FILE) as f:
    state = json.load(f)

token_path = os.path.join(HOME, ".hermes", "google_token.json")
with open(token_path) as f:
    token_data = json.load(f)

creds = Credentials.from_authorized_user_info(token_data)
access_token = creds.token
drive = build("drive", "v3", credentials=creds)

print("📋 Checking Meeting Minutes folder...")
query = f"'{FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
results = drive.files().list(
    q=query, pageSize=100,
    corpora="allDrives", includeItemsFromAllDrives=True, supportsAllDrives=True,
    fields="files(id, name, createdTime, modifiedTime)"
).execute()
files = results.get("files", [])
print(f"   Found {len(files)} documents")

new_or_updated = 0
for f in files:
    doc_id = f["id"]
    name = f["name"]
    modified = f["modifiedTime"]
    prev_state = state.get(doc_id, {})

    if prev_state.get("modified") == modified and os.path.exists(prev_state.get("local_path", "")):
        continue

    print(f"\n📄 {name}")

    url = f"https://docs.googleapis.com/v1/documents/{doc_id}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {access_token}", "Accept": "application/json"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            doc_data = json.loads(resp.read())
    except Exception as e:
        print(f"   ❌ Error: {e}")
        continue

    content = doc_data.get("body", {}).get("content", [])
    text_parts = []
    for elem in content:
        if "paragraph" in elem:
            for run in elem["paragraph"].get("elements", []):
                if "textRun" in run:
                    text_parts.append(run["textRun"].get("content", ""))
    full_text = "".join(text_parts).strip()
    if not full_text:
        print(f"   ⏭️  Empty")
        continue

    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    slug = re.sub(r'-+', '-', slug)[:60]
    mod_date = modified[:10]
    page_path = os.path.join(BRAIN_DIR, f"{mod_date}-{slug}.md")

    safe_title = name.replace('"', '\\"')
    text_body = full_text[:15000]
    page_content = f"""---
type: meeting
title: "{safe_title}"
date: {mod_date}
source: google-drive
source_id: {doc_id}
---

# {name}

```
{text_body}
"""
    if len(full_text) > 15000:
        page_content += "\n[...truncated]"

    existing = ""
    if os.path.exists(page_path):
        with open(page_path) as pf:
            existing = pf.read()

    if existing != page_content:
        with open(page_path, "w") as pf:
            pf.write(page_content)
        print(f"   ✅ Saved")
        new_or_updated += 1
    else:
        print(f"   ⏭️  Unchanged")

    state[doc_id] = {"modified": modified, "local_path": page_path}

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=2)

print(f"\n{'='*50}")
print(f"📊 Summary: {new_or_updated} new/updated out of {len(files)} docs")

if new_or_updated > 0:
    import subprocess
    def gb(args):
        r = subprocess.run(["bun", "run", "src/cli.ts"] + args, cwd=GBRAIN_DIR,
                          capture_output=True, text=True, timeout=300)
        if r.stdout: print(r.stdout[-400:])
        if r.stderr: print(r.stderr[-400:])
        return r

    print(f"\n🔄 Importing to gbrain...")
    gb(["import", BRAIN_DIR, "--no-embed"])
    print(f"\n🔄 Embedding...")
    gb(["embed", "--stale"])

print(f"\n✅ Meeting sync complete!")
PYEOF
