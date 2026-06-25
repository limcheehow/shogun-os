# Lark Gateway Setup

> **Configure Hermes Gateway for Lark event subscriptions.**
> Lark requires a public HTTPS webhook URL for receiving events (unlike Slack which uses Socket Mode).

## Overview

Lark bots receive events (messages, mentions, bot additions) via **event subscriptions** — Lark POSTs JSON events to your webhook URL. The Hermes Gateway can handle these.

Architecture:
```
Lark Platform
  ↓ POST JSON events to your webhook URL
Your Webhook Server (ngrok / Cloudflare Tunnel)
  ↓
Hermes Gateway (per profile)
  ↓
Agent responds with domain knowledge
```

## Step 1: Expose a Public URL

Lark needs a public HTTPS endpoint. Options:

**Option A: Cloudflare Tunnel (recommended)**
```bash
cloudflared tunnel --url http://localhost:8080
```

**Option B: ngrok**
```bash
ngrok http 8080
```

**Option C: Cloudflare Tunnel with service**
```bash
cloudflared tunnel run <tunnel-name>
```

Get your public URL: `https://your-tunnel.ngrok.io` or `https://your-tunnel.trycloudflare.com`

## Step 2: Configure Event Subscription in Lark Developer Console

1. Go to [Lark Developer Console](https://open.larksuite.com/app)
2. Select your app → **Events & Callbacks**
3. Click **Add Event Subscription**
4. Set **Request URL**: `https://your-public-url/webhooks/lark`
5. Lark will send a verification challenge — your gateway must respond with the challenge token
6. Subscribe to events:

| Event | Purpose |
|-------|---------|
| `im.message.receive_v1` | When the bot receives a message |
| `im.message.message_read_v1` | When a message is read |
| `im.chat.member.bot.added_v1` | When bot is added to a group |

7. Click **Confirm**

## Step 3: Configure Hermes Gateway

### Profile Config

In the profile's `config.yaml`, add the webhook:

```yaml
gateway:
  webhooks:
    lark:
      path: /webhooks/lark
```

Or configure globally in `~/.hermes/config.yaml`:

```yaml
gateway:
  enabled: true
  host: 0.0.0.0
  port: 8080
  webhooks:
    lark:
      path: /webhooks/lark
```

### Event Handling

When Lark sends an event, the gateway passes it to the profile's agent. The agent should:

1. Verify the webhook challenge (first request)
2. Parse the event body
3. Respond based on message content

The Lark provider includes helpers for this:

```python
from comm.lark import LarkProvider

provider = LarkProvider(os.environ)

# Verify webhook challenge
if body.get("type") == "url_verification":
    return {"challenge": body["challenge"]}

# Parse incoming event
event = provider.parse_webhook_event(body)
if event and event["type"] == "im.message.receive_v1":
    # Agent responds with domain knowledge
    response = agent.process_message(event["text"], event["sender"])
    provider.send_dm(event["sender"], response)
```

## Step 4: Test the Webhook

```bash
# Send a test event to your local gateway
curl -X POST http://localhost:8080/webhooks/lark \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123"}'
# Expected: {"challenge": "test123"}

# Send a simulated message event
curl -X POST http://localhost:8080/webhooks/lark \
  -H "Content-Type: application/json" \
  -d '{"event":{"event_type":"im.message.receive_v1","message":{"chat_type":"p2p","content":"{\"text\":\"Hello\"}","sender":{"sender_id":{"user_id":"ou_test"}}}}}'
```

## Security

- Lark signs webhook events with a **Verification Token** (set in Developer Console → Events & Callbacks)
- Verify every request: check `X-Lark-Request-Timestamp` and `X-Lark-Request-Nonce` headers
- Always respond to `url_verification` challenges within 3 seconds

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Challenge verification failed` | Webhook URL didn't respond with the challenge token. Check gateway is running. |
| Events not received | Check **Event Subscription** is enabled. May need to publish a new app version. |
| `403 Forbidden` from Lark | Check Verification Token matches. |
| Gateway not reachable | Cloudflare tunnel or ngrok not running. Use `curl http://localhost:8080/webhooks/lark` to test locally. |
| Bot doesn't respond | Verify `im.message.receive_v1` event is subscribed. Bot needs to be added to the chat first. |
| Token expired | Lark tokens expire every 2 hours. The provider auto-refreshes — check `LARK_APP_ID` and `LARK_APP_SECRET` are correct. |