# gbrain Model Resolution Chain Debugging

## The Bug

When gbrain runs through an OpenRouter proxy (configured via `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and `OPENAI_API_KEY` set to the OpenRouter key), the model resolution in `reconfigureGatewayWithEngine()` can produce an invalid model ID like `openai:claude-sonnet-4-6`.

## Full Debugging Walkthrough (from 2026-06-12 dream cycle)

### Initial Symptoms

Dream cycle output showed two related failures:

**1. patterns phase — hard failure:**
```
[cycle.patterns] start
...
"error": {
  "class": "InternalError",
  "code": "PATTERNS_PHASE_FAIL",
  "message": "subagent job rejected: data.model \"claude-sonnet-4-6\" references an unknown provider."
}
```

**2. propose_takes phase — 100 silent extraction failures:**
```
"warnings": [
  "extractor failed on companies/insignia: [chat(openai:claude-sonnet-4-6)] claude-sonnet-4-6 is not a valid model ID",
  "extractor failed on persons/jack-jack: [chat(openai:claude-sonnet-4-6)] claude-sonnet-4-6 is not a valid model ID",
  ...
]
```

### Diagnosis

#### Step 1: Check DB-level config overrides

```bash
psql postgresql://gbrain@127.0.0.1:5432/gbrain -c "SELECT * FROM config ORDER BY key"
```

Result — only 7 rows, NO model overrides:
```
chunk_strategy        | semantic
embedding_dimensions  | 1536
embedding_model       | openrouter:openai/text-embedding-3-small
sync.last_commit      | 7d0378...
sync.last_run         | ...
sync.repo_path        | /home/cheehow/brain
version               | 92
```

#### Step 2: Check global config.json

```bash
cat ~/.gbrain/config.json
```

```json
{
  "engine": "postgres",
  "embedding_model": "openrouter:openai/text-embedding-3-small",
  "embedding_dimensions": 1536,
  "expansion_model": "openai:gpt-5.2",
  "chat_model": "openai:gpt-5.2",
  ...
}
```

So `chat_model` = `"openai:gpt-5.2"`. The `openai:` provider prefix comes from here.

#### Step 3: Check for deprecated config keys

```bash
cd ~/gbrain && bun run src/cli.ts config get models.default
# Config key not found

cd ~/gbrain && bun run src/cli.ts config get models.tier.subagent
# Config key not found

cd ~/gbrain && bun run src/cli.ts config get models.dream.patterns
# Config key not found

cd ~/gbrain && bun run src/cli.ts config get dream.patterns.model
# Config key not found
```

All unset — resolution will fall through to hardcoded defaults.

#### Step 4: Trace the resolution chain in source code

**File: `src/core/ai/gateway.ts` — `reconfigureGatewayWithEngine()` (line 402)**

```typescript
const newChat = await resolveModel(engine, {
    configKey: 'models.chat',
    tier: 'reasoning',
    fallback: cfg.chat_model ?? DEFAULT_CHAT_MODEL,  // "openai:gpt-5.2"
});
```

**File: `src/core/model-config.ts` — `resolveModel()` (line 125)**

1. CLI flag (`--model`) — no
2. `models.chat` config — not set in DB
3. Deprecated config — none specified
4. `models.default` — not set in DB
5. `models.tier.reasoning` — not set in DB
6. `GBRAIN_MODEL` env var — not set
7. **`TIER_DEFAULTS.reasoning`** = `'claude-sonnet-4-6'` ← WINNER
8. Hardcoded fallback (`"openai:gpt-5.2"`) — never reached

So `newChat` = `'claude-sonnet-4-6'` (bare, no provider prefix).

**Back in `reconfigureGatewayWithEngine()` (line 423):**

```typescript
const chatFull = newChat.includes(':') ? newChat
  : prefixWithProviderFrom(cfg.chat_model ?? DEFAULT_CHAT_MODEL, newChat);
```

`newChat` = `'claude-sonnet-4-6'` — does NOT contain `:`, so calls `prefixWithProviderFrom`.

**`prefixWithProviderFrom()` (line 443):**

```typescript
function prefixWithProviderFrom(original: string, bare: string): string {
  const colon = original.indexOf(':');
  if (colon === -1) return bare;
  return `${original.slice(0, colon)}:${bare}`;
}
```

`original` = `'openai:gpt-5.2'` → extracts `'openai'` prefix
`bare` = `'claude-sonnet-4-6'`
→ Returns **`'openai:claude-sonnet-4-6'`**

This becomes the gateway's `chat_model`. All subsequent `gateway.chat()` calls without explicit model override use this invalid ID.

#### Step 5: Why the patterns phase also fails independently

The patterns phase (`src/core/cycle/patterns.ts`) resolves its model separately:

```typescript
const model = await resolveModel(engine, {
    configKey: 'models.dream.patterns',
    deprecatedConfigKey: 'dream.patterns.model',
    tier: 'reasoning',
    fallback: 'sonnet',  // alias resolves to bare 'claude-sonnet-4-6'
});
```

Same resolution chain (no DB overrides) → same bare result `'claude-sonnet-4-6'`. But instead of going through the gateway, this bare model is passed directly as `data.model` to the subagent handler. The subagent handler calls `classifyCapabilities('claude-sonnet-4-6')`, which calls `parseModelId()` — and `parseModelId` requires `provider:model` format (a colon). No colon = throws → `classifyCapabilities` returns `'unknown'` → subagent job rejected.

#### Step 6: Why the `openai:` provider was configured

The gbrain-runner.py wrapper sets:
```python
env["OPENAI_API_KEY"] = key
env["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
```

This routes all OpenAI-API-format calls through OpenRouter. The original config (`chat_model: "openai:gpt-5.2"`) uses the `openai:` provider prefix intentionally — it works fine with OpenRouter as a drop-in. The problem is that `prefixWithProviderFrom` blindly reuses this `openai:` prefix for a **Claude** model, which doesn't exist on OpenAI (or OpenRouter as `claude-sonnet-4-6` — on OpenRouter it would be `anthropic/claude-sonnet-4-6`).

### The Real Underlying Issue

`TIER_DEFAULTS` stores bare model names (`claude-sonnet-4-6`) that work for Anthropic-direct code paths. But `reconfigureGatewayWithEngine` uses `prefixWithProviderFrom` to attach the provider from the existing config — this works correctly when the tier default matches the existing provider's model family, but fails when it doesn't.

### Key Source Files

| File | Role |
|------|------|
| `src/core/model-config.ts` | `resolveModel()`, `TIER_DEFAULTS`, `DEFAULT_ALIASES`, `resolveAlias()` |
| `src/core/ai/gateway.ts` | `reconfigureGatewayWithEngine()` (line 402), `prefixWithProviderFrom()` (line 443), `chat()` (line 2176) |
| `src/core/ai/capabilities.ts` | `classifyCapabilities()`, `getProviderCapabilities()` |
| `src/core/ai/model-resolver.ts` | `parseModelId()`, `resolveRecipe()` |
| `src/core/minions/handlers/subagent.ts` | Subagent model validation (line 165-178) |
| `src/core/cycle/patterns.ts` | Patterns phase model resolution (line 147-152) |
| `src/core/cycle/propose-takes.ts` | Propose-takes phase — uses `gateway.chat()` without model override → gets broken `chat_model` |
| `src/cli.ts` | `reconfigureGatewayWithEngine()` call (line 1614-1615), `buildGatewayConfig()` (line 1496) |