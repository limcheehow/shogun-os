---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# {{DOMAIN_TITLE}} Provider Contract

> **Standard tool names and response shapes for {{DOMAIN}} integrations.**
> Any provider that implements these tools can be plugged into any Hermes Agent profile.

## Tools

### {{PREFIX}}_list_{{ENTITIES}}

List with optional filters.

**Input:**
```json
{
  "search": "string (optional)",
  "status": "string (optional)",
  "date_from": "string (YYYY-MM-DD, optional)",
  "date_to": "string (YYYY-MM-DD, optional)",
  "limit": "integer (optional, default: 50)"
}
```

**Output:**
```json
{
  "{{ENTITIES}}": [{ "id": "string" }],
  "total": "integer"
}
```

### {{PREFIX}}_create_{{ENTITY}}

**Input:** `{ "{{REQUIRED_FIELD}}": "string (required)" }`

**Output:** `{ "id": "string", "status": "string" }`

## Error Response

All tools return:
`{"error": "string", "code": "MISSING_FIELD | AUTH_FAILED | RATE_LIMITED | NOT_FOUND | PROVIDER_ERROR"}`

## Provider Requirements

| Tool | Priority |
|------|----------|
| `{{PREFIX}}_list_{{ENTITIES}}` | P0 |
| `{{PREFIX}}_create_{{ENTITY}}` | P0 |
