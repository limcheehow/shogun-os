---
id: slides-deck-gen
name: Google Slides Deck Generator
version: 1.0.0
description: Generate, update, and present Google Slides presentations via Google DWD. Deck creation from templates, bulk text replacement, and chart insertion.
category: connector
requires:
  - google-dwd
secrets: []
health_checks:
  - type: script
    command: "python3 -c \"from google.oauth2 import service_account; import google.auth.transport.requests; c=service_account.Credentials.from_service_account_file(os.path.expanduser('~/.hermes/secrets/google-dwd-sa.json'), scopes=['https://www.googleapis.com/auth/presentations'], subject='your-user@your-domain.com'); c.refresh(google.auth.transport.requests.Request()); print('TOKEN_OK')\""
    label: "Slides API token"
setup_time: 15 min
cost_estimate: "$0"
---

# Google Slides Deck Generator

Create, update, and present Google Slides decks via API. Used by the marketing-manager profile (Haiku persona) for client decks, investor presentations, and internal slideware.

## IMPORTANT: Instructions for the Agent

**You are the installer.** This recipe gives the agent a Hermes skill for Slides API operations via DWD impersonation.

## Architecture

```
Google DWD (impersonate your-user@your-domain.com)
  ↓ Slides API + Drive API
Hermes Skill (Slides API wrapper)
  ↓ Agent workflows:
  ├── "Create a deck from template"
  ├── "Replace placeholder text across slides"
  ├── "Add a new slide with content"
  └── "Export deck as PDF"
```

## Prerequisites

1. `google-dwd` recipe completed (service account key at `~/.hermes/secrets/google-dwd-sa.json`)
2. Google Slides API enabled in the Google Cloud project
3. `presentations` scope included in the DWD delegation

## Setup Flow

### Step 1: Verify Slides API Access

```bash
python3 << 'EOF'
import os
from google.oauth2 import service_account
import google.auth.transport.requests
from googleapiclient.discovery import build

SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
creds = service_account.Credentials.from_service_account_file(
    SA_PATH,
    scopes=["https://www.googleapis.com/auth/presentations"],
    subject="your-user@your-domain.com"
)
creds.refresh(google.auth.transport.requests.Request())
service = build("slides", "v1", credentials=creds)
print(f"✅ Slides API accessible. Token: {creds.token[:20]}...")
EOF
```

**STOP until "Slides API accessible" is printed.**

### Step 2: Create the Hermes Skill

The skill should support these operations via the Slides REST API:

| Operation | API Method | Use case |
|-----------|-----------|----------|
| Create presentation | `presentations().create()` | New deck from scratch |
| Get presentation | `presentations().get()` | Read existing deck |
| Batch update | `presentations().batchUpdate()` | Replace text, add slides, insert images |
| Get thumbnail | `presentations().pages().getThumbnail()` | Preview a slide |
| Export as PDF | Drive API `files().export()` with `application/pdf` | Deliver to client |
| Copy template | Drive API `files().copy()` | Clone a template deck |

### Step 3: Store Template Deck IDs

Identify template decks in Google Drive:

```bash
# Template for standard Your Company decks
TEMPLATE_DECK_ID="your-template-deck-id"
# Store for the skill to reference
echo "export TAPWAY_DECK_TEMPLATE_ID=\"$TEMPLATE_DECK_ID\"" >> ~/.hermes/.env
```

### Step 4: Create Cron Template (Optional)

For the **marketing-manager** profile — automated slide generation is ad-hoc (triggered by request), not scheduled. No cron needed unless you want weekly report decks.

### Step 5: Verify With a Test Deck

```bash
python3 << 'EOF'
import os
from google.oauth2 import service_account
import google.auth.transport.requests
from googleapiclient.discovery import build

SA_PATH = os.path.expanduser("~/.hermes/secrets/google-dwd-sa.json")
creds = service_account.Credentials.from_service_account_file(
    SA_PATH,
    scopes=["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive"],
    subject="your-user@your-domain.com"
)
creds.refresh(google.auth.transport.requests.Request())
slides = build("slides", "v1", credentials=creds)
drive = build("drive", "v3", credentials=creds)

# Create a test deck
deck = slides.presentations().create(body={"title": "Test Deck - Hermes Recipe"}).execute()
deck_id = deck["presentationId"]
print(f"✅ Test deck created: {deck_id}")

# Add a slide with text
reqs = [{
    "createSlide": {
        "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
        "placeholderIdMappings": [
            {"layoutPlaceholder": {"type": "TITLE"}, "objectId": "test_title"},
            {"layoutPlaceholder": {"type": "BODY"}, "objectId": "test_body"}
        ]
    }
}]
slides.presentations().batchUpdate(presentationId=deck_id, body={"requests": reqs}).execute()
print("✅ Slide added with title + body placeholders")

# Replace text
reqs = [{
    "replaceAllText": {
        "containsText": {"text": "{{TITLE}}", "matchCase": True},
        "replaceText": "Hello from Hermes Agent"
    }
}]
slides.presentations().batchUpdate(presentationId=deck_id, body={"requests": reqs}).execute()
print("✅ Placeholder text replaced")

# Clean up test deck
drive.files().delete(fileId=deck_id).execute()
print("✅ Test deck cleaned up")
print("\n✅ Slides API fully operational via DWD!")
EOF
```

### Step 6: Log Setup Completion

```bash
mkdir -p ~/.gbrain/integrations/slides-deck-gen
echo '{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","event":"setup_complete","version":"1.0.0","status":"ok"}' >> ~/.gbrain/integrations/slides-deck-gen/heartbeat.jsonl
```

## Cost

$0 — Slides API is free within quotas.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `403: Slides API not enabled` | Enable in Google Cloud Console → API Library → Google Slides API |
| `invalid_scope` | Add `https://www.googleapis.com/auth/presentations` (and `drive` for export) to DWD scopes in Admin Console |
| Template copy fails | Share the template deck with the DWD subject email, or use `supportsAllDrives=True` |
| batchUpdate silently fails | Check that placeholder IDs (like `{{TITLE}}`) actually exist in the deck. Different templates use different placeholders. |
| Export fails | Need `drive.file` scope plus export permission. Some templates have IRM restrictions. |