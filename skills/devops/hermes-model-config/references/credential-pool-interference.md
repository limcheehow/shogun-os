# Credential Pool Interference Diagnosis

## Symptom

HTTP 401 from DashScope at runtime, but direct curl to the same endpoint with the same inline API key returns HTTP 200.

## Session Narrative

**Setup:** `model.provider: custom` (inline) with `base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, `model: deepseek-v4-pro`. A named `custom_providers` entry `dashscope-openai` also exists (OpenAI-compatible, same endpoint).

**Diagnostic steps that led to the root cause:**

### Step 1 — Verify the endpoint itself works
```bash
python3 -c "
import yaml, requests
with open('/home/tapway/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
api_key = cfg['model']['api_key']
resp = requests.post(
    f'{cfg[\"model\"][\"base_url\"]}/chat/completions',
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
    json={'model': cfg['model']['default'], 'messages': [{'role': 'user', 'content': 'Reply OK'}], 'max_tokens': 10},
    timeout=30
)
print(f'Status: {resp.status_code}')
print(f'Body: {resp.text[:300]}')
"
```
→ Status 200 — the endpoint, model name, and key are all correct.

### Step 2 — Check agent.log for the actual runtime error
```bash
tail -50 ~/.hermes/logs/agent.log | grep -iE "error|fail|401|auth"
```
→ Shows:
```
Streaming failed before delivery: Error code: 401 - {'error': {'message': 'Incorrect API key provided.'}}
Credential pool provider mismatch: pool=custom:dashscope-openai, agent=custom — skipping pool mutation
```

### Step 3 — Inspect credential pool in auth.json
```bash
python3 -c "
import json
with open('/home/tapway/.hermes/auth.json') as f:
    data = json.load(f)
pool = data.get('credential_pool', {})
for prov, entries in pool.items():
    if 'dashscope' in prov.lower():
        for e in entries:
            key = e.get('api_key', '')
            print(f'{prov}/{e[\"label\"]}: key_len={len(key)} key_prefix={key[:10] or \"NONE\"}')
"
```
→ Shows:
```
custom:dashscope-openai/dashscope-openai: key_len=0 key_prefix=NONE
custom:dashscope-openai/model_config: key_len=0 key_prefix=NONE
```

The credential pool has entries for `custom:dashscope-openai` but **both have `key_len=0`** — empty API keys.

### Step 4 — Inspect custom_providers list keys
```bash
python3 -c "
import yaml
with open('/home/tapway/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
for c in cfg.get('custom_providers', []):
    k = c.get('api_key', '')
    print(f'{c[\"name\"]}: key_len={len(k)}')
"
```
→ Shows:
```
dashscope-openai: key_len=13
```

### Step 5 — Compare inline vs custom_providers keys
```bash
python3 -c "
import yaml
with open('/home/tapway/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
inline = cfg['model']['api_key']
cp = [c for c in cfg.get('custom_providers',[]) if c['name']=='dashscope-openai'][0]
print(f'Inline key: {len(inline)} chars')
print(f'Custom Prov key: {len(cp[\"api_key\"])} chars')
print(f'Same? {inline == cp[\"api_key\"]}')
"
```
→ `False` — the inline key is 35 chars, the custom_providers key is 13 chars with literal `...` (a truncation artifact).

## Root Cause

1. The `custom_providers` list entry `dashscope-openai` had a truncated 13-char key (containing literal `...`)
2. The credential pool at `~/.hermes/auth.json` stored entries under `credential_pool.custom:dashscope-openai` with empty keys
3. At runtime, the pool was consulted and returned the empty keys → 401 from DashScope
4. The pool mutation was skipped because `agent=custom` ≠ `pool=custom:dashscope-openai` — the stale entries persisted

## Resolution

**Step A:** Remove stale credential pool entries
```bash
python3 -c "
import json
with open('/home/tapway/.hermes/auth.json') as f:
    data = json.load(f)
pool = data.get('credential_pool', {})
for key in list(pool.keys()):
    if 'dashscope' in key.lower():
        del pool[key]
data['credential_pool'] = pool
with open('/home/tapway/.hermes/auth.json', 'w') as f:
    json.dump(data, f, indent=2)
"
```

**Step B:** Fix truncated key in custom_providers list
```bash
python3 -c "
import yaml
with open('/home/tapway/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f)
correct_key = cfg['model']['api_key']
for c in cfg.get('custom_providers', []):
    if len(c.get('api_key','')) < 20:
        c['api_key'] = correct_key
with open('/home/tapway/.hermes/config.yaml', 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
"
```

**Step C:** Verify
```bash
python3 -c "
import yaml, json
# Check pool
d = json.load(open('/home/tapway/.hermes/auth.json'))
pool = d.get('credential_pool', {})
print('Pool keys:', list(pool.keys()))
# Check custom_providers
cfg = yaml.safe_load(open('/home/tapway/.hermes/config.yaml'))
for c in cfg.get('custom_providers', []):
    print(f'{c[\"name\"]}: key_len={len(c.get(\"api_key\",\"\"))}')
"
```

## Prevention

- When adding a `custom_providers` entry, always copy the API key explicitly — don't rely on `hermes config set` which may truncate
- After modifying `custom_providers` or `model.api_key`, check `auth.json credential_pool` for stale entries
- The `read_file` tool displays 35-char API keys as `sk-c0b...ca38` (display truncation) — **always verify with `len()`** before assuming `...` is in the actual value