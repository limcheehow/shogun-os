---
name: marketing-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# Marketing Skill (Generic)

> **Works with any marketing provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `marketing` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List active campaigns"
1. Call `mkt_list_campaigns(status=active)` or all campaigns
2. Format as table: Campaign | Channel | Status | Sent | Opens | Clicks

### "Create a campaign"
1. Gather: name, channel, subject, content, audience list
2. Call `mkt_create_campaign` with structured data
3. Confirm with campaign ID and status

### "Campaign performance"
1. Call `mkt_get_campaign_stats(campaign_id=...)`
2. Report: sent, delivered, opened, clicked, conversion rate, ROI
3. Compare against benchmarks

### "List audiences"
1. Call `mkt_list_audiences()` to see available contact lists
2. Show audience name and contact count

### "Check social media schedule"
1. Call `mkt_list_social_posts(status=scheduled)` for upcoming posts
2. List by platform and date

## Cron Job Templates

**Campaign performance** (Monday 8AM):
```bash
hermes cron create "0 8 * * 1" --name "Campaign Performance" --prompt "Check performance of recently active campaigns using mkt_list_campaigns and mkt_get_campaign_stats. Report open rates, click rates, and ROI." --skill "marketing-provider" --deliver origin
```