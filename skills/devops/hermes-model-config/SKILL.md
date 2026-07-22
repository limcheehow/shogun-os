---
name: hermes-model-config
description: Configure, audit, and troubleshoot Hermes Agent model providers — primary, custom, fallback, and cron overrides.
category: devops
tags: [hermes, model, provider, fallback, custom-providers, configuration, audit]
---

# Hermes Model Configuration

Load this skill whenever the user asks about model configuration, provider setup, fallback providers, or model-related issues across Hermes profiles and cron jobs.

## Model Config Structure

Hermes supports a three-tier model resolution:

```
Primary → Custom Provider (optional) → Fallback Chain (optional)
```

### Primary Model (`~/.hermes/config.yaml`)

```yaml
model:
  default: deepseek-v4-flash
  provider: custom
  base_url: https://...dashscope.../apps/anthropic
  api_mode: anthropic_messages
  api_key: sk-xxx
```

- `provider: custom` — means use `base_url` + `api_key` + `api_mode` from the model block directly (no named provider reference)
- `provider: custom:dashscope-openai` — means look up a named custom_providers entry with name `dashscope-openai`
- `provider: openrouter` / `provider: anthropic` — use a built-in provider (reads API key from env var)

### Custom Providers (Named)

For secondary endpoints (e.g., OpenAI-compatible for auxiliary tasks):

```yaml
custom_providers:
  - name: dashscope-openai
    base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    api_key: sk-xxx
    provider_type: openai
```

**Critical rules:**
1. **MUST be a YAML list** (starting with `- name:`), NOT a dict
2. **MUST be at top level**, NOT nested under `model:`
3. `provider_type` determines wire protocol: `anthropic` or `openai`
4. Reference from config as `provider: custom:<name>` (e.g. `custom:dashscope-openai`)

**Wrong** (silently ignored):
```yaml
# Dict format — Hermes returns empty []
custom_providers:
  dashscope-openai:
    base_url: ...

# JSON string — Hermes returns empty []
custom_providers: '[{"name": "dashscope-openai", ...}]'

# Nested under model: — wrong scope
model:
  custom_providers: '[...]'
```

### Fallback Providers

When the primary provider fails (rate-limit, auth, timeout), Hermes tries the fallback chain:

```yaml
fallback_providers:
  - provider: openrouter
    model: deepseek/deepseek-v4-flash
```

**How it works:**
- Applies to: gateway sessions, cron jobs (agent-mode), CLI chatting
- Triggers on: `AuthError`, connection failures, timeouts that the gateway retry logic exhausts
- Cron jobs specifically: when `resolve_runtime_provider()` fails with auth error, the scheduler iterates `fallback_providers` entries
- The `get_fallback_chain()` helper merges `fallback_providers` (new) + `fallback_model` (legacy), deduplicating by provider+model+base_url

## Profile Compliance Checklist

Every Hermes profile (`~/.hermes/profiles/<name>/config.yaml`) should have:

1. **Primary model:**
   - `model.provider: custom` with inline DashScope base_url + api_key + api_mode
   - OR `model.provider: custom:<name>` paired with a top-level `custom_providers` list entry

2. **Custom providers:**
   - `custom_providers` as a YAML list at top level (if needed for auxiliary `custom:dashscope-openai` references)
   - Profiles that reference `provider: custom:dashscope-openai` in `auxiliary.title_generation` MUST define it

3. **Fallback chain:**
   - `fallback_providers` as a YAML list (array of dicts with `provider` + `model`)

4. **No stale keys:**
   - No `custom_providers` as a JSON string anywhere
   - No `custom_providers` nested under `model:` or `model_catalog:`
   - No duplicate top-level `custom_providers` or `fallback_providers` (last key wins in YAML)

## Cron Job Model Resolution

Cron jobs resolve their provider in this order:

1. **Job-specific override** — if the cron has `model` + `provider` set in its job entry, those are pinned
2. **Profile default** — inherits from the active profile's `model.default` / `model.provider`
3. **Fallback chain** — if the primary auth fails, tries `fallback_providers` from the config

**Updating cron models:**
```bash
# Update a cron job to use DashScope
hermes cron update <job_id> --model deepseek-v4-flash --provider custom

# Or use the cronjob tool:
cronjob(action='update', job_id='...', model={'model': 'deepseek-v4-flash', 'provider': 'custom'})
```

## Verification Commands

### Model config health check
```bash
python3 << 'PYEOF'
import yaml
with open('/home//.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)

m = cfg.get('model', {})
cp = cfg.get('custom_providers')
fb = cfg.get('fallback_providers')

print(f"Primary: {m.get('default')} via {m.get('provider')}")
if isinstance(cp, list):
    for c in cp:
        print(f"Custom:  {c.get('name')} ({c.get('provider_type')})")
if isinstance(fb, list):
    for f in fb:
        print(f"Fallback: {f.get('model')} via {f.get('provider')}")
PYEOF
```

### Parse validation
```bash
hermes config 2>&1 | head -5
# Expected: no "Failed to parse" or "Falling back to default config" warnings
```

### Profile-wide API key health check

```bash
python3 ~/.hermes/skills/devops/hermes-model-config/scripts/check-api-keys.py
```

Scans all profiles (default + every named profile under `profiles/`) for truncated `api_key` values containing literal `...`. Silent exit 0 when all healthy.

### Full profile sweep
```bash
for p in ~/.hermes/profiles/*/config.yaml; do
  name=$(basename "$(dirname "$p")")
  python3 -c "
import yaml
with open('$p') as f:
    cfg = yaml.safe_load(f)
m = cfg.get('model', {})
cp = cfg.get('custom_providers')
fb = cfg.get('fallback_providers')
issues=[]
if m.get('provider') not in ('custom', 'custom:dashscope-openai'):
    issues.append(f'provider={m.get(\"provider\")!r}')
if not isinstance(cp, list) or len(cp)==0:
    issues.append('missing custom_providers list')
if not isinstance(fb, list) or len(fb)==0:
    issues.append('missing fallback_providers')
print(f\"{'✅' if not issues else '⚠️'} $name: \" + ('  '.join(issues) if issues else 'ok'))
"
done
```

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `custom_providers` as JSON string (from `hermes config set`) | `type(custom_providers) == str`, Hermes returns `[]` | Delete the string, write proper YAML list |
| `custom_providers` nested under `model:` | Shows in `model.custom_providers` instead of top-level | Move to top level |
| `custom_providers` as YAML dict | `Unknown provider` at runtime | Change to list format (`- name:`) |
| Duplicate top-level keys | Last one wins (YAML semantics), may override the good one | Remove stale duplicates |
| Cron jobs with stale `model.provider: openrouter` | Continue using old provider despite profile change | Update cron job model override via `hermes cron update` |
| `fallback_providers: []` (empty list) | No fallback on auth failure | Replace with list containing one or more entries |
| Profiles missing `custom_providers` but referencing `custom:dashscope-openai` in auxiliary | Title gen / compression silently fails | Add the custom provider definition |\n| `model.provider: custom` but no `base_url` / `api_key` in model block | Provider resolution fails | Ensure `base_url` and `api_key` are set under `model:` |
| **`auxiliary.title_generation.provider: auto` with inline `model.provider: custom`** | **Main chat works, but title generation fails with `HTTP 401: Incorrect API key provided` from DashScope. The request reaches the correct endpoint but the API key isn't carried through the auxiliary code path.** | **Explicitly set the auxiliary provider to a named custom provider: `hermes config set auxiliary.title_generation.provider custom:dashscope-openai` and `hermes config set auxiliary.title_generation.model deepseek-v4-flash`.** |
| **`api_key` value contains literal `...` (truncation artifact)** | **HTTP 401 at startup even though the token itself is valid — the truncated key `sk-c0b...ca38` (13 chars) looks real but isn't** | **Verify with `python3 -c \"import yaml; cfg=yaml.safe_load(open('/path/to/config.yaml')); k=cfg['model']['api_key']; print(len(k), '...' in k)\"` — expected: `35 False`. If `...` is in the value ITSELF (not just display truncation), restore the full key. Confusingly, `read_file` also displays 35-char keys as `sk-c0b...ca38`, so use `len()` to distinguish display truncation (length=35, no `...` in actual string) from corruption (length=13, literal `...`).** |\n| **Provider rate limit (HTTP 429) causing gateway crash loop** | **Gateway crash-loops: watchdog runs but gateway dies immediately on first API call at startup. Logs show `HTTP 429: Allocated quota exceeded`.** | **Switch provider manually (`hermes config set model.provider openrouter`), force-kill watchdog, restart clean. The fallback chain engages at runtime, not during init, so the rate limit blocks startup before fallback logic runs.** |
| **DashScope endpoint mismatch (Anthropic vs OpenAI)** | **DashScope returns HTTP 404 on every call (`NotFoundError`). All traffic silently falls through to fallback provider. No user-visible error — just high OpenRouter billing.** | **DashScope has two endpoints with different model name formats. The MaaS Anthropic endpoint (`ws-<workspace>.maas.aliyuncs.com/apps/anthropic`) may 404 on model `deepseek/deepseek-v4-flash` while the OpenAI-compatible endpoint (`dashscope-intl.aliyuncs.com/compatible-mode/v1`) works with `deepseek-v4-flash` (no `/deepseek/` prefix). Test both endpoints directly via curl before assuming a provider is broken.** |
| **Credential pool interference (stale `auth.json` entries)** | **HTTP 401 from DashScope at runtime even though `model.api_key` is correct and direct curl against the endpoint succeeds. Agent.log shows `Streaming failed before delivery: Error code: 401` immediately after `OpenAI client created`.** | **Two things are typically wrong: (1) the `custom_providers` list entry for a named provider (like `dashscope-openai`) has a truncated API key with literal `...` in the value, and (2) `~/.hermes/auth.json` has stale `credential_pool` entries for that provider with `key_len=0` that intercept requests. The agent.log signal is: `Credential pool provider mismatch: pool=custom:dashscope-openai, agent=custom — skipping pool mutation`. Fix: clean the stale pool entries from `auth.json` (delete `credential_pool.<name>`), then copy the correct 35-char API key from `model.api_key` into the broken `custom_providers` entry.** |

## Cron Fallback for Auth Failures

The cron scheduler (in `cron/scheduler.py`) handles fallback at job runtime:

1. If primary provider auth fails → tries `fallback_providers` entries in order
2. Each entry must have at least `provider` and `model` keys
3. First successful resolution breaks the loop
4. If all fail → raises `RuntimeError` with original auth error

## Runtime Provider Audit: Detecting Silent Fallback

When a user reports unexpectedly high usage on a particular provider (e.g., OpenRouter billing), **the config alone is not enough** to know which provider is actually being used. A primary provider that silently fails — returning HTTP 404, auth errors, repeated timeouts — causes the **fallback chain to fire on every single request**, making the fallback provider appear as the dominant (or only) provider in use.

### Two Kinds of Fallback Usage

| Type | What It Means | How to Detect |
|------|--------------|---------------|
| **Front-door** (pinned primary) | Provider set as `model.provider` or a cron job override | Check `model.provider` in config.yaml or cron job model overrides |
| **Back-door** (silent fallback) | Primary fails on every call, so fallback handles all traffic | Check `fallback_providers` in configs + agent.log for actual call failures |

### Audit Procedure (5 Steps)

**Step 1 — Check config fallback chains**

The `fallback_providers` key in config.yaml defines which provider catches errors. Check the main config AND all profiles:

```bash
grep -A2 "fallback_providers" ~/.hermes/config.yaml
```

**Step 2 — Count actual provider failures vs successes in agent.log**

This is the definitive step — it shows what's really happening at runtime, not what the config says:

```bash
# Count failures on the primary provider
echo "Primary failures:"
grep -c "NotFoundError.*provider=custom" ~/.hermes/logs/agent.log

# Count successful calls on the fallback provider
echo "Fallback successes (e.g. OpenRouter):"
grep -c "provider=openrouter" ~/.hermes/logs/agent.log
```

Look for lines with `error_type=NotFoundError`, `HTTP 404`, `HTTP 429`, or `AuthError` on the primary provider, followed immediately by a successful call on the fallback.

**Step 3 — Session-level breakdown of failures**

Find which sessions are triggering the fallback, grouped by frequency:

```bash
grep "NotFoundError.*provider=custom.*HTTP 404" ~/.hermes/logs/agent.log \
  | sed 's/.*\[//;s/\].*//' \
  | sort | uniq -c | sort -rn
```

This reveals whether the failure affects all sessions (systemic — 404 on wrong model name or endpoint) or specific sessions only (intermittent / per-session issue).

**Step 4 — Check cron job model overrides**

Cron jobs may have their own pinned provider that differs from the profile:

```bash
python3 -c "
import json
data = json.load(open('/home//.hermes/cron/jobs.json'))
for j in data.get('jobs',[]):
    prov = j.get('provider')
    if prov and 'openrouter' in prov:
        print(f'⚠️  {j.get(\"name\",\"?\")} — pinned to {prov}/{j.get(\"model\")}')
"
```

Any match here means that cron job bypasses the profile's primary entirely. Update with `hermes cron update <id> --provider custom` to switch back.

**Step 5 — Confirm single vs multiple gateways**

If all profiles share a single gateway process, ALL fallback chains are in play simultaneously — there is no profile-isolated fallback:

```bash
ps aux | grep "hermes gateway run" | grep -v grep
# One process = single gateway serving all profiles through channel prompts
# Multiple processes = each gateway has its own independent fallback chain
```

### The Auxiliary Provider 401 Trap

When the main model uses `model.provider: custom` (inline config — `base_url` + `api_key` directly under `model:`), **auxiliary sections with `provider: auto` — title generation, compression, triage specifier — may fail with HTTP 401** even though the main chat works fine.

**Root cause:** The `auto` resolution reaches the correct DashScope endpoint, but the auxiliary code path doesn't properly carry the inline `api_key`. The request arrives at DashScope with a missing/empty API key, producing:

```
⚠ Auxiliary title generation failed: HTTP 401: Incorrect API key provided.
```

This is distinct from the 404 endpoint-mismatch case (wrong path like `/apps/anthropic` vs `/compatible-mode/v1`). Here, the URL is correct — the credential is the problem.

**Fix:** Explicitly pin each affected auxiliary section to a named custom provider that has its own `api_key`:

```bash
hermes config set auxiliary.title_generation.provider custom:dashscope-openai
hermes config set auxiliary.title_generation.model deepseek-v4-flash

# Also check these often-overlooked auxiliary sections:
hermes config set auxiliary.compression.provider custom:dashscope-openai
hermes config set auxiliary.triage_specifier.provider custom:dashscope-openai
hermes config set auxiliary.kanban_decomposer.provider custom:dashscope-openai
```

The named `custom:dashscope-openai` provider must exist in the top-level `custom_providers` list with its own `api_key`, `base_url`, and `provider_type: openai`. If it doesn't, create it first:

```yaml
custom_providers:
  - name: dashscope-openai
    base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    api_key: sk-...full-key...
    provider_type: openai
```

**Verification** — after setting, generate a title for any session (or trigger a session switch in the TUI). The 401 should disappear and a valid title should appear.

**Affected auxiliary sections:** `title_generation`, `compression`, `triage_specifier`, `kanban_decomposer`, `summary`. All have `provider: auto` by default and all resolve through the same code path.

### The Fallback Trap

When the primary provider returns a **non-ephemeral error** (HTTP 404 — model not found, wrong endpoint, invalid model name; or HTTP 401 — expired token), the fallback fires on **every single API call** forever. This produces:

- **100% fallback-provider usage** even though the config shows a different primary
- **High fallback-provider billing** that seems disconnected from config changes
- **No visible error in gateway logs** — the fallback is working as designed, logging only a warning per call

The only way to detect this situation is the agent.log audit (Steps 2–3), because the gateway gracefully handles the failure and the user never sees an error message.

### Credential Pool Interference (Empty Keys Override Inline Config)

When `model.provider: custom` (inline) is set with a correct `api_key`, but a named `custom_providers` entry like `dashscope-openai` also exists, the credential pool at `~/.hermes/auth.json` can develop stale entries with **empty API keys** that intercept requests before the inline key is reached.

**Diagnostic signals:**
- Raw curl test against the DashScope endpoint succeeds (HTTP 200 with valid response)
- Hermes agent.log shows `Streaming failed before delivery: Error code: 401` every call
- Agent.log also shows: `Credential pool provider mismatch: pool=custom:dashscope-openai, agent=custom — skipping pool mutation to avoid cross-provider contamination`

**Root cause chain:**
1. The `custom_providers` list entry for `dashscope-openai` has a truncated key (literal `...`, 13 chars instead of 35)
2. The credential pool (`auth.json`) creates entries under `credential_pool.custom:dashscope-openai` 
3. Those entries have empty `api_key` values (`key_len=0`)
4. The pool is consulted at runtime and returns an empty key → 401 from DashScope
5. The pool skips mutation when `agent=custom` doesn't match `pool=custom:dashscope-openai` — so the pool never gets cleaned up

**Fix:**
```bash
# 1. Inspect credential pool
python3 -c "
import json
with open('/home//.hermes/auth.json') as f:
    data = json.load(f)
pool = data.get('credential_pool', {})
for prov, entries in pool.items():
    if 'dashscope' in prov.lower() or 'custom' in prov.lower():
        for e in entries:
            print(f'{prov}/{e.get(\"label\")}: key_len={len(e.get(\"api_key\",\"\"))}')
"

# 2. Remove stale entries
python3 -c "
import json
with open('/home//.hermes/auth.json') as f:
    data = json.load(f)
pool = data.get('credential_pool', {})
for key in list(pool.keys()):
    if 'dashscope' in key.lower() or (key.startswith('custom:') and key != 'custom:'):
        del pool[key]
data['credential_pool'] = pool
with open('/home//.hermes/auth.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Cleaned stale credential pool entries')
"

# 3. Fix truncated key in custom_providers list
python3 -c "
import yaml
with open('/home//.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
correct_key = cfg['model']['api_key']  # the inline key (should be 35 chars)
for c in cfg.get('custom_providers', []):
    if len(c.get('api_key','')) < 20:  # truncated
        print(f'Fixing {c[\"name\"]}: {len(c[\"api_key\"])} chars → {len(correct_key)} chars')
        c['api_key'] = correct_key
with open('/home//.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
print('Config fixed — custom_providers keys restored')
"
```

**Post-fix verification:**
```bash
# Check pool is clean
python3 -c "import json; d=json.load(open('/home//.hermes/auth.json')); print(d.get('credential_pool',{}).keys())"

# Check custom_providers keys are full length
python3 -c "
import yaml
with open('/home//.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
for c in cfg.get('custom_providers', []):
    print(f'{c[\"name\"]}: key_len={len(c.get(\"api_key\",\"\"))}')
"
# All should show key_len=35
```

### Scenario Example

The user asks "Why is OpenRouter billing so high when we switched to DashScope?" You investigate:

1. Config shows `provider: custom` (DashScope) with `fallback_providers: [{provider: openrouter, model: deepseek/deepseek-v4-flash}]`
2. Agent.log shows **145 DashScope 404 failures** and **3,834 OpenRouter successes** — every call falls through
3. Session breakdown shows EVERY session affected (systemic), not just one
4. Cron jobs show no pinned OpenRouter overrides — they inherit the same broken chain
5. Only 1 gateway process — all profiles hit the same fallback

Root cause: the DashScope MaaS endpoint returns 404 for the model name. Fix: correct the model name or the endpoint URL.

See `references/runtime-provider-audit.md` for a full walkthrough with real session output.
See `references/credential-pool-interference.md` for the complete diagnostic trace of stale pool entries overriding inline config keys.