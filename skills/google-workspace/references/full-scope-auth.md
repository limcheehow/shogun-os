# Full-Scope Google OAuth — Workspace + Fitness in One Flow

## Problem

The `setup.py` SCOPES list now includes **12 workspace + 22 fitness scopes** (34 total).
But a user may have a token from an older authorization that only granted a subset
(e.g., only Drive scopes). Re-authorizing with a fresh consent flow is the only way
to add new scopes — refreshing an existing token can't expand the grant.

## The Pattern

Generate an OAuth URL that asks for **all scopes at once**, including ones the user might need in the future. Google's `include_granted_scopes=true` flag merges the new grant with the existing one, but the key is to use `prompt=consent` to force the consent screen even if the user previously authorized.

## Complete Scope List

```python
ALL_SCOPES = [
    # --- Workspace ---
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/contacts",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/presentations",

    # --- Fitness (read+write for each category) ---
    "https://www.googleapis.com/auth/fitness.activity.read",
    "https://www.googleapis.com/auth/fitness.activity.write",
    "https://www.googleapis.com/auth/fitness.body.read",
    "https://www.googleapis.com/auth/fitness.body.write",
    "https://www.googleapis.com/auth/fitness.heart_rate.read",
    "https://www.googleapis.com/auth/fitness.heart_rate.write",
    "https://www.googleapis.com/auth/fitness.sleep.read",
    "https://www.googleapis.com/auth/fitness.sleep.write",
    "https://www.googleapis.com/auth/fitness.location.read",
    "https://www.googleapis.com/auth/fitness.location.write",
    "https://www.googleapis.com/auth/fitness.nutrition.read",
    "https://www.googleapis.com/auth/fitness.nutrition.write",
    "https://www.googleapis.com/auth/fitness.blood_glucose.read",
    "https://www.googleapis.com/auth/fitness.blood_glucose.write",
    "https://www.googleapis.com/auth/fitness.blood_pressure.read",
    "https://www.googleapis.com/auth/fitness.blood_pressure.write",
    "https://www.googleapis.com/auth/fitness.body_temperature.read",
    "https://www.googleapis.com/auth/fitness.body_temperature.write",
    "https://www.googleapis.com/auth/fitness.oxygen_saturation.read",
    "https://www.googleapis.com/auth/fitness.oxygen_saturation.write",
    "https://www.googleapis.com/auth/fitness.reproductive_health.read",
    "https://www.googleapis.com/auth/fitness.reproductive_health.write",
]
```

## Generating the Auth URL

```python
from google_auth_oauthlib.flow import Flow

flow = Flow.from_client_secrets_file(
    "~/.hermes/google_client_secret.json",
    scopes=ALL_SCOPES,
    redirect_uri="http://localhost",
)

auth_url, _ = flow.authorization_url(
    access_type="offline",
    include_granted_scopes="true",
    prompt="consent",  # CRITICAL: forces consent screen to show ALL scopes
)
```

## Key Details

1. **`prompt=consent` is required** — without it, Google skips the consent screen if the user already authorized, and new scopes never get granted
2. **`include_granted_scopes=true`** — tells Google to merge this grant with the user's existing authorizations (harmless, just best practice)
3. **`access_type=offline`** — ensures a refresh_token is returned
4. **No deduplication needed** — the scope list uses narrow scopes (`drive.readonly`, `drive.file`) rather than the broad `drive` scope, so there are no overlaps to worry about.

## After Authorization

The user pastes back the redirect URL. Exchange it with the same flow object:

```python
flow.fetch_token(authorization_response=redirect_url)
creds = flow.credentials
# Save to ~/.hermes/google_token.json
with open(token_path, "w") as f:
    f.write(creds.to_json())
```

The new token now has all requested scopes permanently. The auto-refresh cron (every 30m) will maintain it without re-authorization — but it CANNOT add new scopes on its own; that always requires a fresh consent flow.

## Diagnosing Missing Scopes

Check `~/.hermes/google_token.json`:

```python
import json
with open("~/.hermes/google_token.json") as f:
    t = json.load(f)
print(t.get("scopes", []))
```

A token with only `["drive.file", "documents"]` will fail on fitness, gmail, and calendar calls. A full token should list 34 scope URLs (12 workspace + 22 fitness).

## Scope Recovery Without Re-Auth

If the original OAuth consent granted all scopes but a narrower-scope operation overwrote the token, you can recover without user-facing re-auth:

```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

FULL_SCOPES = [...]  # list from above
creds = Credentials.from_authorized_user_file(token_path, FULL_SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(token_path, "w") as f:
        f.write(creds.to_json())
```

The refresh token carries the original grant and re-issues an access token with the full scope set. Only if this fails (the refresh token itself lacks the scope) should you fall through to `--revoke` + re-auth.

## 🚨 Pitfall: oauthlib Rejects Expanded Scopes From Google

When exchanging the auth code, `oauthlib` has a **strict scope-matching check** in `oauthlib.oauth2.rfc6749.tokens.parse_token_response()`. If Google returns scopes that don't exactly match the requested set (e.g., it silently adds `drive.readonly` or `contacts` alongside your requested scopes), the exchange fails with:

```
Warning: Scope has changed from "[...requested scopes...]"
  to "[...returned scopes that differ...]".
oauthlib.oauth2.rfc6749.errors.MismatchingStateError: ...
```

**Fix:** Monkey-patch `parse_token_response` to accept any scope Google returns **before** calling `flow.fetch_token()`:

```python
from oauthlib.oauth2.rfc6749 import tokens as oauth_tokens
_orig = oauth_tokens.parse_token_response
oauth_tokens.parse_token_response = lambda body, scope=None: _orig(body, scope=None)
```

This bypasses the strict scope comparison while keeping all other token validation intact. It's safe — the actual scopes granted are still captured in `creds.scopes` from the response and saved to the token file.

**Important:** This must be patched at the module level before any `Flow` object calls `fetch_token`. The patch applies globally to the `oauthlib` module for the lifetime of the Python process.

### Why Google Returns Extra Scopes

Google's OAuth consent screen can silently include:
- Related scopes it deems necessary (e.g., `contacts` alongside `contacts.readonly`)
- Scopes from previous authorizations the user approved
- Scopes required by API dependencies (e.g., `drive.readonly` when `drive` was requested)

This is normal behavior — the token will still contain all scopes you need. The monkey-patch is the official workaround for clients that can't accept scope expansion.

### This Also Affects `setup.py --auth-code`

If you use the `google-workspace` skill's `setup.py --auth-code` and it fails with a scope mismatch, this is the same underlying issue. The fix is the same monkey-patch. Since `setup.py` is a bundled script, add the monkey-patch at the top of a wrapper script or patch it directly in `/tmp` for one-shot use.\n\n**Note:** `setup.py`'s SCOPES list now includes all 34 scopes (workspace + fitness), so if you're running a current version of the skill, the direct `--auth-url` → `--auth-code` flow should work for fitness scopes without a standalone script.

### Direct HTTP Exchange (Recommended — Avoids All Oauthlib Issues)

Available as a standalone script: `templates/exchange-full-scope-http.py`

This method uses **raw `urllib.request`** against Google's token endpoint instead of `google_auth_oauthlib.Flow`. Advantages:
- No oauthlib scope-mismatch errors (the `Warning: Scope has changed` rejection)
- No PKCE verifier/state management
- No monkey-patching required
- Works every time — even when Google returns expanded scopes

```bash
python3 ~/.hermes/skills/productivity/google-workspace/templates/exchange-full-scope-http.py --auth-url
# → user authorizes, pastes redirect URL back
python3 ~/.hermes/skills/productivity/google-workspace/templates/exchange-full-scope-http.py 'http://localhost/?code=4/0A...'
```

### Flow-Based Exchange (Fallback — Needs Monkey-Patch)

If you must use `google_auth_oauthlib.Flow` (e.g., interactive terminal mode), you need the oauthlib monkey-patch. See `templates/exchange-full-scope-token.py` for the working implementation.