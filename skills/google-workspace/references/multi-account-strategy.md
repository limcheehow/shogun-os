# Multi-Account Google Strategy

When the user has a **personal Google account** (with OAuth set up for cron jobs) and a **work Google account** (email + calendar needed), use this two-pronged approach instead of setting up a second OAuth token:

## Approach: Shared Calendar + Himalaya Email

| Need | Solution | Why |
|------|----------|-----|
| Work Calendar | Share work calendar → personal Google account. Query via `--calendar "work@company.com"` flag | Uses existing OAuth token. No second auth flow needed. |
| Work Email | Himalaya CLI with Gmail App Password | Simple setup, no OAuth. Works alongside existing Google auth. |

This avoids breaking the existing cron jobs (Morning Briefing, etc.) which depend on the personal Google OAuth token.

## Setup Steps

### 1. Share Work Calendar
Ask the user to:
1. Open Google Calendar on their work account
2. Settings → Settings for my calendars → [calendar name] → Share with specific people
3. Add their personal Gmail email address with "See all event details" permissions

### 2. Verify Calendar Access
```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
$GAPI calendar list --calendar "work@company.com" --start 2026-05-04T00:00:00+08:00 --end 2026-05-11T23:59:59+08:00
```

### 3. Set Up Work Email via Himalaya
Ask the user to generate a Gmail App Password:
1. Work Google Account → Security → 2-Step Verification (must be ON)
2. Security → App Passwords → Select "Mail" + device → Generate
3. They get a 16-char password (e.g., `xxxx xxxx xxxx xxxx`)

Then create `~/.config/himalaya/config.toml`:

```toml
[accounts.work]
email = "user@work.com"
display-name = "Your Name"
default = true

backend.type = "imap"
backend.host = "imap.gmail.com"
backend.port = 993
backend.encryption.type = "tls"
backend.login = "user@work.com"
backend.auth.type = "password"
backend.auth.cmd = "echo THE_APP_PASSWORD"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.gmail.com"
message.send.backend.port = 587
message.send.backend.encryption.type = "start-tls"
message.send.backend.login = "user@work.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "echo THE_APP_PASSWORD"
```

> **Security note**: The `echo` cmd is for quick setup. For production, use `pass` or system keyring. The password goes in the user's config file on their own machine.

Test with:
```bash
himalaya --account work envelope list --max 5
```

## Querying Both Calendars Together

To build a combined view (e.g., for a Morning Briefing), run two queries and merge:

```bash
# Personal calendar
$GAPI calendar list --start ... --end ...

# Work calendar (shared)
$GAPI calendar list --start ... --end ... --calendar "work@company.com"
```

Merge the JSON arrays in your response, labeling events by source where helpful.
