---
name: gbrain-maintain
description: "Brain health maintenance — run health checks, find and fix orphans, detect stale pages, fix broken links, check embedding coverage."
version: 1.0.0
author: Your Company
tags: [gbrain, maintain, health, cleanup]
---
# gbrain Maintain

Keep the brain healthy — detect and fix structural issues.

## Health Dashboard

Run these to get a full picture of brain health:

```bash
mcp_gbrain_get_health()           # Overall dashboard
mcp_gbrain_run_doctor()           # Deep diagnostics + auto-fix suggestions
mcp_gbrain_find_orphans()         # Pages with no inbound wikilinks
mcp_gbrain_find_contradictions()  # Suspected contradictions
```

## Maintenance Tasks

### 1. Fix Orphans (pages with no inbound links)

```bash
mcp_gbrain_find_orphans()
```
For each orphan:
- Check if it SHOULD have inbound links (is it a notable entity?)
- If yes → add back-links from pages that reference it
- If no → leave it (some pages are standalone references)

### 2. Check Stale Pages

Use `mcp_gbrain_list_pages(sort=updated_asc, limit=50)` to find oldest pages.
For pages over 180 days without updates:
- Read current content
- Update if information has changed
- Add "Last reviewed: YYYY-MM-DD" note if still accurate

### 3. Diagnose & Fix Embedding Failures

When the embed pipeline fails with `"OpenAI embedding requires OPENAI_API_KEY"` or similar credential errors, the problem is almost always in the **credential flow** — not the model itself. The gbrain wrapper script (`~/.local/bin/gbrain`) must set `OPENAI_API_KEY` and `OPENAI_BASE_URL` before calling gbrain's TypeScript CLI.

**Diagnostic trace (top to bottom):**

```bash
# 1) Check what model gbrain is configured to use
gbrain config show | grep embedding_model
# Should be: openai:text-embedding-3-large (routes through Backup Provider)

# 2) Check if the wrapper sets OPENAI_BASE_URL to Backup Provider
head -5 ~/.local/bin/gbrain
# Should have: export OPENAI_BASE_URL="https://backup-provider.ai/api/v1"

# 3) Check if the wrapper actually resolves the API key
#    The wrapper tries to find OPENROUTER_API_KEY from:
#    a) $OPENROUTER_API_KEY env var
#    b) ~/.hermes/.env file
#    c) auth.json credential pool (reads creds[N].access_token)
bash ~/.local/bin/gbrain -c 'echo "OPENAI_API_KEY: ${OPENAI_API_KEY:+SET}${OPENAI_API_KEY:-MISSING}"' 2>/dev/null

# 4) Verify the Backup Provider credential exists in auth.json
node -e "const d=require('/home/your-company/.hermes/auth.json'); console.log('Has backup-provider cred:',!!(d.credential_pool?.backup-provider?.length))"

# 5) Check the actual credential shape — does it have access_token?
node -e "const d=require('/home/your-company/.hermes/auth.json'); const c=d.credential_pool?.backup-provider?.[0]; console.log('Credential keys:',Object.keys(c||{}).join(', '))"

# 6) Check if OPENROUTER_API_KEY is available to the cron environment
#    (the autopilot cron at */5 * * * * runs autopilot-run.sh which
#     sources ~/.zshrc or ~/.bashrc)
grep OPENROUTER ~/.zshrc ~/.bashrc 2>/dev/null

# 7) Check if .env has the key (may be commented out)
grep OPENROUTER_API_KEY ~/.hermes/.env
```

**Common failure modes:**

| Symptom | Root cause | Fix |
|---|---|---|
| `"OpenAI embedding requires OPENAI_API_KEY"` on every page | `OPENAI_API_KEY` not set when gbrain CLI runs | Fix wrapper to resolve from correct source (see below) |
| Embedded counter shows `XXXX/1188 (283%)` | Embedding errors keep the counter running without progress | Fix the credential issue, then re-run `gbrain embed --stale` |
| Wrapper can't find key even though Hermes works | The key lives in the gateway process env only, not in any dotfile | Add `export OPENROUTER_API_KEY=...` to `~/.bashrc` or uncomment in `~/.hermes/.env` |
| auth.json has credential but wrapper returns empty | Wrapper reads `access_token` field but Backup Provider credential stores via `secret_fingerprint` only | Update wrapper to check `$OPENROUTER_API_KEY` env var directly, then fall back to `~/.hermes/.env` via python-dotenv, then auth.json |

**Root cause deep-dive:**

The gbrain wrapper (`~/.local/bin/gbrain`) is a bash script that:

1. Sets `OPENAI_BASE_URL` to `https://backup-provider.ai/api/v1`
2. Tries to resolve the API key via inline Node.js reading `auth.json.credential_pool.backup-provider[0].access_token`
3. If found, exports it as `OPENAI_API_KEY`
4. Calls `cd ~/gbrain && exec bun run src/cli.ts "$@"`

Inside gbrain's TypeScript, `configureGateway(buildGatewayConfig(config))` reads `process.env.OPENAI_API_KEY` from the AI gateway config (`src/core/ai/gateway.ts` → `src/cli.ts:buildGatewayConfig`, line 1497: `env: { ...envFromConfig, ...process.env }`). If the wrapper never successfully sets it, the `instantiateEmbedding()` function at line 969-981 throws `"OpenAI embedding requires OPENAI_API_KEY."`.

**The actual fix:**

```bash
# Patch the wrapper to check env var directly (simplest, most reliable)
# Add BEFORE the node -e line:
if [ -z "$GET_KEY" ] && [ -n "$OPENROUTER_API_KEY" ]; then
  GET_KEY="$OPENROUTER_API_KEY"
fi

# Then also check .env via python-dotenv:
if [ -z "$GET_KEY" ]; then
  GET_KEY=$(python3 -c "
from hermes_cli.config import load_env
env = load_env()
print(env.get('OPENROUTER_API_KEY','') or '')
" 2>/dev/null)
fi
```

Then run `gbrain embed --stale` to re-embed all stale chunks.

### 4. Check Contradictions

```bash
mcp_gbrain_find_contradictions(severity="high")
```
High-severity contradictions need immediate resolution. Medium/low can be queued.

### 5. Sync Brain Repo

```bash
mcp_gbrain_sync_brain()  # Incremental git → brain sync
```

## Monthly Maintenance Checklist

- [ ] Run health dashboard — log current metrics
- [ ] Fix orphan pages (create back-links where needed)
- [ ] Review 10 oldest pages for staleness
- [ ] Check for contradictions
- [ ] Run embedding sync if coverage < 95%
- [ ] Log maintenance event

## Quick Health Check (Daily)

```bash
health = mcp_gbrain_get_health()
# Alert if: orphan_count > 50, stale_count > 100, embed_coverage < 90%
```

## Pitfalls

- ❌ Running embed jobs unnecessarily (wasteful — only when coverage drops)
- ❌ Deleting orphan pages that should exist but just need links
- ❌ Ignoring contradictions (they compound into unreliable data)
- ❌ Over-maintaining — don't fix what isn't broken