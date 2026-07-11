---
name: brain-file-delivery
description: "Enforce file-attachment delivery for newly created or modified brain files. After any brain file write, send the file as an attachment to both Telegram (MEDIA:) and Slack (3-step upload API). NO links — actual file attachments only."
version: 1.0.0
author: CH Lim
tags: [brain, gbrain, delivery, slack, telegram, attachments]
triggers:
  - "create brain page"
  - "write brain file"
  - "put_page"
  - "save to brain"
  - "enrich brain"
  - "brain delivery"
  - "send brain file"
  - "attach brain file"
---

# Brain File Delivery — Attachment Enforcement

**MANDATORY:** After ANY brain file creation or modification, deliver the file as an actual attachment to both Telegram and Slack. Never share a link when the file is on local disk.

---

## The Rule

```
BRAIN FILE WRITTEN → ATTACH IT. DO NOT LINK IT.
```

Every time you write a brain file via `mcp_gbrain_put_page`, `write_file` to `~/brain/`, or any other mechanism — you MUST deliver the file as an attachment to both platforms.

---

## 1. Telegram Delivery

Include `MEDIA:/absolute/path/to/file` in your response. The Telegram gateway auto-detects this and sends it as a native file attachment.

```
MEDIA:/home/your-company/brain/people/alice-wong.md
```

This works for: `.md`, `.png`, `.jpg`, `.webp`, `.ogg`, `.mp4`, `.pdf`, `.txt`, `.json`, `.csv`.

**Multiple files?** Include multiple `MEDIA:` lines. Each is delivered as a separate attachment.

---

## 2. Slack Delivery

Use the **3-step upload API** (files.upload is DEPRECATED). The Slack token lives in the profile's `.env` file.

### Step 0: Extract the token

```bash
TOKEN=$(grep '^SLACK_BOT_TOKEN=' ~/.hermes/profiles/default/.env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
```

The default Slack home channel for this profile is `U0XXXXXXX` (Chee How DM). Use the `channel_id` from the session context at the top of each turn.

### Step 1-3: Upload via Python (preferred — single script)

```python
import json, os, urllib.request, urllib.parse, sys

filepath = sys.argv[1]
channel_id = sys.argv[2]
title = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(filepath)

# Get token from profile .env
token = None
for env_path in [
    os.path.expanduser('~/.hermes/profiles/default/.env'),
    os.path.expanduser('~/.hermes/.env'),
]:
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith('SLACK_BOT_TOKEN='):
                    token = line.strip().split('=', 1)[1].strip('"').strip("'")
                    break
    except FileNotFoundError:
        continue
    if token:
        break

if not token:
    print('ERROR: SLACK_BOT_TOKEN not found')
    sys.exit(1)

fsize = os.path.getsize(filepath)
fn = os.path.basename(filepath)

# Step 1: Get upload URL
data = urllib.parse.urlencode({'filename': fn, 'length': fsize}).encode()
r1 = json.loads(urllib.request.urlopen(urllib.request.Request(
    'https://slack.com/api/files.getUploadURLExternal',
    data=data,
    headers={'Authorization': f'Bearer {token}',
             'Content-Type': 'application/x-www-form-urlencoded'}
)).read())

if not r1.get('ok'):
    print(f"ERROR step 1: {r1.get('error')}")
    sys.exit(1)

upload_url = r1['upload_url']
file_id = r1['file_id']

# Step 2: Upload raw bytes
with open(filepath, 'rb') as fh:
    urllib.request.urlopen(urllib.request.Request(upload_url, data=fh.read(), method='POST'))

# Step 3: Complete
data3 = urllib.parse.urlencode({
    'files': json.dumps([{'id': file_id, 'title': title}]),
    'channel_id': channel_id,
}).encode()
r3 = json.loads(urllib.request.urlopen(urllib.request.Request(
    'https://slack.com/api/files.completeUploadExternal',
    data=data3,
    headers={'Authorization': f'Bearer {token}',
             'Content-Type': 'application/x-www-form-urlencoded'}
)).read())

if r3.get('ok'):
    print(f"OK: Uploaded {fn} to Slack ({file_id})")
else:
    print(f"ERROR step 3: {r3.get('error')}")
```

Save this as `~/.hermes/scripts/slack-upload-brain-file.py` and run:

```bash
python3 ~/.hermes/scripts/slack-upload-brain-file.py /home/your-company/brain/people/alice-wong.md U0XXXXXXX
```

---

## 3. Combined Delivery Flow

After every brain file write:

```
1. Write the file (mcp_gbrain_put_page or write_file)
2. Telegram: Include MEDIA:/absolute/path in your response
3. Slack: Run the upload script with the file path and channel_id
4. Confirm both deliveries in your response
```

### Example response after writing a person page:

```
✅ Created people/alice-wong.md

Delivered to:
• Telegram → attached below
• Slack → uploaded to Chee How DM

MEDIA:/home/your-company/brain/people/alice-wong.md
```

---

## 4. What NOT to do

| ❌ Don't | ✅ Do |
|----------|------|
| Share a `file://` path | Use MEDIA: for Telegram, upload for Slack |
| Share a GDrive link (unless file > 20MB) | Attach the actual file |
| Skip Slack delivery | Upload to Slack every time |
| Use `files.upload` API (deprecated) | Use the 3-step upload flow |
| Send raw pipe tables to Slack | Use Block Kit pass-through JSON |
| Send MEDIA: paths to Slack | MEDIA: is Telegram-only |

---

## 5. Edge Cases

| Case | Handling |
|------|----------|
| File > 20MB | Skip Slack upload, note size limit, offer GDrive link |
| Slack token not found | Log warning, deliver Telegram only, tell user |
| Multiple files in one operation | Upload each file separately |
| File is in a non-standard brain path | Still deliver — the rule is brain file → attachment |
| Non-.md files (images, PDFs, etc.) | Same rule applies — attach them |

---

## 6. Pitfalls

- **MEDIA: in Slack = garbage.** The `MEDIA:` prefix is Telegram-only. Slack renders it as a broken file icon with raw text. Must use the 3-step upload API for Slack.
- **Don't skip the Slack upload.** Both platforms, every time. No exceptions unless the file is too large or the token is missing.
- **Use the right channel ID.** The Slack home channel is in the session context at the top of every turn. Don't guess.
- **files.upload is dead.** The deprecated endpoint returns `method_deprecated`. Always use the 3-step flow.