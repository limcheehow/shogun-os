# Google OAuth Reauthorization — Telegram / Headless Flow

When the token is revoked (`RefreshError: unauthorized_client`) and the user is on Telegram (no browser, no localhost):

## Prerequisites

- `client_secret_gmail.json` (or equivalent) at `~/.hermes/`
- The setup script at `~/.hermes/skills/productivity/google-workspace/scripts/setup.py`

## Step-by-Step

### 1. Register the client secret

```bash
python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py \
  --client-secret ~/.hermes/client_secret_gmail.json
# Expected: OK: Client secret saved to ~/.hermes/google_client_secret.json
```

### 2. Generate the auth URL and send to user

```bash
python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --auth-url
# Output: https://accounts.google.com/o/oauth2/auth?response_type=code&...
```

Send this URL to the user with instructions:
1. Open the URL in your browser
2. Sign in with the Google account
3. Approve the permissions
4. The browser will fail on `http://localhost` — that's expected
5. Copy the ENTIRE URL from the address bar and paste it back

### 3. Exchange the code

The user pastes back something like:
```
http://localhost/?code=4/0AdkVLP...&scope=...
```

Extract the `code` parameter and exchange:

```bash
python3 ~/.hermes/skills/productivity/google-workspace/scripts/setup.py \
  --auth-code '4/0AdkVLPzfs7Yt27hHI76NNZtv6...'
# Expected: OK: Authenticated. Token saved to ~/.hermes/google_token.json
```

### 4. Verify

```bash
python3 ~/.hermes/skills/productivity/google-workspace/scripts/google_api.py \
  calendar list --max 1
# Should return JSON with calendar events — not a RefreshError
```

## Pitfalls

- **Don't use `--services` or `--format json` flags** — the setup script (as of June 2026) doesn't support them despite the skill docs mentioning them. Just `--auth-url` with no extra flags.
- **The auth URL expires quickly** — have the user open it immediately. If it expires, re-run `--auth-url` for a fresh one.
- **Mismatched client_secret** — If the token's `client_id` doesn't match the `client_secret.json`, refresh will fail with `unauthorized_client`. Use `python3 -c "import json; ..."` to check.
- **`redirect_uri` must be `http://localhost`** — the Desktop OAuth client type expects this. The redirect will fail (no server listening), but the code in the URL bar is what we need.