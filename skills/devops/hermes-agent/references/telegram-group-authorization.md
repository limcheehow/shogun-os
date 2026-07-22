# Telegram Group Authorization

## Modern Approach: `TELEGRAM_GROUP_ALLOWED_CHATS`

In `~/.hermes/.env`:
```
TELEGRAM_GROUP_ALLOWED_CHATS=-1003773708968,-1003882643127,-1003958841816
```

This authorizes ALL members of listed groups — no per-user allowlist needed. When someone joins a group, they're automatically authorized. Never touch the list again when new members join.

## Deprecated: `allowed_users` / `allowed_chats` in config.yaml

These are old config fields that used comma-separated user IDs. The modern approach is env vars:
- `TELEGRAM_GROUP_ALLOWED_CHATS` — chat IDs, all members authorized
- `TELEGRAM_ALLOWED_USERS` — specific user IDs with DM+group access
- `TELEGRAM_GROUP_ALLOWED_USERS` — user IDs with group-only access (no DM)

Use `*` to allow everyone: `TELEGRAM_ALLOWED_USERS=*`

Use `GATEWAY_ALLOW_ALL_USERS=true` to bypass all per-platform allowlists.

## Finding Group Chat IDs

From gateway logs:
```bash
grep -oP 'group:-?\d+' ~/.hermes/logs/gateway.log | sort -u
```

From Telegram API:
```bash
TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' ~/.hermes/.env | cut -d= -f2-)
curl -s "https://api.telegram.org/bot${TOKEN}/getChat?chat_id=<ID>" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['title'])"
```

## Docs Reference

https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram — search for "TELEGRAM_GROUP_ALLOWED_CHATS"
