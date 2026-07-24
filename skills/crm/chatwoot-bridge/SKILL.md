---
name: chatwoot-bridge
description: "Runtime bridge between Kizuna (Hermes CRM) and Chatwoot. Handles inbound webhooks, sends replies, manages conversation assignment, tracks SLA, and syncs contacts to brain."
triggers:
  - "chatwoot"
  - "chatwoot webhook"
  - "customer message"
  - "shared inbox"
category: crm
---

# Chatwoot Bridge — Kizuna Runtime Integration

## Overview

This bridge connects the **Kizuna (CRM) Hermes profile** to **Chatwoot** (self-hosted open source customer engagement platform), providing:

1. **Inbound message handling** — Chatwoot forwards customer messages via webhook → Hermes processes them
2. **Draft replies** — Hermes drafts replies for human agents to review and send
3. **Auto-respond** — Hermes responds directly for simple inquiries (Hermes-first mode)
4. **Contact sync** — Chatwoot contacts → brain people pages
5. **Conversation assignment** — Assign conversations to agents via Chatwoot API
6. **SLA tracking** — Response time monitoring

## Architecture

```
┌──────────────┐    Webhook     ┌──────────────────┐
│  Chatwoot    │ ────────────>  │  Hermes (Kizuna) │
│              │                │                  │
│  Inboxes:    │  <──────────── │  - Understands   │
│  - IG DM     │   API Reply    │  - Drafts Reply  │
│  - FB Msgr   │                │  - Routes        │
│  - WhatsApp  │                │  - Escalates     │
│  - Website   │                │  - Logs to brain │
│  - Email     │                │                  │
└──────┬───────┘                └──────────────────┘
       │                                │
       │                        ┌───────┴────────┐
       │   Agent Dashboard      │  gbrain         │
       │   (human agents)       │  - Templates    │
       ▼                        │  - Contacts     │
┌─────────────────┐              │  - Conversations│
│  Chatwoot UI    │              └────────────────┘
│  (browser)      │
└─────────────────┘
```

## Configuration

```yaml
# ~/.hermes/profiles/kizuna/config.yaml
customer_communication:
  platform: chatwoot
  enabled: true
  chatwoot:
    api_url: http://localhost:3000
    access_token: <stored in .secrets>
    webhook_secret: <from onboarding>
    account_id: 1  # Chatwoot account ID
  channels:
    - web
    - wa
    - fb
    - ig
  assignment_model: co-pilot  # hermes-first | human-first | co-pilot
  auto_respond: true
  escalation_keywords:
    - "speak to a person"
    - "manager"
    - "complaint"
    - "refund"
```

Credentials in `~/.hermes/profiles/kizuna/.secrets/secrets.env`:
```
CHATWOOT_ACCESS_TOKEN=<personal-access-token>
CHATWOOT_API_URL=http://localhost:3000
```

## Chatwoot API Basics

All calls go to `{api_url}/api/v1/` with header `api_access_token: {token}`.

### Common Endpoints

| Purpose | Endpoint |
|---------|----------|
| List conversations | `GET /conversations?status=open&inbox_id={id}` |
| Get conversation | `GET /conversations/{id}` |
| Send message | `POST /conversations/{id}/messages` |
| Assign conversation | `POST /conversations/{id}/assignments` |
| Toggle status | `POST /conversations/{id}/toggle_status` |
| List agents | `GET /accounts/{id}/agents` |
| List inboxes | `GET /inboxes` |
| Get contact | `GET /contacts/{id}` |

## Inbound Message Flow

When Chatwoot sends a webhook (`message_created`):

### Step 1: Verify Webhook

```bash
# Chatwoot signs with HMAC-SHA256 using the webhook secret
echo -n "$request_body" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET"
```

Match against `X-Chatwoot-Signature` header.

### Step 2: Extract Context

Webhook payload shape:
```json
{
  "event": "message_created",
  "id": 1,
  "conversation": {
    "id": 42,
    "inbox_id": 1,
    "status": "open",
    "assignee": null
  },
  "message": {
    "id": 100,
    "content": "Hi, I'd like a quote",
    "message_type": "incoming",
    "sender": {
      "id": 200,
      "name": "Alice Tan"
    },
    "created_at": "2026-07-24T09:30:00Z"
  }
}
```

### Step 3: Resolve Contact

```bash
python3 ~/.hermes/skills/crm/chatwoot-bridge/scripts/sync-contact.py \
  --api-url "$CHATWOOT_API_URL" \
  --access-token "$CHATWOOT_TOKEN" \
  --contact-id 200
```

Creates/updates `~/brain/people/contacts/chatwoot-<contact-id>.md`

### Step 4: Classify Intent

Same as respond.io bridge — classify as inquiry/complaint/lead/support/other.

### Step 5: Respond or Draft

**If assignment_model = hermes-first:**
```bash
# Send auto-reply via Chatwoot API
curl -s -X POST "$CHATWOOT_API_URL/api/v1/conversations/42/messages" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Thanks for reaching out! How can I help?", "message_type": "outgoing"}'
```

**If assignment_model = co-pilot:**
Post a **private note** (visible only to agents) with the suggested reply:
```bash
curl -s -X POST "$CHATWOOT_API_URL/api/v1/conversations/42/messages" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "🤖 Suggested reply:\n> Thank you for your interest, Alice! I'd be happy to help with a quote. Could you let me know which product you're looking at?", "message_type": "outgoing", "private": true}'
```

**If assignment_model = human-first:**
Do nothing. Chatwoot's notification system will alert the assigned agent.

### Step 6: Log to Brain

```bash
python3 ~/.hermes/skills/crm/chatwoot-bridge/scripts/log-conversation.py \
  --api-url "$CHATWOOT_API_URL" \
  --access-token "$CHATWOOT_TOKEN" \
  --conversation-id 42
```

Creates timeline entry on the contact's brain page.

## Sending Messages

### Send Text Reply

```bash
curl -s -X POST "http://localhost:3000/api/v1/conversations/{id}/messages" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello! How can I help you today?", "message_type": "outgoing"}'
```

### Send Private Note (agent-only)

```bash
curl -s -X POST "http://localhost:3000/api/v1/conversations/{id}/messages" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "🤖 Suggested template: welcome-message", "message_type": "outgoing", "private": true}'
```

### Assign Conversation to Agent

```bash
curl -s -X POST "http://localhost:3000/api/v1/conversations/{id}/assignments" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_id": 5}'
```

Or unassign (round-robin):
```bash
curl -s -X POST "http://localhost:3000/api/v1/conversations/{id}/assignments" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Resolve Conversation

```bash
curl -s -X POST "http://localhost:3000/api/v1/conversations/{id}/toggle_status" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved"}'
```

## Contact Management

### List All Contacts

```bash
curl -s "http://localhost:3000/api/v1/contacts" \
  -H "api_access_token: $CHATWOOT_TOKEN" | jq '.payload[] | {id, name, email, phone_number}'
```

### Sync All Contacts to Brain

```bash
python3 ~/.hermes/skills/crm/chatwoot-bridge/scripts/sync-all-contacts.py \
  --api-url "$CHATWOOT_API_URL" \
  --access-token "$CHATWOOT_TOKEN"
```

## Escalation to Human

When Hermes can't handle:

### Method 1: Assign + Notify

```bash
# 1. Assign to a specific agent (or unassign for round-robin)
curl -s -X POST "$CHATWOOT_API_URL/api/v1/conversations/{id}/assignments" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_id": null}'  # null = round-robin

# 2. Add private note explaining the escalation reason
curl -s -X POST "$CHATWOOT_API_URL/api/v1/conversations/{id}/messages" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "🚨 Escalation: Customer requested human. Intent: complaint about billing.", "message_type": "outgoing", "private": true}'
```

### Method 2: Telegram/Slack Alert

Post to the Kizuna alert channel:
```
🚨 *Escalation needed*
Customer: Alice Tan (WhatsApp)
Message: "I want a refund"
→ [Open in Chatwoot](http://localhost:3000/app/accounts/1/conversations/42)
```

## SLA Monitoring

### Check via Chatwoot API

```bash
python3 ~/.hermes/skills/crm/chatwoot-bridge/scripts/check-sla.py \
  --api-url "$CHATWOOT_API_URL" \
  --access-token "$CHATWOOT_TOKEN" \
  --hours 24
```

Output — same format as respond.io SLA report.

Can run as cron:
```bash
# ~/.hermes/profiles/kizuna/cron/sla-report
0 9 * * 1-5 python3 ~/.hermes/skills/crm/chatwoot-bridge/scripts/check-sla.py \
  --api-url "$CHATWOOT_API_URL" \
  --access-token "$CHATWOOT_TOKEN" \
  --hours 24 | slack-post --channel #crm-stats
```

## Templates in Brain

Same as respond.io bridge — templates stored at `~/brain/templates/chatwoot-*.md`:

```yaml
---
type: template
platform: chatwoot
name: quote-request
channel: wa
tags: [template, sales]
---

# Quote Request

Hi {{contact_name}}!

Thanks for your interest in {{product}}. Here's the information I need to prepare a quote:

1. Approximate quantity
2. Timeline
3. Any special requirements

Once I have these, I'll get back to you within 2 hours!
```

## Canned Responses in Chatwoot UI

You can also push templates into Chatwoot as **canned responses** (available in the agent UI):

```bash
curl -s -X POST "http://localhost:3000/api/v1/accounts/1/canned_response" \
  -H "api_access_token: $CHATWOOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "short_code": "quote",
    "content": "Thanks for your interest! Here's what I need to prepare a quote..."
  }'
```

List existing:
```bash
curl -s "http://localhost:3000/api/v1/accounts/1/canned_response" \
  -H "api_access_token: $CHATWOOT_TOKEN"
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Webhook returning 401 | Secret mismatch | Check config `chatwoot.webhook_secret` vs Chatwoot dashboard |
| "Conversation not found" | Wrong account_id | Verify `chatwoot.account_id` in config |
| Message not sending | Access token scope | Generate token from Chatwoot Profile → Personal Access Tokens |
| Private note visible to customer | Missing `private: true` field | Add `"private": true` or use `message_type: "activity"` |
| Chatwoot container unhealthy | Postgres connection | Check `docker compose logs web` for PG errors |
