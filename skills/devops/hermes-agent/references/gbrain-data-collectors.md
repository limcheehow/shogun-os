# Gmail + Calendar → gbrain Data Collectors

The gbrain `email-to-brain` and `calendar-to-brain` integrations require Clawvisor as a proxy,
which needs separate credentials. **Bypass them** by writing direct Python collectors that:

1. Use the existing Google OAuth token (covers `gmail.readonly` + `calendar` scopes)
2. Pull recent data from the Google API
3. Write each item as a markdown file with frontmatter into `~/brain/data/<source>/`
4. Run `gbrain import <dir> --no-embed` to index the markdown
5. Schedule with `*/15` or `*/30` cron (no-agent mode, deliver=local)

## Prerequisites

- **Google OAuth token** with Gmail + Calendar scopes. Lokasi tipikal: `~/.hermes/gmail_token.json`
- Token must have `refresh_token` for long-running cron (access tokens expire in 1 hour)
- Python packages: `google-auth`, `google-api-python-client`

## Architecture

```
┌──────────────┐    ┌────────────────┐    ┌──────────────┐
│ Google APIs  │───▶│ collect-*.py   │───▶│ ~/brain/data/│
│ (Gmail/Cal)  │    │ (markdown gen) │    │ email/*.md   │
└──────────────┘    └────────────────┘    │ calendar/*.md│
                                          └──────┬───────┘
                                                 │ gbrain import
                                                 ▼
                                          ┌──────────────┐
                                          │ gbrain PGLite │
                                          │ (voice agent  │
                                          │  can search)  │
                                          └──────────────┘
```

## PII Handling

Emails and calendar descriptions often contain phone numbers, email addresses, and
other PII. The collectors MUST scrub these before writing to markdown:

```python
import re
text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", text)
text = re.sub(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]", text)
```

## Cron Setup

Create wrapper scripts (not inline shell commands) because `hermes cron --script`
requires a file path:

```bash
# collect-gmail-cron.sh
#!/usr/bin/env bash
set -euo pipefail
python3 /home/tapway/.hermes/scripts/collect-gmail.py 2>&1
gbrain import /home/tapway/brain/data/email --no-embed 2>&1
```

Then register:

```bash
hermes cron create '*/15 * * * *' --name 'Collect Gmail → gbrain' \
  --script collect-gmail-cron.sh --no-agent --deliver local
```

## Verification

After the first run:

```bash
gbrain list -n 5 --type email
gbrain list -n 5 --type calendar-event
```

The voice agent at `/call` can now `search` or `query` for emails and calendar events
through gbrain's MCP interface. No Clawvisor needed.

## Related Files

- `scripts/collect-gmail.py` — Pulls 50 recent emails (7-day window), writes markdown with PII scrubbed
- `scripts/collect-calendar.py` — Pulls 100 events (past 7 + future 14 days), writes markdown
- `scripts/collect-gmail-cron.sh` — Cron wrapper: collect + gbrain import
- `scripts/collect-calendar-cron.sh` — Cron wrapper: collect + gbrain import