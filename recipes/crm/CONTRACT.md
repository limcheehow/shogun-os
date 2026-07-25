---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# CRM Provider Contract

> **Standard tool names and response shapes for CRM integrations.**
> Covers contacts, deals/pipeline, activities, and account management.

## Tools

### crm_list_contacts

List CRM contacts.

**Input:** `{ "search": "string", "type": "string (lead | contact | all)", "limit": 50, "offset": 0 }`

**Output:** `{ "contacts": [{ "id": "string", "name": "string", "email": "string", "phone": "string", "company": "string", "type": "string", "owner": "string" }], "total": 0 }`

### crm_create_contact

Create a new contact/lead.

**Input:** `{ "name": "string (required)", "email": "string", "phone": "string", "company": "string", "type": "string (lead | contact)", "owner": "string" }`

**Output:** `{ "id": "string", "name": "string" }`

### crm_list_deals

List deals in the pipeline.

**Input:** `{ "search": "string", "stage": "string", "pipeline": "string", "owner": "string", "limit": 50, "offset": 0 }`

**Output:** `{ "deals": [{ "id": "string", "name": "string", "contact_id": "string", "contact_name": "string", "value": 0, "stage": "string", "pipeline": "string", "owner": "string", "probability": 0, "expected_close_date": "YYYY-MM-DD" }], "total": 0 }`

### crm_create_deal

Create a new deal.

**Input:** `{ "name": "string (required)", "contact_id": "string (required)", "value": "number", "stage": "string", "pipeline": "string", "owner": "string", "expected_close_date": "YYYY-MM-DD" }`

**Output:** `{ "id": "string", "name": "string", "stage": "string" }`

### crm_update_deal_stage

Move a deal to a different stage.

**Input:** `{ "id": "string (required)", "stage": "string (required)" }`

**Output:** `{ "id": "string", "stage": "string" }`

### crm_list_activities

List activities/events for a contact or deal.

**Input:** `{ "contact_id": "string", "deal_id": "string", "type": "string (call | email | meeting | note)", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50 }`

**Output:** `{ "activities": [{ "id": "string", "type": "string", "subject": "string", "date": "YYYY-MM-DD", "owner": "string", "notes": "string" }], "total": 0 }`

### crm_create_activity

Log a new activity.

**Input:** `{ "type": "string (required)", "subject": "string (required)", "contact_id": "string", "deal_id": "string", "date": "YYYY-MM-DD", "notes": "string", "owner": "string" }`

**Output:** `{ "id": "string", "type": "string", "subject": "string" }`

## Error Response Shape

All tools return `{"error": "string", "code": "..."}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `crm_list_contacts` | P0 |
| `crm_create_contact` | P0 |
| `crm_list_deals` | P0 |
| `crm_create_deal` | P0 |
| `crm_update_deal_stage` | P0 |
| `crm_list_activities` | P1 |
| `crm_create_activity` | P1 |