# Config YAML Corruption — Cron Jobs Fail with "No models provided"

## Symptom

Cron jobs fail with:
```
RuntimeError: Error code: 400 - {'error': {'message': 'No models provided', 'code': 400}, 'user_id': 'user_3D82vnR5tGyGjowrYK2pMggPWAh'}
```

The errors.log shows:
```
WARNING cron.scheduler: Job '<id>': failed to load config.yaml, using defaults: while parsing a block mapping
```

Followed by OpenRouter API calls with `model= <empty>`.

## Root Cause

The `~/.hermes/config.yaml` has invalid YAML — typically in the `telegram.channel_prompts` section where multi-line string values are formatted with **actual newlines inside single-quoted strings**.

**Invalid YAML:**
```yaml
  channel_prompts:
    '-1003773708968': 'You are KIZUNA — your company's HR Manager.
      This continuation line with actual newlines is INVALID inside single quotes.'
```

In YAML, single-quoted strings cannot span multiple lines with actual line breaks. The `\n` escape inside a single-quoted string is literal backslash-n (two characters), not a newline.

## Why Cron Jobs Break but the Gateway Works

- **Gateway** reads config.yaml once at startup and caches it in memory. If it starts successfully, it keeps working regardless of later corruption.
- **Cron scheduler** re-reads config.yaml fresh each time it spawns a child job process. If the file has broken YAML, the job gets "safe defaults" — which use `fallback_model` (typically OpenRouter) with an empty model string, hence the 400 "No models provided".

## Fix

Convert multi-line string values to YAML **literal block scalars** (`|`) or **folded block scalars** (`>`):

```yaml
  channel_prompts:
    '-1003773708968': |
      You are KIZUNA — your company's HR Manager.
      This continuation uses actual newlines which ARE valid in a | block.
      The text is preserved verbatim including newlines.
```

Or use double-quoted strings where `\n` is a proper escape:

```yaml
    '-1003773708968': "You are KIZUNA — your company's HR Manager.\nContinuation with \\n."
```

### Quick Validation

```bash
python3 -c "import yaml; yaml.safe_load(open('~/.hermes/config.yaml')); print('OK')"
```

If this fails, find the broken section with a YAML linter or by bisecting.

### After Fix

1. Run the failing cron job manually: `hermes cron run <job_id>`
2. Check `last_status` shows `ok` within the next tick
