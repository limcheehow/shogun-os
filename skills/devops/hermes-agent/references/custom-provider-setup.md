# Custom Provider Setup — DashScope (Alibaba) Anthropic Endpoint

Full walkthrough from this session: configuring DeepSeek v4 pro through Alibaba DashScope's Anthropic-compatible endpoint.

## Prerequisites

- Hermes Agent installed
- DashScope API key (`sk-...`)
- Model available on DashScope (e.g. `deepseek-v4-pro`)

## Setup Steps

### 1. Create the custom provider in `~/.hermes/config.yaml`

The `custom_providers` block **must** be a YAML list (items with `- name:` prefix). Dict format causes `Unknown provider` error.

```yaml
custom_providers:
  - name: dashscope-anthropic
    base_url: https://dashscope-intl.aliyuncs.com/apps/anthropic
    api_key: sk-6ea5b78644a940bfa37f266cea896499
    provider_type: anthropic
```

**Why `provider_type: anthropic`**: DashScope exposes an Anthropic-compatible wire protocol, not OpenAI-compatible. The `provider_type` tells Hermes which message format to use on the wire.

### 2. Switch to the custom provider

```bash
hermes config set model.provider custom:dashscope-anthropic
hermes config set model.default deepseek-v4-pro
```

### 3. Verify

```bash
hermes config                # check model section
hermes chat -q "Hello, are you working?"   # test actual response
```

## What NOT to do

❌ Set `model.provider: anthropic` with `model.api_key` — Hermes looks for `ANTHROPIC_API_KEY` env var, ignores config key.

❌ Set `model.base_url` without a custom provider — base_url only takes effect when provider type is openai/anthropic and the provider is configured as a custom provider.

❌ Use YAML dict format for `custom_providers`:
```yaml
# WRONG — Hermes rejects this
custom_providers:
  dashscope-anthropic:
    base_url: ...
```

✅ Always use list format:
```yaml
# RIGHT
custom_providers:
  - name: dashscope-anthropic
    base_url: ...
```

## All Profiles Inherit from Main

When `model.provider` is set on the main model, these inherit it automatically:
- `auxiliary.*` (vision, compression, session_search, etc.) — all use `provider: auto`
- `delegation` sub-agents — `provider: ''`
- `memory` — `provider: ''`
- All cron jobs with `model: null, provider: null`

Exception: `x_search` is hardcoded to `model: grok-4.20-reasoning` (xAI), separate API.

## DashScope OpenAI-Compatible Endpoint (for Auxiliary Tasks)

DashScope also exposes an OpenAI-compatible endpoint at `/compatible-mode/v1`. This is needed when a specific auxiliary function (like `title_generation`) needs a provider that speaks OpenAI protocol — the Anthropic-only provider will 404 on those routes.

### Add the second provider

```yaml
custom_providers:
  - name: dashscope-anthropic
    base_url: https://dashscope-intl.aliyuncs.com/apps/anthropic
    api_key: sk-6ea5b78644a940bfa37f266cea896499
    provider_type: anthropic
  - name: dashscope-openai
    base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    api_key: sk-6ea5b78644a940bfa37f266cea896499
    provider_type: openai
```

### Point auxiliary functions at the OpenAI provider

When a feature like title generation fails with 404 on `provider: auto` (which resolves to the Anthropic endpoint and hits the wrong URL path), override it explicitly:

```bash
hermes config set auxiliary.title_generation.provider custom:dashscope-openai
hermes config set auxiliary.title_generation.model deepseek-v4-flash
```

### Test the endpoint directly

```bash
curl -s --max-time 15 https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-6ea5b78644a940bfa37f266cea896499" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}'
```

## Troubleshooting

**`Unknown provider 'custom:dashscope-anthropic'`**: The `custom_providers` block is in dict format. Change to list format.

**`No Anthropic credentials found`**: `model.provider` is set to `anthropic` (native) instead of `custom:dashscope-anthropic`. The native provider looks for `ANTHROPIC_API_KEY` env var, not config's `api_key`.

**Response takes 50+ seconds**: First request to a new model on DashScope may be slow (cold start). Subsequent requests are faster.

**Auxiliary feature (title_generation, vision) fails with 404**: `provider: auto` resolved to a custom provider whose base URL doesn't support the endpoint path being called. Override that specific auxiliary section's provider explicitly (e.g., `custom:dashscope-openai` for OpenAI-compatible features).

**API key silently truncated when using grep/terminal to read config**: Tools like `grep -A 2` may truncate long values with `...` in the output. When you need the full API key for a config patch, read it from the skill reference file or the raw config file with `read_file` (not `grep`). Patching a truncated key into config breaks all auth.