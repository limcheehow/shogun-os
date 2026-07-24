# Respond.io API v2 Reference

Base URL: `https://api.respond.io/v2/`
Auth: Header `X-API-Key: <key>`

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/workspace` | GET | Get workspace info |
| `/contacts` | GET | List contacts |
| `/contacts/{id}` | GET | Get contact details |
| `/contacts/{id}/tags` | POST | Tag a contact |
| `/conversations` | GET | List conversations |
| `/conversations/{id}` | GET | Get conversation |
| `/conversations/{id}/assign` | POST | Assign to agent/team |
| `/messages` | POST | Send a message |
| `/messages/{id}` | GET | Get message details |
| `/templates` | GET | List saved templates |
| `/webhooks` | GET/POST | List/create webhooks |

## Webhook Events

| Event | Triggered When |
|-------|---------------|
| `message.created` | Any new message (inbound or outbound) |
| `conversation.assigned` | Conversation assigned to an agent |
| `conversation.closed` | Conversation marked as closed |

## Webhook Payload Shape

```json
{
  "event": "message.created",
  "contact": {
    "id": "cnt_xxx",
    "name": "Alice Tan",
    "phone": "+60123456789"
  },
  "conversation": {
    "id": "conv_xxx",
    "channel": "whatsapp",
    "status": "open"
  },
  "message": {
    "id": "msg_xxx",
    "text": "Hello!",
    "type": "text",
    "timestamp": "2026-07-24T09:30:00Z"
  }
}
```

## Notes

- Rate limit: 60 req/min
- Respond.io uses `X-Signature-256` HMAC-SHA256 webhook verification
- Contacts can have `customFields` with arbitrary JSON
- Messages support: text, image, video, file, template
