---
name: {{SKILL_NAME}}
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# {{DOMAIN_TITLE}} Skill (Generic)

> **Works with any {{DOMAIN}} provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- MCP server named `{{MCP_SERVER_NAME}}` in the owning profile's `config.yaml`
- Provider env vars in the **profile** `.env` (not only main `~/.hermes/.env`)
- Owning profile: `{{PROFILE}}`

## Workflows

### List

1. Call `{{PREFIX}}_list_{{ENTITIES}}` with filters
2. Format as table

### Create

1. Gather required fields
2. Call `{{PREFIX}}_create_{{ENTITY}}`
3. Confirm returned id

## Cron Job Templates

```bash
hermes -p {{PROFILE}} cron create "0 9 * * 1-5" \
  --name "{{DOMAIN_TITLE}} Daily Check" \
  --prompt "Run daily {{DOMAIN}} check using contract tools. Summarize exceptions." \
  --skill "{{SKILL_NAME}}" \
  --deliver origin
```

## Adding a New Provider

1. Add `plugins/<vendor>.py` implementing CONTRACT tools
2. Add `providers/<vendor>.md` setup doc
3. Set `{{PROVIDER_ENV}}=<vendor>` and vendor credentials on the profile
4. Ensure profile MCP `env:` lists every variable the plugin reads
