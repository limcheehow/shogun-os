---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Customer Support Provider Contract

> **Standard tool names and response shapes for customer support integrations.**
> Covers tickets, SLAs, knowledge base, and customer satisfaction.

## Tools

### spt_list_tickets

List support tickets with filters.

**Input:** `{ "search": "string", "status": "string (open | pending | resolved | closed)", "priority": "string (low | medium | high | critical)", "assignee": "string", "contact_email": "string", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50 }`

**Output:** `{ "tickets": [{ "id": "string", "subject": "string", "status": "string", "priority": "string", "assignee": "string", "contact_name": "string", "contact_email": "string", "created_date": "ISO 8601", "updated_date": "ISO 8601", "sla_deadline": "ISO 8601" }], "total": 0 }`

### spt_create_ticket

Create a new support ticket.

**Input:** `{ "subject": "string (required)", "description": "string (required)", "priority": "string", "contact_email": "string", "contact_name": "string", "assignee": "string", "tags": ["string"] }`

**Output:** `{ "id": "string", "subject": "string", "status": "open" }`

### spt_update_ticket

Update ticket status, priority, or assignment.

**Input:** `{ "id": "string (required)", "status": "string", "priority": "string", "assignee": "string", "comment": "string" }`

**Output:** `{ "id": "string", "status": "string" }`

### spt_list_articles

Search knowledge base articles.

**Input:** `{ "query": "string", "category": "string", "limit": 20 }`

**Output:** `{ "articles": [{ "id": "string", "title": "string", "excerpt": "string", "category": "string", "url": "string", "updated_date": "ISO 8601" }], "total": 0 }`

### spt_get_sla_report

Get SLA compliance report.

**Input:** `{ "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "group_by": "string (agent | priority | all)" }`

**Output:** `{ "period": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" }, "total_tickets": 0, "breached": 0, "compliance_rate": 0, "avg_response_time_minutes": 0, "avg_resolution_time_minutes": 0, "breakdown": [{ "key": "string", "total": 0, "breached": 0, "compliance_rate": 0 }] }`

## Error Response Shape

All tools return `{"error": "string", "code": "..."}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `spt_list_tickets` | P0 |
| `spt_create_ticket` | P0 |
| `spt_update_ticket` | P0 |
| `spt_list_articles` | P1 |
| `spt_get_sla_report` | P1 |