# Telegram `allowed_users` Gets Wiped on Updates

## Problem

After a Hermes update (`hermes update`), the `telegram.allowed_users` config field disappears from `~/.hermes/config.yaml`. When absent, the gateway defaults to blocking all non-whitelisted users. The bot owner's DM still works, but team members get silently blocked.

## Diagnosis

```bash
tail -100 ~/.hermes/logs/gateway.log | grep "Unauthorized"
```

Expected output when the field is missing:
```
WARNING gateway.run: Unauthorized user: 6292271928 (Jason Cham) on telegram
```

## Fix

```bash
hermes config set telegram.allowed_users ''
```

No gateway restart needed — config is read live from disk.

## Behavior

- `allowed_users: ''` (empty string) = allow everyone
- `allowed_users` absent entirely = blocks everyone except bot owner
- `allowed_users: '629298834,6292271928'` = allow only specific user IDs
