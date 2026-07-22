---
name: hermes-auxiliary-setup
description: Set up and troubleshoot Hermes auxiliary services — vision, Google OAuth, compression, and other secondary backends that need separate provider configuration.
category: devops
tags: [hermes, vision, google, oauth, troubleshooting, config, auxiliary]
---

# Hermes Auxiliary Services — Setup & Troubleshooting

Load this skill when diagnosing why a Hermes feature (vision, compression, Google integration, etc.) isn't working even though `hermes tools list` shows it as enabled, or when setting up backend providers for auxiliary services.

## Quick Diagnostic: Why Isn't My Tool Available?

The #1 reason a toolset shows ✓ enabled in `hermes tools list` but the tool isn't in your session: **the backend provider can't resolve a client.**

Hermes silently strips tools from a toolset when the underlying provider client is `None`. This happens for:

- **vision / vision_analyze** — vision backend can't create a client
- **web / web_search** — search backend not configured
- **moa** — no API key configured

### Vision — The Diagnostic Command

```bash
python3 -c "
import sys
sys.path.insert(0, '$HOME/.hermes/hermes-agent')
from agent.auxiliary_client import resolve_vision_provider_client
provider, client, model = resolve_vision_provider_client()
print(f'provider={provider}')
print(f'client={client}')
print(f'model={model}')
"
```

If `client=None` or the output shows `unknown provider`, the vision toolset is dead and `vision_analyze` will never appear in your tools — no matter how many times you add `vision` to `toolsets` or restart the gateway.

## Vision Setup

### Text-Only Models Need a Separate Vision Provider

DeepSeek V4, GPT-OSS-120B, and similar text-only models **cannot process images**. Hermes auto-detects this and skips them. You MUST configure a separate vision-capable model.

### Recommended: Use OpenRouter

```bash
hermes config set auxiliary.vision.provider openrouter
hermes config set auxiliary.vision.model google/gemini-2.5-flash
```

This works immediately because OpenRouter is already configured as your main provider. No new API keys needed.

### Alternative: Custom Provider (DashScope, Groq, etc.)

See `references/custom-provider-dashscope.md` for the full DashScope (qwen3-vl-flash) setup. Key pitfall: `custom_providers` must be a proper YAML list.

### Image Input Mode

```yaml
agent:
  image_input_mode: auto  # auto | native | text
```

- **auto** — uses native if model supports vision, falls back to text analysis
- **native** — attaches images as content parts (requires multimodal model)
- **text** — runs vision_analyze on each image, sends text description to main model

## The `hermes config set` String Trap

**`hermes config set` stores JSON-like values as YAML STRINGS, not YAML lists/dicts.** This silently breaks list-valued config keys.

### What Happens

```bash
hermes config set toolsets '["hermes-cli", "vision"]'
```

Writes to config.yaml:
```yaml
toolsets: '["hermes-cli", "vision"]'    # ← YAML string, NOT a list
```

Same for `custom_providers`:
```yaml
custom_providers: '[{"name": "dashscope-openai", ...}]'   # ← string, NOT list
```

### Why It Breaks

The YAML parser sees a single string value, not a list. `custom_providers` expects a list — runtime code looks for list items and finds none → `unknown provider`.

### How to Detect

```bash
grep "toolsets\|custom_providers\|platform_toolsets" ~/.hermes/config.yaml
```

If the value starts with `'[` (single-quoted bracket), it's a string trap. It should look like:
```yaml
toolsets:
- hermes-cli
- vision
```

### Fix: Edit config.yaml directly

```bash
# View the broken entry
grep -n "custom_providers\|toolsets" ~/.hermes/config.yaml

# Fix by replacing the string with a proper YAML list
hermes config set toolsets '["hermes-cli", "vision"]'   # this IS the standard way
```

Note: `hermes config set` with `'["..."]'` syntax IS the intended API — Hermes internally parses the JSON string. The trap only bites when the string format is correct JSON but the runtime code reads YAML directly. Always verify with `hermes config 2>&1 | head` after setting list-valued keys.

## Stray `platform_toolsets` Entries

If a platform section has `platform_toolsets` set to a restricted list like `["vision"]`, it OVERRIDES the global toolsets and you lose all other tools (terminal, file, browser, etc.) on that platform.

```bash
# Check for restricted platform toolsets
grep "platform_toolsets:" ~/.hermes/config.yaml

# Clear them (removes the override, inherits global toolsets)
hermes config set telegram.platform_toolsets ''
hermes config set slack.platform_toolsets ''
```

## Google OAuth Token Management

### Token Locations

Hermes looks for OAuth tokens at `~/.hermes/google_token.json`. However, other systems (gbrain, voice-agent) may store tokens elsewhere:

| System | Token Path | Notes |
|--------|-----------|-------|
| Hermes google-workspace | `~/.hermes/google_token.json` | Standard location |
| gbrain | `~/.gbrain/google-tokens.json` | May have correct format but different path |
| Voice agent | varies | Check voice-agent config |

### Token Format Required by google-workspace

```json
{
  "access_token": "ya29...",
  "expires_in": 3599,
  "refresh_token": "1//...",
  "scope": "https://www.googleapis.com/auth/...",
  "token_type": "Bearer",
  "client_id": "......apps.googleusercontent.com",
  "client_secret": "GOCSPX-..."
}
```

**All 7 fields are required.** Missing `client_id` or `client_secret` causes `ValueError: missing fields client_secret, client_id` on refresh.

### Refresh Failure: unauthorized_client

When the token format is correct but refresh fails with `RefreshError: unauthorized_client: Unauthorized`:
- The refresh token was either **revoked** (user removed app access at myaccount.google.com/permissions) or the OAuth client was regenerated/changed
- **Fix**: Re-authorize via the OAuth flow. See `references/google-oauth-reauthorization-telegram.md` for the full headless/Telegram reauthorization flow.
- Quick summary: `setup.py --client-secret <file>` → `setup.py --auth-url` → send URL → user copies redirect → `setup.py --auth-code <code>`

### Bridging gbrain Tokens to Hermes

If gbrain has a working token at `~/.gbrain/google-tokens.json`:
```bash
# Copy to Hermes location
cp ~/.gbrain/google-tokens.json ~/.hermes/google_token.json

# If client_id/secret is missing (older tokens), inject from client_secret file:
python3 -c "
import json
with open('/home/tapway/.hermes/client_secret_gmail.json') as f:
    cs = json.load(f)['installed']
with open('/home/tapway/.gbrain/google-tokens.json') as f:
    tok = json.load(f)
tok.update({k: cs[k] for k in ('client_id','client_secret') if k not in tok})
with open('/home/tapway/.hermes/google_token.json','w') as f:
    json.dump(tok, f)
"
```

## Pitfalls

- **`resolve_vision_provider_client()` returning `(provider, None, None)` means the vision tool is silently stripped** — even though `hermes tools list` shows ✓ vision. Always run the diagnostic command.
- **`hermes config set` string trap**: values like `'["hermes-cli", "vision"]'` become YAML strings. Verify with `grep` after setting list-valued keys.
- **Stray `platform_toolsets` overrides can strip all tools on a platform** — clear them with `hermes config set <platform>.platform_toolsets ''` unless intentionally restricting.
- **Gateway restart alone won't fix a dead vision backend** — if the provider client is None, the toolset stays stripped regardless of restarts. Fix the provider first, then restart.
- **DeepSeek V4 + vision = impossible** — Hermes explicitly skips text-only models for vision in auto mode. You MUST configure a separate vision provider.
- **Google token refresh failure is silent until API call** — the token file looks valid, but `refresh_token` may be revoked. Run `google_api.py calendar list --max 1` to smoke-test.

## Reference Files

- `references/google-oauth-reauthorization-telegram.md` — Full step-by-step OAuth reauthorization flow for headless/Telegram environments.
- `references/google-service-account-dwd-setup.md` — Google Workspace Service Account + Domain-Wide Delegation setup plan.

## Diagnostic Checklist

When a toolset shows ✓ but the tool isn't in your session:

1. Run the provider-specific diagnostic (vision → `resolve_vision_provider_client()`, google → API call)
2. Check `custom_providers` is a proper YAML list, not a string
3. Check `platform_toolsets` isn't overriding with a restricted set
4. Fix the provider, then restart the gateway
5. Smoke-test: for Google, `calendar list --max 1`; for vision, `vision_analyze` on a local image
