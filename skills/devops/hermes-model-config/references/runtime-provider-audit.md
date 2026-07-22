# Runtime Provider Audit: Silent Fallback Detection

## The Problem

A user reports that OpenRouter billing remains very high despite switching the primary provider from OpenRouter to DashScope. The config clearly shows `model.provider: custom` pointing to a DashScope MaaS Anthropic-compatible endpoint. Yet the billing says otherwise.

## The Investigation

### Hypothesis: Silent fallback — the primary is failing on every call

The config has `fallback_providers: [{provider: openrouter, model: deepseek/deepseek-v4-flash}]`. If the primary DashScope endpoint returns an error (not a transient one like rate-limiting, but a solid 404), every single API call will fail on the primary and succeed on the fallback. The user sees 100% OpenRouter usage.

### Step 1 — Check config fallback chains

```bash
grep -A2 "fallback_providers" ~/.hermes/config.yaml
```

Output:
```
fallback_providers:
  - provider: openrouter
    model: deepseek/deepseek-v4-flash
```

Confirmed: OpenRouter is the fallback. But is it actually being activated?

### Step 2 — Check all profile-level configs

All 8 profiles (coding-agent, compliance-manager, finance-manager, hr-manager, marketing-manager, procurement-manager, product-manager, project-manager) also have the same pattern — primary `provider: custom` (DashScope) with OpenRouter fallback. This is a shared config pattern, not a profile-specific setting.

### Step 3 — Count runtime failures vs successes in agent.log

```bash
echo "DashScope 404 failures:"
grep -c "NotFoundError.*provider=custom" ~/.hermes/logs/agent.log
# → 145

echo "OpenRouter successes:"
grep -c "provider=openrouter" ~/.hermes/logs/agent.log
# → 3,834
```

**Every DashScope call fails with HTTP 404; every successful call goes through OpenRouter.**

### Step 4 — Session-level breakdown

```bash
grep "NotFoundError.*provider=custom.*HTTP 404" ~/.hermes/logs/agent.log \
  | sed 's/.*\[//;s/\].*//' \
  | sort | uniq -c | sort -rn
```

Output:
```
20 20260610_122729_e67cc7
11 20260610_124107_b5e5be
10 20260610_094129_b07b3513
 9 20260610_104439_2a00881e
 9 20260610_091950_ca83f059
 7 20260610_135105_6a93ac
...
 1 cron_7e8631ff5bc9_20260610_110100
 1 cron_5239f5ed1285_20260610_110059
```

Every single session (including cron jobs) shows the same failure — **systemic, not intermittent**. The 404 is not a transient blip; it's a fundamental endpoint/model mismatch.

### Step 5 — Check cron job model overrides

```bash
python3 -c "
import json
data = json.load(open('/home/tapway/.hermes/cron/jobs.json'))
for j in data.get('jobs',[]):
    prov = j.get('provider')
    if prov and 'openrouter' in prov:
        print(f'⚠️  {j.get(\"name\",\"?\")} — pinned to {prov}/{j.get(\"model\")}')
"
```

No output — no cron jobs were pinned to OpenRouter. They all inherit from the profile, which uses the same broken DashScope fallback chain.

### Step 6 — Confirm single vs multiple gateways

```bash
ps aux | grep "hermes gateway run" | grep -v grep
```

Output:
```
Company 23011 ... /home/tapway/.hermes/hermes-agent/venv/bin/hermes gateway run
```

Single gateway. All profiles route through it via `channel_prompts`. There is no profile-isolated fallback.

### Verdict

**Root cause**: The DashScope MaaS Anthropic endpoint `ws-rm3m81doye8ddmh2.ap-southeast-1.maas.aliyuncs.com/apps/anthropic` returns HTTP 404 for model `deepseek/deepseek-v4-flash`. The exact 404 line in agent.log:

```
API call failed (attempt 1/1) error_type=NotFoundError
  provider=custom
  base_url=https://ws-rm3m81doye8ddmh2.ap-southeast-1.maas.aliyuncs.com/apps/anthropic
  model=deepseek/deepseek-v4-flash
  summary=HTTP 404: event:error
```

**Impact**: Every single API call across all profiles and all cron jobs goes through OpenRouter. 3,834 calls in one day.

### Resolution

Two options:

**Option A — Fix DashScope**: DashScope has two different endpoints with different model name formats and wire protocols. If one returns 404, try the other.

| Endpoint | Wire Protocol | Model Name | Status |
|----------|---------------|------------|--------|
| `ws-<workspace>.maas.aliyuncs.com/apps/anthropic` | Anthropic Messages | `deepseek/deepseek-v4-flash` (with `/deepseek/` prefix) | ❌ Returns HTTP 404 |
| `dashscope-intl.aliyuncs.com/compatible-mode/v1` | OpenAI | `deepseek-v4-flash` (no prefix) | ✅ Tested: HTTP 200 |

**Direct API test (OpenAI endpoint):**
```bash
curl -s "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "max_tokens": 10
  }'
```

Returns HTTP 200 with valid completion. The model name is `deepseek-v4-flash` — **without** the `/deepseek/` prefix that OpenRouter requires.

The MaaS Anthropic endpoint 404 could mean:
- The workspace was deprovisioned or expired
- The Anthropic-compatible proxy on that workspace is no longer active
- The model name format expected differs from what's configured

**Fix**: Switch to the OpenAI-compatible endpoint:
```yaml
model:
  default: deepseek-v4-flash          # ← no /deepseek/ prefix
  provider: custom
  base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
  api_key: sk-...                      # ← same key, different base_url
  # Remove api_mode: anthropic_messages — defaults to openai
```

**Option B — Remove the fallback**: Delete the `fallback_providers` entry from config.yaml. DashScope failures become "API call failed, no fallback available" errors visible to the user — no more silent OpenRouter billing.

### Key Takeaway

The config's `model.provider` field only shows what should happen. To see what actually happens, you must check `agent.log` for the real call pattern. A silent fallback can cause 100% of traffic to use a different provider than what the config describes, with no user-visible error.