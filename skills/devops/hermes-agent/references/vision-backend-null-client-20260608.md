# Vision Backend Null-Client Diagnostic (2026-06-08)

Full session transcript of diagnosing why `vision_analyze` was absent from tools
despite `hermes tools list` showing `✓ enabled  vision`.

## Timeline

1. **User report**: vision_analyze not in tool list
2. **Agent check**: `hermes tools list` → ✓ vision enabled
3. **Agent fix attempt**: Added `vision` to `toolsets` in config.yaml
   → resulted in YAML string corruption: `toolsets: '["hermes-cli", "vision"]'`
4. **User frustration**: "you have asked me to restart like 3 times and nothing worked"
5. **Agent deep dive**: Traced through `tools_config.py` → `_toolset_has_keys("vision")`
   → calls `resolve_vision_provider_client()` → returns `(provider, None, None)`
6. **Root cause**: `auxiliary.vision.provider` was `custom:dashscope-openai` but
   `custom_providers` entry was a malformed YAML string:
   ```yaml
   custom_providers: '[{"name": "dashscope-openai", ...}]'  # string, not list
   ```
   Produced: `resolve_provider_client: unknown provider 'dashscope-openai'`
7. **Fix**: Switched vision to openrouter + gemini-2.5-flash:
   ```bash
   hermes config set auxiliary.vision.provider openrouter
   hermes config set auxiliary.vision.model google/gemini-2.5-flash
   ```
8. **Verification**: `resolve_vision_provider_client()` → `client OK=True`

## Key Insight

`hermes tools list` shows toolset registration status (✓ enabled / ✗ disabled).
It does NOT show whether the toolset's backend actually resolves at session init.
A ✓ enabled toolset with a broken backend silently strips its tools — no error, no warning.

## Diagnostic One-Liner

```bash
python3 -c "
import sys
sys.path.insert(0, '/home/tapway/.hermes/hermes-agent')
from agent.auxiliary_client import resolve_vision_provider_client
p, c, m = resolve_vision_provider_client()
print('OK' if c else 'BROKEN', '-', p, '-', m)
"
```

## Secondary Finding: `hermes config set` Corrupts Lists

`hermes config set` wraps all values in YAML single quotes, turning:
```yaml
toolsets: ["hermes-cli", "vision"]
```
into:
```yaml
toolsets: '["hermes-cli", "vision"]'   # YAML string, not list
```

Affected keys: `toolsets`, `platform_toolsets`, `fallback_providers`, `custom_providers`.
Detection: `grep "toolsets: '\|custom_providers: '" ~/.hermes/config.yaml`
Any hit = corruption. Fix with Python surgery (see skill body).
