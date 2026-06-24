# Dream Cycle Troubleshooting Reference

Debugging walkthrough from June 2026 session covering the full dream cycle stack.

## Phase-by-Phase Error Reference

### Patterns: `PATTERNS_PHASE_FAIL`

```
[InternalError/PATTERNS_PHASE_FAIL] subagent job rejected: 
data.model "claude-sonnet-4-6" references an unknown provider.
```

**Root cause:** `TIER_DEFAULTS.reasoning = 'claude-sonnet-4-6'` (bare model, no provider prefix).
The `getProviderCapabilities()` → `classifyCapabilities()` call needs `provider:model` format.

**Fix:** Set `models.tier.reasoning` in gbrain PGLite config:
```bash
cd ~/gbrain && gbrain config set models.tier.reasoning "openrouter:anthropic/claude-sonnet-4"
```

### Synthesize: `SYNTH_PHASE_FAIL` — 401 auth

```
[InternalError/SYNTH_PHASE_FAIL] 401 {"type":"error","error":{"type":"authentication_error",
"message":"invalid x-api-key"}}
```

**Two possible causes:**

1. **Invalid Anthropic API key** (401 from Anthropic's API). Test directly:
   ```python
   import requests
   r = requests.post("https://api.anthropic.com/v1/messages",
       headers={"x-api-key":"key","anthropic-version":"2023-06-01"},
       json={"model":"claude-sonnet-4-6","max_tokens":10,"messages":[{"role":"user","content":"hi"}]})
   print(r.status_code)  # 200 = OK, 401 = bad key
   ```

2. **Wrong model prefix** (401 from OpenRouter). The subagent code at `src/core/minions/handlers/subagent.ts` calls `isAnthropicProvider()` which checks the provider prefix (before `:`). `openrouter:anthropic/claude-sonnet-4` has provider `openrouter` → NOT Anthropic. Fix:
   ```bash
   cd ~/gbrain && gbrain config set models.dream.synthesize "anthropic:claude-sonnet-4-6"
   ```

### Synthesize: All children timeout (PGLite limitation)

Dream cycle summary shows:
```
Dream cycle (partial) in 100-120s:
  ✗ synthesize  synthesize phase failed ...
```
And the dream-cycle-summaries page shows:
```
**Children:** 0 completed, 86 failed/timeout.
```

This is NOT an authentication error — the subagent jobs were submitted successfully but no worker process exists to execute them. On PGLite, the exclusive file lock prevents running `gbrain jobs work` concurrently.

**Confirm by checking the dream cycle summary page:**
```bash
cat ~/brain/dream-cycle-summaries/$(date +%Y-%m-%d).md
```
If children are 0 completed, N failed/timeout → PGLite worker limitation.

## Key Architectural Insights

### `isAnthropicProvider()` behavior

```typescript
// src/core/model-config.ts
export function isAnthropicProvider(modelString: string): boolean {
  const colon = trimmed.indexOf(':');
  if (colon !== -1) {
    return trimmed.slice(0, colon).trim().toLowerCase() === 'anthropic';
  }
  return trimmed.toLowerCase().startsWith('claude-');
}
```

- `anthropic:claude-sonnet-4-6` → provider = `anthropic` → ✅ true
- `openrouter:anthropic/claude-sonnet-4` → provider = `openrouter` → ❌ false
- `claude-sonnet-4-6` → starts with `claude-` → ✅ true

### `agent.use_gateway_loop` flag

This config exists to route subagent jobs through a provider-agnostic gateway loop instead of Anthropic-direct. However:

1. Stored in PGLite `config` table as TEXT (not JSON boolean)
2. Code reads it with: `engine.getConfig('agent.use_gateway_loop')` which returns raw DB text
3. Check: `typeof useGatewayLoopRaw === 'string' && (useGatewayLoopRaw === 'true' || useGatewayLoopRaw === '1')`
4. `gbrain config set agent.use_gateway_loop true --force` stores it as typed boolean `true`, NOT string `"true"` → fails the typeof check
5. Fix: insert directly into PGLite:
   ```javascript
   await db.query("INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT DO UPDATE",
     ["agent.use_gateway_loop", "true"])
   ```
6. Even with gateway loop enabled, the OpenRouter auth chain still fails with 401 (experimental, not production-ready in v0.40.8.1)

### Synthesize phase flow

```
synthesize.ts:
  1. Read meeting_transcripts_dir (or session_corpus_dir) for .md/.txt files
  2. Filter by: > min_chars, not in exclude_patterns, not already synthesized (verdicts cache)
  3. Split long transcripts into chunks (max_chars_per_chunk from model context budget)
  4. For each chunk → submit subagent job to MinionQueue
  5. Wait for all children via waitForCompletion (35 min timeout per child)
  6. Collect put_page results → reverse-write to filesystem
  7. Write summary page at dream-cycle-summaries/<date>.md
```

The subagent handler (`src/core/minions/handlers/subagent.ts`):
1. Submits job to queue → status "waiting"
2. `waitForCompletion` polls until terminal state
3. Worker `gbrain jobs work` picks up "waiting" jobs and executes them
4. On PGLite, step 3 never happens → timeout after 35 minutes

## gbrain Wrapper Redaction Pitfall

When updating `~/.local/bin/gbrain` via `write_file` or `patch` tools, API key values in the content may be replaced with `***` by the system's redaction layer. This corrupts the grep pattern.

**Symptom:** The grep command contains `***` inside the single-quote pattern:
```bash
OP_KEY=$(grep -m1 '^OPENROUTER_API_KEY=***  # BROKEN - *** in the grep pattern
```

**Expected (correct):**
```bash
OP_KEY=$(grep -m1 '^OPENROUTER_API_KEY=***   # CORRECT - pattern ends at the quote
```

**Fix:** Use a heredoc in terminal instead of write_file:
```bash
cat > ~/.local/bin/gbrain << 'SCRIPT_END'
#!/bin/bash
...
SCRIPT_END
```

**Verification:** After writing, check the actual file bytes:
```bash
head -5 ~/.local/bin/gbrain | xxd | head -3
# Look for: 5e4f 5045 4e52 4f55 5445 525f 4150 (^OPENROUTER_AP)
# The pattern should end right after the = sign, not have key chars inside
```