# Chatwoot API v1 Reference

Base URL: `{api_url}/api/v1/`
Auth: Header `api_access_token: <personal-access-token>`

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/conversations` | GET | List conversations (filter by status, inbox_id) |
| `/conversations/{id}` | GET | Get conversation details with messages |
| `/conversations/{id}/messages` | POST | Send message / private note |
| `/conversations/{id}/assignments` | POST | Assign/unassign agent |
| `/conversations/{id}/toggle_status` | POST | Resolve/reopen |
| `/contacts` | GET | List contacts |
| `/contacts/{id}` | GET | Get contact |
| `/contacts/{id}/conversations` | GET | Contact's conversation history |
| `/inboxes` | GET | List all inboxes |
| `/accounts/{id}/agents` | GET | List agents |
| `/accounts/{id}/canned_response` | GET/POST | List/create canned responses |

## Message Types

| `message_type` | Meaning |
|----------------|---------|
| `0` | Incoming (from customer) |
| `1` | Outgoing (agent sends) |
| `2` | Activity (system event) |

## Private Notes

Set `"private": true` to make the message visible only to agents.

## Chatwoot Webhook

Events forwarded (configurable in Chatwoot dashboard):
- `message_created`
- `conversation_created`
- `conversation_status_changed`
- `conversation_updated`
- `contact_created`
- `contact_updated`

Signed with `X-Chatwoot-Signature` header (HMAC-SHA256).
