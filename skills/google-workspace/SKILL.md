---
name: google-workspace
description: "Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python."
version: 1.1.0
author: Nous Research
license: MIT
metadata:
  hermes:
    tags: [Google, Gmail, Calendar, Drive, Sheets, Docs, Contacts, Email, OAuth]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [himalaya]
---

# Google Workspace

Gmail, Calendar, Drive, Contacts, Sheets, and Docs — through Hermes-managed OAuth and a thin CLI wrapper. When `gws` is installed, the skill uses it as the execution backend for broader Google Workspace coverage; otherwise it falls back to the bundled Python client implementation.

## References

- `references/google-dwd-setup.md` — Google DWD (Domain-Wide Delegation) playbook: service account setup, DWD enablement in Workspace Admin Console, impersonation pattern, multi-user access, and token watchdog cron
- `references/full-scope-auth.md` — Full Google OAuth with workspace + fitness scopes in one flow; scope recovery without re-auth; diagnosing missing scopes; **oauthlib scope-mismatch monkey-patch**
- `references/gmail-search-syntax.md` — Gmail search operators (is:unread, from:, newer_than:, etc.)
- `references/gmail-digest-workflow.md` — End-to-end workflow for "give me a digest of your inbox" requests, including categorization, HTML email handling, and search patterns
- `references/gmail-integration-status.md` — Current Gmail integration status, partial auth scenarios, and brain integration options
- `references/gmail-attachment-download.md` — Downloading PDF/image attachments from Gmail, including password-protected PDF extraction
- `references/contacts-csv-import.md` — Import contacts from a secondary Google account via CSV export, create brain person files
- `references/multi-account-strategy.md` — Using shared calendars + Himalaya to access a secondary Google account without setting up a second OAuth token
- `references/advanced-calendar-operations.md` — Writing to shared calendars, declining events, cross-timezone events, and Out of Office event restrictions
- `references/calendar-to-brain-oauth.md` — Standalone Node.js sync script using direct OAuth (reuses ~/.hermes/google_token.json), handles bulk backfill, pagination, attendee filtering, merge-with-existing files
- `references/shared-drive-access.md` — Accessing shared drives and folders owned by other accounts
- `references/shared-drive-upload-pattern.md`
- `references/irm-restricted-files.md` — IRM/DRM-protected files: detection via `access-disabled-code:'2'` header, endpoint behavior table, IMPORTRANGE workaround, file copy, and export manual workaround steps — Uploading files to shared drives with `supportsAllDrives=true`; resumable upload via direct REST API
- `references/docs-batch-update.md` — Writing Google Docs content via batchUpdate REST API (scope upgrade, full/partial replace, pitfalls)
- `references/docx-table-edit.md` — Editing DOCX table cells via ZIP-in-ZIP XML manipulation; Drive download → edit → re-upload pattern; filled compliance matrix workflow
- `references/docs-brain-sync-pattern.md` — Full-replace content sync from a markdown brain file to a Google Doc via batchUpdate; includes no_agent cron setup, token handling, and verification checks
- `references/google-dwd-auth.md` — Google Domain-Wide Delegation (DWD) auth pattern: service account impersonation as an alternative to individual OAuth. Covers when to use DWD, code patterns, multi-scope management, and troubleshooting. References the canonical `google-dwd` recipe at `~/shogun-os/recipes/google-dwd.md`.
- `references/doc-append-style-guide.md` — **Appending content to Google Docs: content voice/tone matching, heading hierarchy mirroring, and formatting consistency rules. Read before writing new sections into an existing doc.**
- `references/drive-upload-pattern.md` — Uploading local files to a Drive folder via `files().create()` with `MediaFileUpload`; reusable for receipt/document ingestion workflows
- `references/google-token-watchdog.md` — Proactive token refresh watchdog for when auto-refresh isn't working
- `references/sheets-create.md` — Creating new spreadsheets via direct Sheets API (create, batchUpdate)
- `references/sheets-read-pattern.md` — Sheet name discovery, multi-tab navigation, A1 range quoting pitfalls, and read patterns

## Templates

- `templates/exchange-full-scope-token.py` — Standalone OAuth code exchange for workspace + fitness (19 scopes). Handles the oauthlib scope-mismatch monkey-patch. Usage: `python3 exchange-full-scope-token.py 'http://localhost/?code=...'`
- `templates/exchange-full-scope-http.py` — **Preferred.** Direct HTTP exchange (no oauthlib, no monkey-patch). Usage: `python3 exchange-full-scope-http.py --auth-url` then `python3 exchange-full-scope-http.py 'http://...'`. Accepts any scopes Google returns.

## Scripts

- `scripts/setup.py` — OAuth2 setup (run once to authorize)
- `scripts/google_api.py` — compatibility wrapper CLI. It prefers `gws` for operations when available, while preserving Hermes' existing JSON output contract.
- `scripts/meeting-sync.sh` — Daily sync script for Google Docs meeting notes
- `scripts/drive_upload.py` — (located under sibling skill `receipt-to-sheet/scripts/`) Upload a local file to a Drive folder, returns shareable link. Reuses the same OAuth token.

## First-Time Setup

The setup is fully non-interactive — you drive it step by step so it works
on CLI, Telegram, Discord, or any platform.

Define a shorthand first:

```bash
GSETUP="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/setup.py"
```

### Step 0: Check if already set up

```bash
$GSETUP --check
```

If it prints `AUTHENTICATED`, skip to Usage — setup is already done.

### Step 1a: Check for Google DWD (Domain-Wide Delegation)

Before starting individual OAuth setup, ask:

**"Do you have Google DWD (Domain-Wide Delegation) set up for a service account?"**

- **Yes** → Use the DWD path. Skip individual OAuth below.
  Load `references/google-dwd-setup.md` for the full playbook.
  Key difference: instead of `~/.hermes/google_token.json`, DWD uses a
  service account key at `~/.hermes/secrets/google-dwd-sa.json` and
  impersonates any user in the domain via the `subject` field.
  A `no_agent=true` cron running every 30 min keeps cached tokens fresh.

- **No / Not sure** → Fall through to individual OAuth path (Step 1b).

### Step 1b: Triage — ask the user what they need (individual OAuth path)**

Before starting OAuth setup, ask the user TWO questions:

**Question 1: "What Google services do you need? Just email, or also
Calendar/Drive/Sheets/Docs, and/or Fitness?"**

- **Email only** → They don't need this skill at all. Use the `himalaya` skill
  instead — it works with a Gmail App Password (Settings → Security → App
  Passwords) and takes 2 minutes to set up. No Google Cloud project needed.
  Load the himalaya skill and follow its setup instructions.

- **Any combination of workspace services (no fitness)** → Continue with this
  skill. The `setup.py` script bakes all scopes into the auth URL (gmail,
  calendar, drive, contacts, sheets, docs). Enable only the APIs you need in
  Google Cloud Console — the consent screen will show all scopes, but unused
  APIs are harmless. There is no `--services` flag on `setup.py`; you
  cannot narrow scopes via CLI.

- **Fitness data too (health tracker / wearable sync)** → Same setup flow.
  All 22 fitness scopes (activity, body, heart_rate, sleep, location, nutrition,
  blood_glucose, blood_pressure, body_temperature, oxygen_saturation,
  reproductive_health, each with read+write) are baked into setup.py's SCOPES
  list — 34 scopes total (12 workspace + 22 fitness). **But you MUST also
  enable the Fitness API** in Google Cloud Console at
  https://console.cloud.google.com/apis/library/fitness.googleapis.com
  otherwise the consent screen will list the scopes but API calls will fail with
  "Access Not Configured".

**Question 2: "Does your Google account use Advanced Protection (hardware
security keys required to sign in)? If you're not sure, you probably don't
— it's something you would have explicitly enrolled in."**

- **No / Not sure** → Normal setup. Continue below.
- **Yes** → Their Workspace admin must add the OAuth client ID to the org's
  allowed apps list before Step 4 will work. Let them know upfront.

### Step 2: Create OAuth credentials (one-time, ~5 minutes)

Tell the user:

> You need a Google Cloud OAuth client. This is a one-time setup:
>
> 1. Create or select a project:
>    https://console.cloud.google.com/projectselector2/home/dashboard
> 2. Enable the required APIs from the API Library:
>    https://console.cloud.google.com/apis/library
>    Enable: Gmail API, Google Calendar API, Google Drive API,
>    Google Sheets API, Google Docs API, People API,
>    **and Fitness API** (if you need health/fitness scopes)
> 3. Create the OAuth client here:
>    https://console.cloud.google.com/apis/credentials
>    Credentials → Create Credentials → OAuth 2.0 Client ID
> 4. Application type: "Desktop app" → Create
> 5. If the app is still in Testing, add the user's Google account as a test user here:
>    https://console.cloud.google.com/auth/audience
>    Audience → Test users → Add users
> 6. Download the JSON file and tell me the file path
>
> Important Hermes CLI note: if the file path starts with `/`, do NOT send only the bare path as its own message in the CLI, because it can be mistaken for a slash command. Send it in a sentence instead, like:
> `The JSON file path is: /home/user/Downloads/client_secret_....json`

Once they provide the path:

```bash
$GSETUP --client-secret /path/to/client_secret.json
```

If they paste the raw client ID / client secret values instead of a file path,
write a valid Desktop OAuth JSON file for them yourself, save it somewhere
explicit (for example `~/Downloads/hermes-google-client-secret.json`), then run
`--client-secret` against that file.

### Step 3: Get authorization URL\n\nThe `setup.py` script has all scopes baked in — just run:\n\n```bash\n$GSETUP --auth-url\n```\n\n⚠️ **`--services` and `--format` flags are NOT supported** by `setup.py`.\nIt always prints a plain URL string. Pass it directly and tell the user to\nclick it. Do NOT pass `--services all --format json` or similar — that\nwill error with `unrecognized arguments`.

Agent rules for this step:
- Send the exact URL to the user as a single line so they can click it.
  ⚠️ **PITFALL — URL transcription errors**: Do NOT manually retype, abbreviate, or reconstruct the URL. If you must wrap it in a markdown link ([text](url)), copy-paste the ENTIRE URL from the terminal output, including the full `scope=` parameter. A single character typo (e.g. `readout` instead of `readonly`) causes Google to reject the entire auth request with "Some requested scopes were invalid." The safest approach: send the raw URL as plain text (not a markdown link) so there's zero transcription risk.
- Tell the user that the browser will likely fail on `http://localhost:1` after approval, and that this is expected.
- Tell them to copy the ENTIRE redirected URL from the browser address bar.
- If the user gets `Error 403: access_denied`, send them directly to `https://console.cloud.google.com/auth/audience` to add themselves as a test user.

### Step 4: Exchange the code

The user will paste back either a URL like `http://localhost:1/?code=4/0A...&scope=...`
or just the code string. Either works. The `--auth-url` step stores a temporary
pending OAuth session locally so `--auth-code` can complete the PKCE exchange
later, even on headless systems:

```bash
$GSETUP --auth-code "THE_URL_OR_CODE_THE_USER_PASTED"
```

⚠️ **`--format json` is NOT supported** by `setup.py`. Just pass the URL or code
string directly. The script prints a plain success message on completion.

If `--auth-code` fails because the code expired, was already used, or came from
an older browser tab, it now returns a fresh `fresh_auth_url`. In that case,
immediately send the new URL to the user and have them retry with the newest
browser redirect only.

### Step 5: Verify

```bash
$GSETUP --check
```

Should print `AUTHENTICATED`. Setup is complete — token refreshes automatically from now on.

### Notes

- **Two auth paths: DWD vs individual OAuth.** If the user has Google DWD,
  use `references/google-dwd-setup.md` instead of the individual OAuth flow
  (Steps 2-5). DWD uses a service account key at `~/.hermes/secrets/google-dwd-sa.json`
  with user impersonation — no user-facing consent screen, no refresh token expiry.
  A `no_agent=true` token watchdog cron keeps legacy token files refreshed.
- Token is stored at `~/.hermes/google_token.json` (individual OAuth path) and auto-refreshes.
- Pending OAuth session state/verifier are stored temporarily at `~/.hermes/google_oauth_pending.json` until exchange completes.
- If `gws` is installed, `google_api.py` points it at the same `~/.hermes/google_token.json` credentials file. Users do not need to run a separate `gws auth login` flow.
- To revoke: `$GSETUP --revoke`

## Usage

All commands go through the API script. Set `GAPI` as a shorthand:

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
```

### Gmail

```bash
# Search (returns JSON array with id, from, subject, date, snippet)
$GAPI gmail search "is:unread" --max 10
$GAPI gmail search "from:boss@company.com newer_than:1d"
$GAPI gmail search "has:attachment filename:pdf newer_than:7d"

# Read full message (returns JSON with body text)
$GAPI gmail get MESSAGE_ID

# Send
$GAPI gmail send --to user@example.com --subject "Hello" --body "Message text"
$GAPI gmail send --to user@example.com --subject "Report" --body "<h1>Q4</h1><p>Details...</p>" --html
$GAPI gmail send --to user@example.com --subject "Hello" --from '"Research Agent" <user@example.com>' --body "Message text"

# Reply (automatically threads and sets In-Reply-To)
$GAPI gmail reply MESSAGE_ID --body "Thanks, that works for me."
$GAPI gmail reply MESSAGE_ID --from '"Support Bot" <user@example.com>' --body "Thanks"

# Labels
$GAPI gmail labels
$GAPI gmail modify MESSAGE_ID --add-labels LABEL_ID
$GAPI gmail modify MESSAGE_ID --remove-labels UNREAD
```

### Calendar

```bash
# List events from primary calendar (defaults to next 7 days)
$GAPI calendar list
$GAPI calendar list --start 2026-03-01T00:00:00Z --end 2026-03-07T23:59:59Z

# List events from a shared/secondary calendar by email
$GAPI calendar list --calendar "colleague@company.com"
$GAPI calendar list --start 2026-05-04T00:00:00+08:00 --end 2026-05-11T23:59:59+08:00 --calendar "work@company.com"

# Create event (ISO 8601 with timezone required)
$GAPI calendar create --summary "Team Standup" --start 2026-03-01T10:00:00-06:00 --end 2026-03-01T10:30:00-06:00
$GAPI calendar create --summary "Lunch" --start 2026-03-01T12:00:00Z --end 2026-03-01T13:00:00Z --location "Cafe"
$GAPI calendar create --summary "Review" --start 2026-03-01T14:00:00Z --end 2026-03-01T15:00:00Z --attendees "alice@co.com,bob@co.com"

# Delete event
$GAPI calendar delete EVENT_ID
```

> **Secondary calendars**: Use `--calendar CALENDAR_EMAIL` to query calendars shared with the authenticated account. The user's personal OAuth token is used for auth, so the target calendar must be shared with that account. To read events from a work calendar without setting up a second OAuth token, ask the user to share their work calendar with their personal Google account. Events from secondary calendars include the calendar email in the event ID, distinguishing them from primary calendar events.

### Drive

```bash
$GAPI drive search "quarterly report" --max 10
$GAPI drive search "mimeType='application/pdf'" --raw-query --max 5
```

> **Shared Drives:** See `references/shared-drive-api-patterns.md` for accessing files in Google Shared Drives (team drives). Standard API calls return `404 File not found` — you need `supportsAllDrives=True`, `corpora="allDrives"`, and `includeItemsFromAllDrives=True` parameters.

**Shared Drive access** requires 3 extra API parameters: `supportsAllDrives=True`, `includeItemsFromAllDrives=True`, `corpora="allDrives"`. See `references/shared-drive-access.md` for the full pattern, including how to read Docs from shared drives (the Docs API doesn't accept `supportsAllDrives` — use direct REST calls instead).

> ⚠️ **Shared drive limitation:** The `google_api.py` wrapper does NOT pass `supportsAllDrives` or `includeItemsFromAllDrives` parameters. It will return `404 File not found` or empty results for folders/files in shared drives or owned by other accounts. To access shared drive content, use direct Python scripts with the REST API — see `references/shared-drive-access.md` for the correct pattern.

### Contacts

```bash
$GAPI contacts list --max 20
```

### Sheets

```bash
# Read
$GAPI sheets get SHEET_ID "Sheet1!A1:D10"

# Write
$GAPI sheets update SHEET_ID "Sheet1!A1:B2" --values '[["Name","Score"],["Alice","95"]]'

# Append rows
$GAPI sheets append SHEET_ID "Sheet1!A:C" --values '[["new","row","data"]]'
```

> ⚠️ **Pitfall — don't assume the sheet is called "Sheet1".** Many real
> spreadsheets have custom tab names like "Overview", "Transactions",
> or "1_Tiles". Passing the wrong name gives `400 Unable to parse range`.
> **Always discover the sheet names first** — see
> `references/sheets-read-pattern.md` for the Python recipe.
```

> ⚠️ **No `sheets create` in google_api.py.** Only get/update/append exist.
> To create a new spreadsheet, use a direct Python script against the
> Sheets API. See `references/sheets-create.md` for the recipe.

### Docs

```bash
# Read
$GAPI docs get DOC_ID

# Write — see references/docs-batch-update.md
# The wrapper only supports read. For writing (batchUpdate), use the
# direct REST approach in `references/docs-batch-update.md`.
# Requires `https://www.googleapis.com/auth/documents` scope.

Convert markdown → beautiful Google Doc — see references/docs-docx-pipeline.md
Build a styled .docx with python-docx (headings, tables, TOC, cover page),
upload via Drive API with mimeType conversion, then add page breaks via batchUpdate.
This approach preserves far more formatting fidelity than batchUpdate text insert.

**Content style & formatting** — see `references/docs-content-style.md`.
When writing into an existing Google Doc, ALWAYS match the doc's voice, tone,
heading hierarchy, and formatting. Read the doc first, then write in its style.
This is the most common source of user frustration with doc edits.
```

## Output Format

All commands return JSON. Parse with `jq` or read directly. Key fields:

- **Gmail search**: `[{id, threadId, from, to, subject, date, snippet, labels}]`
- **Gmail get**: `{id, threadId, from, to, subject, date, labels, body}`
- **Gmail send/reply**: `{status: "sent", id, threadId}`
- **Calendar list**: `[{id, summary, start, end, location, description, htmlLink}]`
- **Calendar create**: `{status: "created", id, summary, htmlLink}`
- **Drive search**: `[{id, name, mimeType, modifiedTime, webViewLink}]`
- **Contacts list**: `[{name, emails: [...], phones: [...]}]`
- **Sheets get**: `[[cell, cell, ...], ...]`

## Rules

1. **Never send email or create/delete events without confirming with the user first.** Show the draft content and ask for approval.
2. **Check auth before first use** — run `setup.py --check`. If it fails, guide the user through setup.
3. **Use the Gmail search syntax reference** for complex queries — load it with `skill_view("google-workspace", file_path="references/gmail-search-syntax.md")`.
4. **Calendar times must include timezone** — always use ISO 8601 with offset (e.g., `2026-03-01T10:00:00-06:00`) or UTC (`Z`).
5. **Respect rate limits** — avoid rapid-fire sequential API calls. Batch reads when possible.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| User keeps getting asked to re-auth (\"constantly asked to do Google OAuth\") | Token expires hourly but something in the call chain isn't using `Credentials.from_authorized_user_file()` auto-refresh. **Fix:** set up a `no_agent=true` cron job running every 30min to proactively refresh the token before expiry. See `references/google-token-watchdog.md`. |
| `NOT_AUTHENTICATED` | Run setup Steps 2-5 above |
| `REFRESH_FAILED` | Token revoked or expired — redo Steps 3-5 |
| `invalid_grant: Token has been expired or revoked` | **Two possible causes — check before revoking!**<br>**1. Token file format mismatch** (refresh token IS valid, but file format is wrong). The raw HTTP exchange scripts save token with keys `access_token`, `expires_in`, `refresh_token`, `scope` (singular), `token_type` but `Credentials.from_authorized_user_file()` requires: `token` (NOT `access_token`), `refresh_token`, `token_uri`, `client_id`, `client_secret`, `scopes` (array), `expiry` (ISO), `universe_domain`, `account`. **Diagnose:** try refreshing via direct POST to Google's token endpoint — if it returns a fresh access token, the refresh token is alive and it's a format issue. **Fix:** read the token dict, add the missing fields from `client_secret.json`, rename `access_token`→`token`, `scope`→`scopes` (as array), add `expiry: None`, save. See `references/google-token-watchdog.md` for the refresh-and-rewrite pattern and `scripts/google-token-refresh.sh` for a ready-made watchdog that handles this automatically.<br>**2. Token legitimately expired** — refresh token itself is dead. This happens after ~7 days of inactivity or if the Google Cloud OAuth consent screen expires Testing status (90 days in Testing mode). Fix: `$GSETUP --revoke` then re-run Steps 3-5 to get a fresh token. Fall back to brain files (`~/brain/daily/calendar/`) or session_search when calendar API is offline. |
| `HttpError 403: Insufficient Permission` | **First try: scope recovery via token refresh.** If the original OAuth consent granted all scopes (setup.py bakes all scopes into the auth URL) but a narrower-scope operation overwrote `google_token.json`, you can recover without user-facing re-auth: load the token with `Credentials.from_authorized_user_file(token_path, FULL_SCOPE_LIST)` and call `creds.refresh(Request())` — the refresh token still carries the original grant and re-issues an access token with the full scope set. Save the creds back to `google_token.json`. Only if this fails (the refresh token itself lacks the scope) should you fall through to `$GSETUP --revoke` + redo Steps 3-5. |
| `HttpError 403: Access Not Configured` | API not enabled — user needs to enable it in Google Cloud Console |
| `ModuleNotFoundError` | Run `$GSETUP --install-deps` |
| `HttpError 403: domain-wide delegation disabled` | DWD not enabled in Workspace Admin Console → see `references/google-dwd-setup.md` Step 3 |
| `HttpError 403: Not Authorized to Access This Resource` | Service account's Client ID not in DWD allowlist → see `references/google-dwd-setup.md` Step 3 |
| `Warning: Scope has changed from ... to ...` on auth code exchange | Google returned expanded scopes (e.g. added `drive.readonly`). Oauthlib rejects this by default. **Fix:** Use the direct HTTP exchange script (`templates/exchange-full-scope-http.py`) instead of Flow-based exchange — it bypasses all oauthlib scope checking. Alternatively, monkey-patch `oauthlib.oauth2.rfc6749.tokens.parse_token_response` before `flow.fetch_token()` to accept any scope — see `references/full-scope-auth.md`. |
- **Token has only 2 scopes** (`drive.file`, `documents`) or token missing `scopes` key entirely | A Flow-based exchange failed mid-way, consuming the auth code but leaving a corrupted token. **Fix:** Use the direct HTTP exchange script: `templates/exchange-full-scope-http.py` to re-authorize cleanly with all 34 scopes (12 workspace + 22 fitness). Do NOT reuse the same auth code — generate a fresh URL. |
| `TOKEN_CORRUPT: Authorized user info was not in the expected format, missing fields client_id, client_secret.` | Token was saved as raw OAuth response instead of `Credentials.from_authorized_user_info()` format. **Raw format has:** `access_token`, `expires_in`, `refresh_token`, `scope`, `token_type`. **Required format has:** `token` (NOT `access_token`), `refresh_token`, `token_uri`, `client_id`, `client_secret`, `scopes` (array), `expiry` (ISO 8601), `universe_domain`, `account`. **Fix:** Transform via script or manually: read raw fields + client secret file → build dict with correct keys → save. The `templates/exchange-full-scope-http.py` template already outputs the correct format. |
- `HttpError 403: You need to have writer access to this calendar.` | User shared the calendar as read-only. Ask them to upgrade to "Make changes to events" in Google Calendar sharing settings. |
| `TypeError: Got an unexpected keyword argument supportsAllDrives` | This happens on Docs API calls (not Drive API). The Google client library's `documents().get()` doesn't accept `supportsAllDrives`. Use direct REST calls instead — see `references/shared-drive-access.md`. |
| `HttpError 403: The caller does not have permission` on batchUpdate | Token has `documents.readonly` but not `documents` (write). Fix: add `"https://www.googleapis.com/auth/documents"` to setup.py SCOPES, `$GSETUP --revoke`, re-auth. |

## Accessing Google Forms, Docs, and Sheets Behind Sign-In

**The browser tool cannot sign in to Google.** Google blocks automated browser
sign-in on forms, docs, and sheets pages. Attempting to type credentials or
click the "Next" button on the Google Sign-In page will fail.

**When you encounter a Google Form, Doc, or Sheet link the user has shared:**

### 1. Check email first (fastest path)

Many Google resources send email notifications when they're shared or when
forms are submitted. Use the `himalaya` skill to check the inbox:

```bash
# Search for form notifications or shares
himalaya envelope list subject "form" --page-size 10

# Search broader
himalaya envelope list --folder INBOX --page-size 30
```

The `himalaya` skill is preferred over `google-workspace` for email because
it uses IMAP/SMTP app passwords which do not expire, unlike Google OAuth
tokens.

### 2. Try Google Sheets API first (diagnostic value)

**Lead with the Sheets API.** It can diagnose file presence even when the
Drive API can't — use it before giving up.

```bash
$GAPI sheets get SHEET_ID "Sheet1!A1:Z100"
```

**Key diagnostic: Sheets API errors vs Drive API errors**

| Sheets API error | Meaning | Next step |
|---|---|---|
| `400: This operation is not supported for this document. The document must not be an Office file.` | File IS an XLSX (or other Office format) uploaded to Google Drive. The Sheets API routes to it (proves the file exists) but can't read the native Office format. **This does NOT mean the file is unshared with the OAuth account** — it may still be viewable or even shared. | Try the Drive API `files().get_media()` (direct XLSX download), export endpoints, or the IRM/DRM workaround below. If all fail, ask user to share with the OAuth account email. |
| `404: File not found` or `403: The caller does not have permission` | File is not accessible at all via this account. | User must re-share with the OAuth account email. |
| Success (returns data) | File IS a native Google Sheet shared with the authenticated account. | Read and process as normal. |

**⚠️ Drive API false negative:** The Drive API often returns `404 File not
found` for files in another person's account, even when the Sheets/export
endpoints CAN see the file. **Always try the Sheets API before concluding
the file is inaccessible.**

### 3. Exhaust OAuth API approaches before asking user to re-share

**Rule: do not ask the user to re-share the file until you've tried ALL of
these with the OAuth token:**

1. **Sheets API** (Sheets API `get` — gives best diagnostic error)
2. **Drive API** `files().get()` with `?alt=media` (direct download)
3. **Export endpoint** `https://docs.google.com/spreadsheets/d/{ID}/export?format=csv`
   with `Authorization: Bearer {token}` header
4. **Export endpoint** with `?format=xlsx` (for Office files)
5. **Gmail notifications** — search inbox for the file name or sharing notification
   (use the `himalaya` skill to check: `himalaya envelope list subject "shared"`)

Only after all five fail should you report that the file isn't accessible and
ask the user to share it with the OAuth account email or export it manually.

### 4. Form response data lives in Google Sheets (not emailed)

Google Forms store responses in an **associated Google Sheet** — they do NOT
send email notifications by default. If you search the inbox for form submission
notifications and find nothing, this is why. The responses are in the linked
Sheet only.

To access form response data:
- Find the associated response Sheet (form owner can see it in the form editor
  under "Responses" tab → green Sheets icon)
- Use the `$GAPI sheets get SHEET_ID` command to read the response data
- Or ask the form owner to enable email notifications per response (Form →
  Settings → Collect email addresses → Send email receipt)

### 5. IRM/DRM-restricted files (access-disabled-code)

Some Google Workspace files have **Information Rights Management (IRM)** restrictions applied by the owner's organization that block download, export, print, and copy — even though the file is viewable in the browser by the authenticated user.

**How to detect IRM-restricted files:**
- Export endpoints (`/export?format=csv`, `/export?format=xlsx`, `/gviz/tq?tqx=out:csv`) return **`403`** with a **`access-disabled-code: '2'`** response header
- The 403 response page contains a `ppConfig` JavaScript object with `productName`, `sealIsEnforced`, and `heartbeatRate` properties — Google's DRM infrastructure
- The Sheets API returns `400: This operation is not supported for this document` (because it's an XLSX)
- The Drive API returns `404 File not found` (false negative for files owned by other accounts)
- A COMPASS cookie is set in the 403 response for the file's path
- **The file IS accessible** — the OAuth Bearer token reaches Google's backend successfully, but the policy blocks raw data export

**IMPORTRANGE workaround (recommended):**

IRM restrictions typically block API-based export but still allow server-to-server data sharing within Google's infrastructure. You can bypass this by creating a new native Google Sheet and using `=IMPORTRANGE()`.

See `references/irm-restricted-files.md` for the full step-by-step Python implementation, endpoint behavior reference table, and alternative workarounds.

**⚠️ First-time authorization required:** The IMPORTRANGE will return `#REF!` until the user opens the new sheet and clicks "Allow access" on the yellow banner. Send the user the URL (`https://docs.google.com/spreadsheets/d/{new_id}/edit`) and ask them to authorize. Once done, you can read the data via the Sheets API.

### 6. Admit limitation

If the resource is behind Google Sign-In and you've exhausted the above
options, tell the user explicitly:
- You cannot automate access to this specific Google resource
- Suggest they export the data to a shareable format (CSV, PDF, public link)
- Or ask them to set up email notifications on the form

## Scope Testing Guide

See `references/scope-testing-guide.md` for detailed instructions on how to test missing scopes and verify functionality.

## Partial Authentication Status

**⚠️ Common Partial Auth Scenarios:**

**Read-only Access:**
- **Status**: AUTHENTICATED (partial) with basic read access
- **Available**: Gmail search, email reading, calendar listing
- **Missing**: `gmail.modify`, `gmail.send`, `documents` (write), `contacts` (write)
- **Use Case**: Manual email processing, inbox monitoring, calendar viewing
- **Fix**: Re-run OAuth setup with full scopes

**Detection & Testing:**
- Run `setup.py --check` to see exact missing scopes
- Test functionality: `gmail search` works, `gmail send` fails with "Insufficient Permission" error
- Current scopes visible in `~/.hermes/google_token.json` under "scopes" array

**Brain Integration Ready:**
- **Status**: Gmail search works, can process emails manually
- **Available**: Email content retrieval, entity detection, timeline updates
- **Use Case**: Manual email-to-brain workflow, contact enrichment
- **Integration**: Connect with gbrain email-to-brain automation

**Multi-Account Access:**
- **Status**: Primary account authenticated, secondary accounts need separate setup
- **Available**: Primary Gmail account operations
- **Missing**: Secondary account access without additional OAuth tokens
- **Fix**: Use `--calendar` flag for shared calendars, separate setup for additional accounts

## Revoking Access

```bash
$GSETUP --revoke
```
