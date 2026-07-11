# Service Account + Domain-Wide Delegation Setup

Allows the agent to impersonate **any user on the domain** for Gmail, Calendar, Drive, Docs, Sheets — no per-user OAuth needed.

## Prerequisites

- Google Cloud Project (existing: `hermes-agent-gozen`, project ID shown in `google_client_secret.json`)
- Google Workspace super admin (the user who sets this up)

## Admin Setup (one-time)

### Google Cloud Console

1. Go to **[Credentials page](https://console.cloud.google.com/apis/credentials)** with the correct project selected

2. **+ Create Credentials → Service Account**
   - Name: `hermes-agent` (or whatever convention)
   - Skip "Grant access" → Skip "Grant users access" → Done

3. Click the service account → **Keys** tab → **Add Key** → **Create New Key** → **JSON**
   - Downloads a JSON key file — this is the only copy
   - Place it at `~/.hermes/service-account-key.json`

4. **[APIs Library](https://console.cloud.google.com/apis/library)** → Enable:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Sheets API
   - Google Docs API
   - People API
   - (optional) Google Contacts API

### Google Workspace Admin Console

1. Go to **[admin.google.com](https://admin.google.com)** → **Security** → **API Controls** → **Domain-wide Delegation**

   If you can't find it, use this direct URL: 👉 **[https://admin.google.com/ac/owl/domainwidedelegation](https://admin.google.com/ac/owl/domainwidedelegation)**

2. Click **Add new**

3. **Client ID**: copy from the JSON key file (`client_id` field). Note: service account client IDs are **numeric** (e.g., `107398056952657264498`), NOT the `xxx.apps.googleusercontent.com` format used by OAuth web/desktop clients. Use the raw numeric value as-is.

4. **OAuth scopes** (paste as one comma-separated string, no spaces):

```
https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.compose,https://www.googleapis.com/auth/calendar,https://www.googleapis.com/auth/calendar.events,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/contacts
```

5. Click **Authorize**

## Agent-Side Access

`google_api.py` now supports a `--subject` flag for all services (Gmail, Calendar, Drive, Sheets, Docs):

```bash
GAPI="python3 ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py"

# Read inbox as any domain user
$GAPI --subject "user@your-domain.com" gmail search "is:unread" --max 5

# Send email
$GAPI --subject "user@your-domain.com" gmail send \
  --to "client@example.com" --subject "Update" --body "Hi"

# Access Drive
$GAPI --subject "user@your-domain.com" drive search "report" --max 5

# Check Calendar
$GAPI --subject "user@your-domain.com" calendar list --max 5
```

When `--subject` is set, the wrapper:
- Skips `gws` CLI (which uses OAuth user tokens) and goes direct to googleapiclient
- Uses the service account key at `~/.hermes/service-account-key.json`
- Impersonates the specified `@your-domain.com` user with domain-wide delegation

**Important:** The SCOPES list in `google_api.py` must exactly match the scopes authorized in admin.google.com. Mismatches cause `unauthorized_client` errors. Current authorized scopes (2026-06-11): gmail.readonly, gmail.send, gmail.modify, gmail.compose, calendar, calendar.events, drive, drive.readonly, spreadsheets, documents, contacts.

## Verification

After setup, run a quick smoke test:

```bash
python3 ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py \
  --subject "user@your-domain.com" gmail labels
```

Should return the target user's Gmail labels. Also test Drive and Calendar:

```bash
# Drive
python3 ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py \
  --subject "user@your-domain.com" drive search "test" --max 2

# Calendar
python3 ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py \
  --subject "user@your-domain.com" calendar list --max 2
```

## Limitation

❌ **External accounts** (@gmail.com, other domains) — service account can't touch these. They'd need their own OAuth consent flow (Desktop OAuth setup, see `references/manual-oauth-callback.md`).

## Triage: SA-DWD vs Desktop OAuth

When the user asks about setting up Google access:

| If they say... | Recommend |
|---|---|
| "I want access for my whole team / all @company.com users" | SA-DWD (this doc) |
| "Just me, personal Gmail" | Desktop OAuth (First-Time Setup in SKILL.md) |
| "I'm the Workspace admin" | SA-DWD — they can do the whole flow themselves |
| "I need to access a specific external email alongside my work account" | Desktop OAuth for external, SA-DWD for domain |

## Troubleshooting

| Problem | Fix |
|---------|------|
| `HttpError 403: Insufficient Permission` after DWD | Missing scope in admin.google.com — re-check the scopes list |
| `unauthorized_client` on ALL scopes (entire JWT token fails) | **Scope misalignment** — the SCOPES list in `google_api.py` does not match exactly what was authorized in admin.google.com. Even one extra/unlisted scope blocks the entire token request (not just that scope). Fix: align both lists character-for-character. |
| Service account key not found | Check `~/.hermes/service-account-key.json` exists |
| "Service account cannot impersonate" | Domain-wide delegation not authorized — check admin.google.com |
| `HttpError 404: File not found` on visible file | File is in a Shared Drive — need `supportsAllDrives=True` flag |