# Slack Bot Creation Checklist

Use when scoping and building a new Slack bot agent that connects to a Hermes profile.

## Phase 0: Infrastructure Discovery

Before designing anything, audit what already exists:

```bash
# 1. CHECK EXISTING PROFILES
ls ~/.hermes/profiles/
# Target profile may already have config, tokens, .env

# 2. CHECK EXISTING SCRIPTS
ls ~/.hermes/scripts/
# grep for keywords — the solution may be partly built

# 3. CHECK CRON JOBS
hermes cron list
# Existing automation may already cover some features

# 4. CHECK BRAIN DATA SOURCES
ls ~/brain/
# HR policies, staff profiles, CSV data dumps, calendar events

# 5. CHECK DATA PIPELINES
# Daily BrioHR syncs, calendar collectors, GDrive syncs, etc.

# 6. CHECK EXISTING SLACK CONFIG
grep -A2 "slack:" ~/.hermes/config.yaml
# channel_prompts, allowed_channels, free_response_channels
```

Map each proposed feature to:
- ✅ **Already built** — just needs wiring to Slack
- 🟡 **Partial solution exists** — needs extension/adaptation
- ❌ **New build** — needs full implementation

## Phase 1: Profile & Slack App Setup

### Create Slack App (api.slack.com)

Name the app clearly. Use Socket Mode. Required scopes:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages |
| `app_mentions:read` | Detect @mentions |
| `channels:history` | Read public channel messages |
| `channels:read` | List/get channel info |
| `im:history` | Read DM history |
| `im:write` | Open DMs |
| `users:read` | Look up users |
| `files:read` | Read attachments |
| `files:write` | Upload files |

Subscribe to events: `message.im`, `message.channels`, `app_mention`.
Enable Messages Tab. Install to workspace.

### Wire to Profile

Add to `~/.hermes/profiles/<name>/.env`:
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

Configure `~/.hermes/profiles/<name>/config.yaml`:
```yaml
slack:
  require_mention: true
  free_response_channels: D0B0LU0HP4L
  allowed_channels: C0123ABCDE
  channel_prompts:
    C0BOTCHANNEL: |
      You are [BOT NAME], the [role] for your company.
      PERSONALITY: friendly, professional, concise
      SOURCES: brain paths that contain your data
      ALLOWED SKILLS: [relevant skill names]
      BLOCKED: terminal, execute_code, github-*, cronjob
      ACCESS CONTROL: [who can do what]
```

### Start Gateway

Verify config parses cleanly, then start in a dedicated tmux session.

## Phase 2: Feature Templates

### Feature A — Data Query (e.g., leave lookup)

When the data pipeline already exists:
1. Write/adapt a Python script that queries the data source and outputs Slack-friendly text
2. Wire it as a cron job or have the agent call it on demand
3. Test with a natural language query

### Feature B — Knowledgebase Q&A (e.g., HR handbook)

When documents are already in brain/gbrain:
1. Point the bot's channel prompt to the relevant brain directory
2. Test with sample policy questions
3. Fallback: "I'll ask HR to follow up" for unanswered questions

### Feature C — Scheduled Posts (e.g., team happiness)

For daily events (birthdays, anniversaries, new joiners):
1. Build a detector script that reads staff data
2. Compare against today's date
3. Create a cron job that runs daily and posts to the channel
4. Silent on empty days (no output = no post)

### Feature D — Slash Command (e.g., /shoutout)

For user-initiated actions:
1. Register the slash command in the Slack app's manifest
2. Build a handler that stores to brain and posts to channel
3. Storage: one JSON file per date in `~/brain/data/<bot>/`

## Pitfalls

- **Always check existing scripts first** — `ls ~/.hermes/scripts/` may reveal 80% of the work is done
- **Check cron jobs before creating new ones** — avoid duplicate names
- **Only one gateway holds bot tokens** at a time
- **Channel prompts are fragile YAML** — avoid hand-editing long multi-line strings
- **Test each feature in a DM first** before inviting the bot to public channels
- **Always ask permission** before restarting the gateway
- **Slash commands need Slack app manifest updates**