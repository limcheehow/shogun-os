# Dream Cycle Configuration

## Overview

The dream cycle runs: lint → backlinks → sync → synthesize → extract → patterns → embed → orphans

Located at `~/.hermes/scripts/dream-cycle.sh`.

## API Key Bug (fixed May 11, 2026)

The script originally used:
```bash
grep OPENROUTER_API_KEY ~/.hermes/.env | head -1 | cut -d= -f2
```

Problem: `grep OPENROUTER_API_KEY` matches ALL lines including commented ones. The `.env` file has:
```
# OPENROUTER_API_KEY=
OPENROUTER_API_KEY=sk-or-v1-...
```

The commented line is first, so `head -1` returns an empty value.

**Fix:**
```bash
grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-
```
The `^` anchor and `-m1` ensure it only matches uncommented lines, first occurrence.

## Brain Directory Requirement

The `dream` command requires a brain directory. Without the `--dir` flag, it reads `sync.repo_path` from the database config. If the engine fails to connect (e.g., stale PGLite lock, or no config file), the command fails with:

```
No brain directory found. Pass --dir <path> or configure one via `gbrain init`.
```

**Fix:** Pass `--dir ~/brain` explicitly in the script and cron prompt.

## Running Manually

The correct command (via the gbrain wrapper at `~/.local/bin/gbrain` which injects API keys):

```bash
cd ~/gbrain && gbrain dream
```

If running without the wrapper, pass API keys explicitly:

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  bun run src/cli.ts dream
```

## Common Startup Errors

### Wrong command: `python3 -m gbrain dreamcycle`

This fails because gbrain is a Bun CLI, not a Python module, and the command is `gbrain dream` not `dreamcycle`. The cron job must call `gbrain dream` or `bun run src/cli.ts dream`.

### `models.tier.reasoning` not set → patterns phase fails

The patterns phase fails with:
```
PATTERNS_PHASE_FAIL — data.model "claude-sonnet-4-6" references an unknown provider.
```

**Fix:** Set the reasoning tier to a valid `provider:model` pair:
```bash
gbrain config set models.tier.reasoning "openrouter:anthropic/claude-sonnet-4"
```
This affects the patterns phase, not synthesize.

### `models.dream.synthesize` vs deprecated `dream.synthesize.model`

The old config key `dream.synthesize.model` prints a deprecation warning and is ignored when `models.dream.synthesize` is set. Always use the new key:
```bash
gbrain config set models.dream.synthesize "openrouter:anthropic/claude-sonnet-4"  # OR
gbrain config set models.dream.synthesize "anthropic:claude-sonnet-4-6"           # Anthropic-direct
```

### 401 from synthesize subagent — invalid Anthropic API key

If `models.dream.synthesize` is set to an Anthropic model, the subagent loop requires a valid `ANTHROPIC_API_KEY` in the environment. The key is read by the gbrain wrapper at `~/.local/bin/gbrain`:

```bash
# The wrapper must pass ANTHROPIC_API_KEY to the exec'd process:
ANTHROPIC_KEY=$(grep -m1 '^ANTHROPIC_API_KEY=' ~/.hermes/.env | cut -d= -f2-)
exec env \
  OPENROUTER_API_KEY=*** \
  ANTHROPIC_API_KEY=*** \
  ...
```

Test the key directly:
```bash
curl -s -w "\nHTTP:%{http_code}" -X POST "https://api.anthropic.com/v1/messages" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-6","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

Expected: HTTP 200. If 401, the key is expired/revoked.

### OpenRouter auth via gateway loop (experimental)

The subagent code has a `agent.use_gateway_loop` flag that routes subagent jobs through the provider-agnostic gateway loop instead of the Anthropic-direct path. Enable it via:

```bash
# Must write to the DB config table, not just the JSON config:
cd ~/gbrain && bun -e '
const{PGlite}=await import("@electric-sql/pglite");
const db=await PGlite.create("/home/cheehow/.gbrain/brain.pglite");
await db.query("INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2", ["agent.use_gateway_loop", "true"]);
await db.close();
'
```

**Known issues:**
- The `gbrain config set` CLI doesn't know about this key (warns "Nothing in gbrain reads this") — use the PGLite SQL above instead
- On PGLite, subagent jobs still need a separate `gbrain jobs work` daemon to process them, which the exclusive PGLite file lock prevents
- The code checks `typeof useGatewayLoopRaw === 'string'` — must be a DB text value "true", not a JSON boolean true

### Subagent jobs submitted but never processed (PGLite limitation)

On PGLite, the synthesize phase submits subagent jobs to the MinionQueue, but no worker daemon (`gbrain jobs work`) can run because PGLite's exclusive file lock prevents concurrent processes. Jobs sit in "waiting" state until they time out (~35 min).

This is an architecture limitation — Postgres + pgvector is required for the full subagent architecture. On PGLite, the other dream phases (lint, backlinks, sync, extract, patterns, embed, orphans) all complete successfully. Only synthesize (and potentially propose_takes which uses subagents) is affected.

## Stale Locks from Interrupted Runs

The dream cycle acquires a `gbrain-cycle` lock in the PGLite database. If the process is killed mid-cycle (timeout, OOM, SIGKILL/137, ^C), the lock persists and blocks future runs with:

```
"cycle_already_running"
```

**Clear it:**
```bash
cd ~/gbrain && bun -e '
const{PGlite}=await import("@electric-sql/pglite");
const db=await PGlite.create("/home/cheehow/.gbrain/brain.pglite");
await db.query("DELETE FROM gbrain_cycle_locks");
console.log("Cleared");
await db.close();
'
```

Also clear any stale `subagent` jobs left in "waiting" from the interrupted run:
```bash
cd ~/gbrain && bun -e '
const{PGlite}=await import("@electric-sql/pglite");
const db=await PGlite.create("/home/cheehow/.gbrain/brain.pglite");
await db.query("DELETE FROM minion_jobs WHERE name = $1 AND status = $2", ["subagent", "waiting"]);
await db.close();
'
```

## Timeout Considerations

The synthesize phase processes transcripts sequentially with Sonnet API calls. With ~20 transcripts, this can take 30-60+ minutes. Default terminal timeouts (600s) will kill the process. Always run in background mode:
```
notify_on_complete=true, timeout=7200
```
