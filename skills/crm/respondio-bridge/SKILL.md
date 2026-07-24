---
name: respondio-bridge
description: "Runtime bridge between Kizuna (Hermes CRM) and Respond.io. Handles inbound webhooks, sends replies with template support, syncs contacts to brain, tracks response SLA, and manages conversation assignment."
triggers:
  - "respondio"
  - "respond.io"
  - "respond io webhook"
  - "customer message"
  - "send template"
category: crm
---

# Respond.io Bridge — Kizuna Runtime Integration

## Overview

This bridge connects the **Kizuna (CRM) Hermes profile** to **Respond.io**, providing:

1. **Inbound message handling** — Respond.io forwards customer messages via webhook → Hermes processes them
2. **Template replies** — Fixed response templates stored in brain, sent via Respond.io API
3. **Contact sync** — New contacts auto-created as brain people pages
4. **Conversation assignment** — Hermes-first or Human-first routing
5. **Response SLA tracking** — First response time, resolution time

## Architecture

```
┌──────────────┐     Webhook      ┌──────────────────┐
│  Respond.io  │ ──────────────>  │  Hermes (Kizuna) │
│              │                  │                  │
│  Channels:   │  <────────────── │  - Understands   │
│  - IG DM     │   API Response   │  - Routes        │
│  - FB Msgr   │                  │  - Escalates     │
│  - WhatsApp  │                  │  - Logs to brain │
│  - Website   │                  │                  │
└──────────────┘                  └──────────────────┘
         │                                │
         │                        ┌───────┴────────┐
         │                        │  gbrain         │
         │                        │  - Templates    │
         │                        │  - Contacts     │
         │                        │  - Conversations│
         │                        └────────────────┘
```

## Configuration

Config lives in `~/.hermes/profiles/kizuna/config.yaml`:

```yaml
customer_communication:
  platform: respondio
  enabled: true
  channels:
    - ig
    - fb
    - wa
    - web
  assignment_model: hermes-first  # hermes-first | human-first | co-pilot
  auto_respond: true
  webhook_secret: <from onboarding>
  escalation_keywords:
    - "speak to a person"
    - "manager"
    - "complaint"
    - "refund"
```

Credentials in `~/.hermes/profiles/kizuna/.secrets/secrets.env`:
```
RESPONDIO_API_KEY=<key>
```

## Inbound Message Flow (Webhook Handler)

When Respond.io sends a webhook (`message.created`):

### Step 1: Verify Webhook Signature

```bash
# Verify HMAC-SHA256 signature
echo -n "$request_body" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET"
```

Compare with `X-Signature-256` header. Reject mismatches.

### Step 2: Extract Message Context

Fields from the webhook payload:
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
    "text": "Hi, I'm interested in your product",
    "type": "text",
    "timestamp": "2026-07-24T09:30:00Z"
  }
}
```

### Step 3: Resolve or Create Contact

```bash
python3 ~/.hermes/skills/crm/respondio-bridge/scripts/sync-contact.py \
  --api-key "$RESPONDIO_KEY" \
  --contact-id "cnt_xxx" \
  --channel "wa"
```

This creates/updates `~/brain/people/contacts/<channel>-<respondio-contact-id>.md`

### Step 4: Classify Intent

Ask Hermes (self-refer):
> "Classify this customer message as: inquiry, complaint, lead, support, or other.
> Message: \"{text}\" from {contact_name} on {channel}"

If `lead` → trigger deal creation flow
If `complaint` → escalate priority
If `inquiry` → route to template or free-form reply

### Step 5: Respond

**If assignment_model = hermes-first:**
- Search brain for matching template: `gbrain search "template: {keywords}"`
- If matching template found → send template reply
- If no template → draft a free-form reply
- Send via Respond.io API

**If assignment_model = human-first:**
- Don't send response. Tag the conversation in Respond.io for human agent.
- Optionally: write a suggestion to the conversation notes.

**If assignment_model = co-pilot:**
- Draft a reply but don't send. Write it as a suggested reply in Respond.io API.

### Step 6: Log to Brain

```bash
python3 ~/.hermes/skills/crm/respondio-bridge/scripts/log-conversation.py \
  --contact "cnt_xxx" \
  --channel "wa" \
  --message "Hi, I'm interested in your product" \
  --response "Sure! Let me help you with that..." \
  --respondio-conversation-id "conv_xxx"
```

Creates timeline entry on the contact's brain page.

## Sending Messages

### Send Text Reply

```bash
curl -s -X POST "https://api.respond.io/v2/messages" \
  -H "X-API-Key: $RESPONDIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_xxx",
    "type": "text",
    "text": "Thank you for reaching out! How can I help you today?"
  }'
```

### Send Template Reply

Templates are stored as brain pages in `~/brain/templates/respondio-*.md`:

```yaml
---
type: template
platform: respondio
name: welcome-message
tags: [template, whatsapp, welcome]
---

# Welcome Message

Body: |
  Hi {{contact_name}}! 👋
  
  Thank you for contacting {company}. 
  How can I help you today?
  
  Reply with:
  1️⃣ Product inquiry
  2️⃣ Support
  3️⃣ Talk to a human
```

Use the template SDK:
```bash
python3 ~/.hermes/skills/crm/respondio-bridge/scripts/send-template.py \
  --name "welcome-message" \
  --conversation "conv_xxx" \
  --contact-name "Alice"
```

### Send Media / Image

```bash
curl -s -X POST "https://api.respond.io/v2/messages" \
  -H "X-API-Key: $RESPONDIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conv_xxx",
    "type": "image",
    "media_url": "https://example.com/catalog.jpg"
  }'
```

## Contact Management

### Lookup Contact

```bash
curl -s "https://api.respond.io/v2/contacts/{id}" \
  -H "X-API-Key: $RESPONDIO_KEY" | jq .
```

### Sync All Contacts to Brain

```bash
python3 ~/.hermes/skills/crm/respondio-bridge/scripts/sync-all-contacts.py \
  --api-key "$RESPONDIO_KEY"
```

This batch syncs all Respond.io contacts to brain people pages under `~/brain/people/contacts/`.

### Tag Contact

```bash
curl -s -X POST "https://api.respond.io/v2/contacts/{id}/tags" \
  -H "X-API-Key: $RESPONDIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["lead", "interested"]}'
```

## Escalation to Human

When Hermes can't handle a query (intent is unclear, customer asks for human, complaint keywords detected):

### Method 1: Respond.io Assignment API

```bash
curl -s -X POST "https://api.respond.io/v2/conversations/{id}/assign" \
  -H "X-API-Key: $RESPONDIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "assignee_id": "team_xxx"  # or leave unset for round-robin
  }'
```

### Method 2: Internal Notification

Post to Kizuna's Slack/Telegram channel:
```
🚨 *Escalation needed*
Channel: WhatsApp (Alice Tan)
Message: "I need to speak to a manager"
Reason: escalation_keyword matched
→ [Open in Respond.io](https://app.respond.io/conversations/conv_xxx)
```

## SLA Monitoring

### Check response times

```bash
python3 ~/.hermes/skills/crm/respondio-bridge/scripts/check-sla.py \
  --api-key "$RESPONDIO_KEY" \
  --hours 24 \
  --threshold-minutes 5
```

Output:
```
📊 SLA Report (last 24h)
━━━━━━━━━━━━━━━━━━━━━━━━━
Total conversations: 47
Auto-responded (≤5s):   38 (81%)
Human first response:    5 (11%, avg 3m12s)
Breached (>30min):       2 (4%)
  - conv_abc: Alice Tan → WA (45min)
  - conv_def: Bob Lee → IG (33min)
```

This can run as a cron job:
```bash
# ~/.hermes/profiles/kizuna/cron/sla-report
0 9 * * 1-5 python3 ~/.hermes/skills/crm/respondio-bridge/scripts/check-sla.py \
  --api-key "$RESPONDIO_KEY" \
  --hours 24 | slack-post --channel #crm-stats
```

## Templates in Brain — Authoring

When the user asks "add a new template":

1. Create a brain page at `~/brain/templates/respondio-<name>.md`
2. Frontmatter: `type: template`, `platform: respondio`, `channel: wa` (optional)
3. Body: template body with `{{variables}}`
4. The bridge loads this at runtime when intent matches the template name or keywords

List all templates:
```
gbrain search "type:template platform:respondio"
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Webhook returning 401 | Secret mismatch | Regenerate webhook secret in Respond.io dashboard |
| "Contact not found" | Contact not synced to brain | Run `sync-contact.py` manually |
| Template not matched | Wrong intent classification | Add more keywords to the template's brain page tags |
| Human escalation not working | No assignee configured | Check Respond.io team assignment settings |
| SLA alert too noisy | Threshold too tight | Adjust `--threshold-minutes` |
