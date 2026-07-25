---
name: crm-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# CRM Skill (Generic)

> **Works with any CRM provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `crm` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List deals in pipeline"
1. Call `crm_list_deals` with optional stage/pipeline filter
2. Format as table: Deal | Contact | Value | Stage | Probability | Close Date
3. Calculate total pipeline value and weighted value

### "Create a new deal"
1. Find or create contact via `crm_list_contacts` / `crm_create_contact`
2. Call `crm_create_deal` with contact ID, name, value, stage
3. Confirm with deal ID and stage

### "Move deal to next stage"
1. Call `crm_update_deal_stage(id=..., stage=...)`
2. Confirm the new stage

### "Log a call/meeting"
1. Call `crm_create_activity(type=call|meeting, subject=..., contact_id=..., notes=...)`
2. Confirm the activity was logged

### "Find a contact"
1. Search via `crm_list_contacts(search=name)`
2. Return contact details or create if not found

## Cron Job Templates

**Sales pipeline** (Monday 9AM):
```bash
hermes cron create "0 9 * * 1" --name "Sales Pipeline" --prompt "Run crm_list_deals() and report total pipeline value, deals by stage, and top 3 largest deals. Flag deals with no activity in 7+ days." --skill "crm-provider" --deliver origin
```

**Weekly summary** (Friday 5PM):
```bash
hermes cron create "0 17 * * 5" --name "Weekly CRM Summary" --prompt "Summarize this week's CRM activity: new deals created, deals won/lost, activities logged. Use crm_list_deals and crm_list_activities with date_from set to Monday." --skill "crm-provider" --deliver origin
```