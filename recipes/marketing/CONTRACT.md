---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Marketing Provider Contract

> **Standard tool names and response shapes for marketing integrations.**
> Covers campaigns, email marketing, analytics, and social media.

## Tools

### mkt_list_campaigns

List marketing campaigns.

**Input:** `{ "search": "string", "status": "string", "channel": "string (email | social | all)", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50 }`

**Output:** `{ "campaigns": [{ "id": "string", "name": "string", "status": "string", "channel": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "budget": 0, "sent": 0, "opened": 0, "clicked": 0 }], "total": 0 }`

### mkt_create_campaign

Create a new campaign.

**Input:** `{ "name": "string (required)", "channel": "string (required)", "subject": "string", "content": "string", "audience_list_id": "string", "schedule_date": "YYYY-MM-DD", "budget": 0 }`

**Output:** `{ "id": "string", "name": "string", "status": "draft" }`

### mkt_list_audiences

List audience/contact lists.

**Input:** `{ "search": "string", "limit": 50 }`

**Output:** `{ "audiences": [{ "id": "string", "name": "string", "contact_count": 0, "tags": ["string"] }], "total": 0 }`

### mkt_get_campaign_stats

Get performance statistics for a campaign.

**Input:** `{ "campaign_id": "string (required)", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD" }`

**Output:** `{ "campaign_id": "string", "name": "string", "sent": 0, "delivered": 0, "opened": 0, "clicked": 0, "bounced": 0, "unsubscribed": 0, "conversion_rate": 0, "roi": 0 }`

### mkt_list_social_posts

List scheduled or published social media posts.

**Input:** `{ "platform": "string (linkedin | twitter | facebook | all)", "status": "string (draft | scheduled | published)", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50 }`

**Output:** `{ "posts": [{ "id": "string", "platform": "string", "content": "string", "status": "string", "scheduled_date": "YYYY-MM-DD", "engagement": 0 }], "total": 0 }`

## Error Response Shape

All tools return `{"error": "string", "code": "..."}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `mkt_list_campaigns` | P0 |
| `mkt_create_campaign` | P0 |
| `mkt_list_audiences` | P0 |
| `mkt_get_campaign_stats` | P0 |
| `mkt_list_social_posts` | P1 |