---
name: support-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# Customer Support Skill (Generic)

> **Works with any support provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `support` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List open/high priority tickets"
1. Call `spt_list_tickets(status=open, priority=high|critical)`
2. Format as table: Ticket | Subject | Priority | Assignee | Age | SLA Deadline
3. Flag tickets approaching or past SLA deadline

### "Create a new ticket"
1. Gather: subject, description, priority, contact email
2. Call `spt_create_ticket` with structured data
3. Confirm with ticket ID and status

### "Update ticket status"
1. Call `spt_update_ticket(id=..., status=..., comment=...)`
2. Confirm the status change

### "Search knowledge base"
1. Call `spt_list_articles(query=...)` with the issue description
2. Return top matching articles as potential solutions

### "SLA compliance report"
1. Call `spt_get_sla_report(date_from=..., date_to=...)`
2. Report: total tickets, breached, compliance rate, avg response/resolution time

## Cron Job Templates

**Ticket summary** (Monday 9AM):
```bash
hermes cron create "0 9 * * 1" --name "Support Ticket Summary" --prompt "Run spt_list_tickets() for open tickets and spt_get_sla_report() for last week. Report open ticket count, critical/high priority tickets, SLA compliance rate, and avg response time." --skill "support-provider" --deliver origin
```