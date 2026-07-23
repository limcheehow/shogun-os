---
name: microsoft-integration
description: "Microsoft 365 Graph API client — mail, calendar, OneDrive, and directory via OAuth 2.0 client credentials."
version: 1.0.0
author: Nous Research
license: MIT
platforms: [linux, macos, windows]
required_environment_variables:
  - MSFT_TENANT_ID
  - MSFT_CLIENT_ID
  - MSFT_CLIENT_SECRET
metadata:
  hermes:
    tags: [Microsoft, Graph, OAuth, Mail, Calendar, Drive, Directory]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [google-workspace]
---

# Microsoft 365 Integration

Microsoft Graph API client for Hermes Agent — mail, calendar, OneDrive, and directory operations via OAuth 2.0 client credentials.

## Scripts

- `scripts/msft_api.py` — GraphClient class + CLI dispatch for all operations

## Tests

- `tests/__init__.py` — package marker
- `tests/test_msft_api.py` — 7 mocked tests covering token refresh, caching, mail search/send, calendar, drive, and connection failure

## Prerequisites

1. **Azure AD App Registration** — create one in the [Azure Portal](https://portal.azure.com/):
   - App registrations → New registration
   - Supported account types: "Accounts in this organizational directory only"
   - No redirect URI needed (client credentials flow)
   - Under "Certificates & secrets", create a client secret
   - Under "API permissions", add Microsoft Graph → Application permissions for the scopes you need (e.g., `Mail.Read`, `Mail.Send`, `Calendars.Read`, `Files.Read.All`, `User.Read.All`, `Directory.Read.All`)
   - Click "Grant admin consent" for the tenant

2. **Set environment variables**:

```bash
export MSFT_TENANT_ID="your-tenant-id"
export MSFT_CLIENT_ID="your-client-id"
export MSFT_CLIENT_SECRET="your-client-secret"
```

## Usage

Set a shorthand:

```bash
MSFT="python ${HOME}/.hermes/skills/devops/microsoft-integration/scripts/msft_api.py"
```

### Mail

```bash
# Search mailbox (returns JSON)
$MSFT --user user@example.com mail search "meeting" --max 5

# Get a specific message
$MSFT --user user@example.com mail get MESSAGE_ID

# Send an email
$MSFT --user user@example.com mail send --to recipient@example.com --subject "Hello" --body "Message text"
```

### Calendar

```bash
# List events (defaults to next 7 days)
$MSFT --user user@example.com calendar list
$MSFT --user user@example.com calendar list --days 30
```

### OneDrive

```bash
# List root children
$MSFT --user user@example.com drive list

# Search files
$MSFT --user user@example.com drive search "budget"
```

### Directory

```bash
# Get user info
$MSFT --user user@example.com directory get-user

# List all users in the directory
$MSFT --user user@example.com directory list-users
```

## Output Format

All commands return JSON. Parse with `jq` or read directly.

## GraphClient API

The `GraphClient` class can also be used directly from Python:

```python
from msft_api import GraphClient

client = GraphClient()
user = "user@example.com"

# Get messages
messages = client.get(client._user_path(user, "/messages?$top=5"))

# Send mail
client.post(client._user_path(user, "/sendMail"), {
    "message": {
        "subject": "Test",
        "body": {"contentType": "Text", "content": "Hello"},
        "toRecipients": [{"emailAddress": {"address": "to@example.com"}}],
    },
})
```

## Auth Model

- **OAuth 2.0** client credentials flow against `login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
- Token cached in-memory with a 60-second safety margin before expiry
- No user interaction required — suitable for automated/background workflows

## Running Tests

```bash
cd ~/.hermes/skills/devops/microsoft-integration
python3 -m pytest tests/ -v
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Missing required env var(s)` | Set `MSFT_TENANT_ID`, `MSFT_CLIENT_ID`, and `MSFT_CLIENT_SECRET` |
| `401 Unauthorized` on token endpoint | Check client secret hasn't expired in Azure Portal |
| `403 Forbidden` on API calls | Grant admin consent for the required API permissions in Azure Portal |
| `Connection test failed` | Verify the user UPN exists in the directory |