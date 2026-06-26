# Google Token Refresh Watchdog

When the user complains about being "constantly asked to do Google OAuth" or getting re-auth prompts every hour, the root cause is almost always the same: the access token expires (3600s lifetime) and something in the call chain isn't using `Credentials.from_authorized_user_file()` which would auto-refresh.

## Diagnostic

### 1. Check token key structure (most common failure)

The file must have the keys `Credentials.from_authorized_user_file()` expects: `token` (NOT `access_token`), `refresh_token`, `token_uri`, `client_id`, `client_secret`, `scopes` (plural array), `expiry`, `universe_domain`, `account`. If the file has `access_token`, `expires_in`, `scope` (singular), `token_type` instead, it was written by the direct HTTP exchange scripts — it's the **wrong format** even if the data is valid.

```bash
python3 -c "
import json
t = json.load(open('/home/cheehow/.hermes/google_token.json'))
print('Keys:', list(t.keys()))
print('Has scopes (plural):', bool(t.get('scopes')))
print('Has client_id:', bool(t.get('client_id')))
print('Has token_uri:', bool(t.get('token_uri')))
print('Has token key:', bool(t.get('token')))
print('Has access_token key:', bool(t.get('access_token')))
"
```

If `scopes`, `client_id`, or `token_uri` are missing, run the raw refresh test (step 2). If the raw refresh succeeds, fix the format by adding the missing fields from `client_secret.json` and renaming `access_token`→`token` and `scope` (list of 1) → `scopes`.

### 2. Check token state

```bash
python3 -c "
import json
t = json.load(open('/home/cheehow/.hermes/google_token.json'))
print(f'Refresh token present: {bool(t.get(\"refresh_token\"))}')
print(f'Scopes: {len(t.get(\"scopes\",[]))} scopes')
print(f'Expiry: {t.get(\"expiry\")}')
"
```

2. Test if the refresh token is still valid:

```python
import json, urllib.request, urllib.parse

with open('~/.hermes/google_token.json') as f:
    token = json.load(f)
with open('~/.hermes/google_client_secret.json') as f:
    client = json.load(f)

cfg = client['installed']
body = urllib.parse.urlencode({
    'client_id': cfg['client_id'],
    'client_secret': cfg['client_secret'],
    'refresh_token': token['refresh_token'],
    'grant_type': 'refresh_token',
}).encode()

req = urllib.request.Request(cfg['token_uri'], data=body, headers={
    'Content-Type': 'application/x-www-form-urlencoded'
})
resp = json.loads(urllib.request.urlopen(req).read())
print('✅' if 'access_token' in resp else f'❌ {resp}')
```

## Fix: Proactive Token Refresh Watchdog

Even with a valid refresh token, some Google API call paths don't use the `Credentials` class's auto-refresh mechanism. The pragmatic fix is a `no_agent=true` cron job that refreshes the token every 30 minutes (before the 1-hour expiry):

### Script

Place at `~/.hermes/scripts/google-token-refresh.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

TOKEN_FILE="$HOME/.hermes/google_token.json"
CLIENT_FILE="$HOME/.hermes/google_client_secret.json"
LOCK_FILE="/tmp/hermes-google-token-refresh.lock"

exec 200>"$LOCK_FILE"
flock -n 200 || exit 0

[ ! -f "$TOKEN_FILE" ] || [ ! -f "$CLIENT_FILE" ] && exit 0

python3 -c "
import json, urllib.request, urllib.parse, os, sys, time

token_file = os.path.expanduser('$TOKEN_FILE')
client_file = os.path.expanduser('$CLIENT_FILE')

with open(token_file) as f:
    token = json.load(f)
with open(client_file) as f:
    client = json.load(f)

refresh_token = token.get('refresh_token')
if not refresh_token:
    sys.exit(0)

# Refresh if expiring within 15min or already expired
expiry = token.get('expiry')
if expiry:
    try:
        from datetime import datetime
        expiry_ts = datetime.fromisoformat(expiry.replace('Z', '+00:00')).timestamp()
        if expiry_ts and expiry_ts > time.time() + 900:
            sys.exit(0)  # Still fresh
    except:
        pass

cfg = client['installed']
body = urllib.parse.urlencode({
    'client_id': cfg['client_id'],
    'client_secret': cfg['client_secret'],
    'refresh_token': refresh_token,
    'grant_type': 'refresh_token',
}).encode()

req = urllib.request.Request(cfg['token_uri'], data=body,
    headers={'Content-Type': 'application/x-www-form-urlencoded'})
resp = json.loads(urllib.request.urlopen(req).read())

if 'access_token' in resp:
    # Update token — keep all existing keys, write in Credentials format
    token['access_token'] = resp['access_token']
    token['expiry'] = None
    with open(token_file, 'w') as f:
        json.dump(token, f, indent=2)
    # Silent on success
else:
    print(f'REFRESH_FAILED: {resp}')
"
```

### Cron Job

```bash
hermes cron create \
  --name "Google Token Auto-Refresh" \
  --schedule "every 30m" \
  --script google-token-refresh.sh \
  --no-agent \
  --deliver local
```

Key points:
- `deliver: local` — never spams the user
- `no_agent: true` — pure script run, zero LLM cost
- Lock file prevents overlapping runs if the cron scheduler is backed up
- Silent on success, only outputs on failure
- Sets `expiry: None` so the next tool to read the token computes a fresh expiry from the new access token