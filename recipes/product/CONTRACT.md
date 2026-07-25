---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Product Management Provider Contract

> **Standard tool names and response shapes for product management integrations.**
> Covers ideas, feedback, roadmaps, release notes, and feature requests.

## Tools

### pd_list_ideas

List product ideas / feature requests.

**Input:** `{ "search": "string", "status": "string (new | under_review | planned | in_progress | shipped | declined)", "source": "string (customer | internal | partner | all)", "limit": 50 }`

**Output:** `{ "ideas": [{ "id": "string", "title": "string", "description": "string", "status": "string", "source": "string", "submitter": "string", "vote_count": 0, "created_date": "YYYY-MM-DD", "tags": ["string"] }], "total": 0 }`

### pd_create_idea

Submit a new product idea.

**Input:** `{ "title": "string (required)", "description": "string", "source": "string", "submitter": "string", "tags": ["string"] }`

**Output:** `{ "id": "string", "title": "string", "status": "new" }`

### pd_get_roadmap

Get the product roadmap.

**Input:** `{ "product": "string", "horizon": "string (current | next | future | all)", "limit": 50 }`

**Output:** `{ "product": "string", "items": [{ "id": "string", "title": "string", "description": "string", "horizon": "string", "status": "string", "quarter": "string", "priority": "string", "progress_pct": 0, "linked_ideas": ["string"] }] }`

### pd_list_releases

List releases / changelogs.

**Input:** `{ "product": "string", "status": "string (planned | in_progress | shipped)", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50 }`

**Output:** `{ "releases": [{ "id": "string", "version": "string", "name": "string", "status": "string", "release_date": "YYYY-MM-DD", "features": ["string"], "fixes": ["string"], "notes_url": "string" }], "total": 0 }`

### pd_list_feedback

List customer feedback / survey responses.

**Input:** `{ "source": "string (survey | support | interview | all)", "product": "string", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "sentiment": "string (positive | neutral | negative | all)", "limit": 50 }`

**Output:** `{ "feedback": [{ "id": "string", "source": "string", "summary": "string", "sentiment": "string", "customer": "string", "product": "string", "date": "YYYY-MM-DD", "tags": ["string"], "linked_idea_id": "string" }], "total": 0 }`

## Error Response Shape

All tools return `{"error": "string", "code": "..."}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `pd_list_ideas` | P0 |
| `pd_create_idea` | P0 |
| `pd_get_roadmap` | P0 |
| `pd_list_releases` | P1 |
| `pd_list_feedback` | P1 |