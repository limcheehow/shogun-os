---
name: scrum-production-hardening
category: workflow
setup_time: 0
cost: $0
depends_on: [department-scrum]
---

# Scrum Production Hardening

Reference guide for the 15 production pitfalls discovered running department-scrum in production. **Read this before deploying scrum for the first time.**

## Full Reference

All 15 pitfalls are documented in `skills/department-scrum/references/production-pitfalls.md`.

## Quick Reference

| # | Pitfall | Impact | Fix |
|---|---------|--------|-----|
| 1 | Gateway healthy but WebSocket dead | DMs silently dropped | Check logs for "Session is closed" |
| 2 | LLM timeout cascade | False gaps DM + crash | Increase timeout to 120s+ |
| 3 | Cron batch-fire race condition | Duplicate DMs sent | Save state BEFORE sending |
| 4 | HERMES_HOME points to profile dir | State file not found | Use `~/.hermes` expanded |
| 5 | JSON extraction from CLI | Parse failures | Scan for first `{` or `[` line |
| 6 | Brain tool selection | Low hit rate | Keyword for IDs, semantic for concepts |
| 7 | Listener crash vs LLM outage | Wrong recovery action | Check process + logs |
| 8 | Save state after channel post | `posted_to_channel: null` | Post first, then save |
| 9 | Recovery sweep date filtering | Stale replies processed | Filter by today's date |
| 10 | Non-standard compliance_state | Non-responder list broken | Use `ok` / `pending_clarification` only |
| 11 | Pass-through post failure | Post missing from channel | Cross-ref via `conversations.history` |
| 12 | CLI syntax verification | Silent injection failure | Verify with `--help` first |
| 13 | Block Kit format | Unformatted posts | Use `blocks=` with `mrkdwn` |
| 14 | Duplicate systemd services | Infinite crash loop | Remove system-level units |
| 15 | Cron silent skip | Job doesn't fire | Compare last_run vs today |

## Cron Jobs

No cron jobs — this is a read-only reference document.

## See Also

- `skills/department-scrum/SKILL.md` — Full scrum workflow v3.0.0
- `skills/department-scrum/references/production-pitfalls.md` — Detailed pitfall docs
- `skills/company-workflow/SKILL.md` — Mandatory workflow gates
