---
name: product-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# Product Management Skill (Generic)

> **Works with any product management provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `product` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List feature requests / ideas"
1. Call `pd_list_ideas(status=new|under_review)` sorted by vote count
2. Format as table: Idea | Status | Votes | Source | Submitted

### "Submit a new idea"
1. Gather: title, description, source, tags
2. Call `pd_create_idea` with structured data
3. Confirm with idea ID

### "View the roadmap"
1. Call `pd_get_roadmap(horizon=current|next)`
2. Report items by horizon with status and progress
3. Flag items behind schedule

### "List recent releases"
1. Call `pd_list_releases(status=shipped)`
2. Format as table: Version | Name | Date | Features
3. Highlight key features shipped

### "Customer feedback review"
1. Call `pd_list_feedback()` for recent feedback
2. Group by sentiment and source
3. Link feedback to existing ideas where possible

## Cron Job Templates

**Roadmap review** (Monday 10AM):
```bash
hermes cron create "0 10 * * 1" --name "Roadmap Review" --prompt "Check the product roadmap using pd_get_roadmap(horizon=current). Report items in progress, on track, and at risk. Highlight newly shipped features." --skill "product-provider" --deliver origin
```