# Backup Provider → Anthropic SDK Proxy for GBrain

## Overview

GBrain's dream cycle (synthesize/patterns phases) and subagent handler use the Anthropic SDK (`@anthropic-ai/sdk`) for LLM calls. Instead of a direct Anthropic API key, these can be routed through Backup Provider, which proxies the Anthropic Messages API format.

## Critical: Double-Path BaseURL Bug

The Anthropic SDK **automatically appends `/v1/messages`** to the configured `baseURL`. Setting `baseURL: 'https://backup-provider.ai/api/v1'` causes requests to hit `https://backup-provider.ai/api/v1/v1/messages` → **404 error**.

**✅ Correct:** `baseURL: 'https://backup-provider.ai/api'` (no `/v1`)
**❌ Wrong:** `baseURL: 'https://backup-provider.ai/api/v1'` (SDK adds another `/v1`)

## Environment Variable Fallback Chain

All patched code follows this priority:

```
1. OPENROUTER_API_KEY  → proxy through Backup Provider (baseURL = backup-provider.ai/api)
2. ANTHROPIC_API_KEY   → direct Anthropic (no baseURL override)
3. Neither set         → skip (synthesize/patterns not available)
```

## Files Patched

### 1. `src/core/cycle/synthesize.ts`

**`makeHaikuClient()`** — Routes the significance verdict judge (Haiku) through Backup Provider:

```typescript
function makeHaikuClient(): JudgeClient | null {
  const apiKey = process.env.OPENROUTER_API_KEY || process.env.ANTHROPIC_API_KEY;
  const orBase = process.env.OPENROUTER_BASE_URL || 'https://backup-provider.ai/api';
  const baseURL = process.env.ANTHROPIC_BASE_URL || (process.env.OPENROUTER_API_KEY ? orBase : undefined);
  if (!apiKey) return null;
  const client = new Anthropic({ apiKey, baseURL });
  return { create: client.messages.create.bind(client.messages) };
}
```

**Config check fix** — The original code checks only `config.corpusDir` before allowing the phase to proceed. When using `meeting_transcripts_dir` instead of `session_corpus_dir`, this short-circuits with "not configured". Fix:

```typescript
// Before (broken):
if (!opts.inputFile && !config.corpusDir) { return skipped(...); }

// After (fixed):
if (!opts.inputFile && !config.corpusDir && !config.meetingTranscriptsDir) { return skipped(...); }
```

**Inline synthesis replacement** — The original fan-out dispatches subagent jobs to MinionQueue (needs a separate worker daemon which doesn't work with PGLite). Replaced with direct inline Anthropic API calls. See "Inline Synthesis Patch" section below.

### 2. `src/core/minions/handlers/subagent.ts`

**`makeAnthropic` factory** — Routes the subagent LLM loop (Sonnet synthesis + tool use) through Backup Provider:

```typescript
const makeAnthropic = deps.makeAnthropic ?? (() => {
  const apiKey = process.env.OPENROUTER_API_KEY || process.env.ANTHROPIC_API_KEY;
  const orBase = process.env.OPENROUTER_BASE_URL || 'https://backup-provider.ai/api';
  const baseURL = process.env.ANTHROPIC_BASE_URL || (process.env.OPENROUTER_API_KEY ? orBase : undefined);
  return new Anthropic({ apiKey, baseURL });
});
```

### 3. `src/core/cycle/patterns.ts`

Accepts `OPENROUTER_API_KEY` in addition to `ANTHROPIC_API_KEY`:

```typescript
// Before:
if (!process.env.ANTHROPIC_API_KEY) { return skipped(...); }

// After:
if (!process.env.OPENROUTER_API_KEY && !process.env.ANTHROPIC_API_KEY) { return skipped(...); }
```

### 4. `src/core/cycle/transcript-discovery.ts`

Accepts `.md` files alongside `.txt`:

```typescript
// Before:
if (!name.endsWith('.txt')) continue;

// After:
if (!name.endsWith('.txt') && !name.endsWith('.md')) continue;
```

## Model Names (Backup Provider Format)

When proxying through Backup Provider, use their model identifiers:

| Role | Anthropic ID | Backup Provider ID | Cost (per 1K tokens) |
|---|---|---|---|
| Synthesis (Sonnet) | `claude-sonnet-4-6` | `anthropic/claude-sonnet-4` | $0.003 / $0.015 |
| Verdict (Haiku) | `claude-haiku-4-5-20251001` | `anthropic/claude-haiku-4.5` | $0.001 / $0.005 |

Set via gbrain config:
```bash
bun run src/cli.ts config set dream.synthesize.model anthropic/claude-sonnet-4
bun run src/cli.ts config set dream.synthesize.verdict_model anthropic/claude-haiku-4.5
```

## Inline Synthesis Patch (PGLite Alternative)

### Why it's needed

GBrain's native synthesize implementation uses a **MinionQueue subagent architecture**: submits `subagent` jobs to a queue, then `waitForCompletion` polls until a separate worker process (`gbrain jobs work`) processes them. This **does not work with PGLite**, which uses an exclusive file lock — only one process can connect at a time. All subagent jobs sit in "waiting" forever.

### What the patch does

Replaces the MinionQueue fan-out (lines 169-221 in `src/core/cycle/synthesize.ts`) with direct Anthropic SDK calls. For each worth-processing transcript:

1. Build a synthesis prompt truncated to ~12K chars (within context window)
2. Call `synthClient.messages.create()` with the Sonnet model
3. Parse the response — extract frontmatter (title, type, tags) from YAML
4. Write to DB via `engine.putPage()` 
5. Write to disk via `writeFileSync()` (dual-write)
6. Track outcomes for the summary page

The synthesis prompt instructs the model to output **only** markdown with YAML frontmatter:

```
You are synthesizing a meeting transcript into a personal knowledge brain page. 
Output ONLY the page content as a markdown document with YAML frontmatter.

The frontmatter must include:
- type: "note" or "reflection"
- title: a descriptive title
- tags: relevant keywords

The body must:
1. Quote key insights verbatim from the transcript
2. Include wikilinks to relevant people, companies, or concepts
3. Be structured and well-organized

Remember: Output ONLY the markdown page content with frontmatter. No explanations.
```

### Pages written

The inline approach writes pages to:
- `wiki/personal/reflections/<date>-<topic>-<hash>/` — extracted from frontmatter title
- `dream-cycle-summaries/<date>` — summary index

### Postgres alternative

If using Postgres + pgvector (instead of PGLite), the original subagent architecture works because a separate `gbrain jobs work` daemon can connect concurrently. The `patterns` phase has the same limitation — it also uses `queue.add('subagent')`.

## Verification

Test the proxy works with a direct API call:

```bash
OPENROUTER_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-)
curl -s -X POST https://backup-provider.ai/api/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $OPENROUTER_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"anthropic/claude-haiku-4.5","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

Expected: 200 with Anthropic-format response (not 404/401).
