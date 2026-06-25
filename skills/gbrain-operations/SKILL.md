---
name: gbrain-operations
version: 2.0.0
description: |
  GBrain operations: sync, embed, doctor, dream cycle, MCP server setup,
  lock management, schema packs, brainstorm, publish, capture, and
  common troubleshooting (PGLite, Supabase, API keys).
  Generic version — no company-specific content.
triggers:
  - "gbrain sync"
  - "gbrain embed"
  - "gbrain doctor"
  - "gbrain dream"
  - "gbrain serve"
  - "gbrain mcp"
  - "gbrain brainstorm"
  - "gbrain capture"
  - "gbrain publish"
  - "gbrain schema"
  - "gbrain autopilot"
  - "stale lock"
  - "sync lock"
  - "pglite corruption"
  - "supabase auto-pause"
  - "supabase rest api"
  - "migrate pglite"
  - "dream cycle"
---

# GBrain Operations

Core operations for managing a [GBrain](https://github.com/garrytan/gbrain) knowledge base. Covers the full lifecycle: sync content, generate embeddings, maintain health, run dream cycles, manage MCP connectivity, and troubleshoot common issues.

## Prerequisites

```bash
# Install gbrain
bun install -g github:garrytan/gbrain

# Verify
gbrain --version
```

Environment variables needed (set in `~/.hermes/.env` or profile `.env`):

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL` | Postgres connection (for production gbrain) |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `OPENROUTER_API_KEY` | Embeddings (gbrain uses OpenRouter by default) |

---

## Quick Reference

| Operation | Command | When |
|-----------|---------|------|
| Sync content | `gbrain sync` | After changing brain files |
| Generate embeddings | `gbrain embed` | After sync, to update vector search |
| Health check | `gbrain doctor` | Daily or when something feels wrong |
| Clean cycle | `gbrain dream` | Nightly maintenance |
| Serve MCP | `gbrain serve` | For Hermes MCP connectivity |
| Web UI | `gbrain web` | Browse brain in browser |
| Publish site | `gbrain publish` | Export static site |

---

## CLI Reference

### gbrain sync

Scans brain files for changes and updates the database.

```bash
# Incremental sync (recommended)
gbrain sync

# Full re-sync (ignores checkpoint)
gbrain sync --full

# Dry run — preview changes
gbrain sync --dry-run
```

**Best practices:**
- Run `gbrain sync --dry-run` before `--full` to preview impact
- Incremental sync is fast enough to run every 15 min via cron
- Full sync is needed when you change filename conventions or restructure folders

### gbrain embed

Generates/updates vector embeddings for semantic search.

```bash
# Embed all documents needing updates
gbrain embed

# Embed only stale documents (faster)
gbrain embed --stale

# Full re-embed (regenerates all embeddings)
gbrain embed --full
```

**Embedding provider:** gbrain uses OpenRouter by default. Set `OPENROUTER_API_KEY` in the environment. To use a different provider:

```bash
# Use OpenAI
export OPENAI_API_KEY="sk-..."
gbrain embed --provider openai

# Use local model
gbrain embed --provider local
```

### gbrain doctor

Comprehensive health check.

```bash
gbrain doctor

# Fix auto-fixable issues
gbrain doctor --fix

# Verbose output
gbrain doctor --verbose
```

Checks performed:
1. Database connectivity
2. Page integrity (missing content, broken frontmatter)
3. Embedding coverage
4. Stale pages
5. Orphan pages (no inbound links)
6. Lock files (stale PGLite locks)

### gbrain dream

Nightly maintenance cycle. Synthesizes new knowledge, resolves takes, consolidates facts, and prunes outdated content.

```bash
# Full dream cycle
gbrain dream

# Dry run — preview changes
gbrain dream --dry-run

# Run specific phase only
gbrain dream --phase synthesize
gbrain dream --phase consolidate

# Set timeout (default: 180s)
gbrain dream --timeout 300
```

**Cron setup** (run nightly via default profile):
```bash
hermes cron create \
  --name "gbrain-dream-cycle" \
  --schedule "0 2 * * *" \
  --prompt "Run: cd /path/to/brain && gbrain dream" \
  --deliver local
```

### gbrain serve

Starts the MCP server for Hermes integration.

```bash
# Standard MCP serve
gbrain serve

# With specific source
GBRAIN_SOURCE="hr" gbrain serve

# With federated read
GBRAIN_FEDERATED_READ=true gbrain serve
```

**Hermes config** (add to profile's `config.yaml` or `mcp_servers`):
```yaml
mcp_servers:
  gbrain:
    command: gbrain
    args: [serve]
    env:
      GBRAIN_SOURCE: "${GBRAIN_SOURCE}"
      GBRAIN_FEDERATED_READ: "${GBRAIN_FEDERATED_READ:-true}"
```

### gbrain brainstorm

Generates new ideas by cross-referencing existing brain pages.

```bash
gbrain brainstorm --prompt "What should I research next?"
```

### gbrain capture

Captures raw data from files or stdin and creates brain pages.

```bash
# From file
gbrain capture --file ~/meeting-notes.md --slug "meetings/2026-q2-review"

# From stdin
cat notes.txt | gbrain capture --slug "quick-note"
```

---

## Python Wrapper Pattern

For running gbrain CLI commands from Python (cron scripts, enrichment pipelines):

```python
import subprocess, os

def run_gbrain(cmd: list[str], env: dict | None = None) -> dict:
    """Run a gbrain CLI command and return the result."""
    base_env = os.environ.copy()
    if env:
        base_env.update(env)
    
    try:
        result = subprocess.run(
            ["gbrain"] + cmd,
            capture_output=True, text=True, timeout=300,
            env=base_env
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timed out after 300s"}
    except FileNotFoundError:
        return {"success": False, "error": "gbrain CLI not found"}

# Usage
result = run_gbrain(["doctor"])
print(result["output"])
```

---

## Troubleshooting

### PGLite Lock Contention

**Symptom:** `gbrain sync` hangs or shows `Aborted() pglite` / `postmaster.pid` error.

**Cause:** PGLite (the embedded Postgres used in local mode) sometimes leaves stale lock files after a crash or simultaneous access.

**Fix:**
```bash
# Check for stale locks
ls -la ~/.gbrain/pglite/postmaster.pid

# Clear the lock
rm -f ~/.gbrain/pglite/postmaster.pid

# If corruption continues, migrate to Supabase:
gbrain doctor --fix  # attempts auto-recovery
```

**Prevention:**
- Never run two `gbrain` processes concurrently on the same PGLite database
- Use Supabase for production (more reliable than PGLite for >1000 pages)
- Set a cron to run `gbrain doctor --fix` daily

### Supabase Auto-Pause

**Symptom:** `gbrain sync` or `gbrain doctor` fails with connection timeout on Supabase.

**Cause:** Supabase free-tier projects auto-pause after 7 days of inactivity. Wake-up takes 5-30 seconds on first query.

**Fix:**
```bash
# Wake the database by running a simple query
curl -s "https://<project-ref>.supabase.co/rest/v1/" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"
```

**Prevention:**
- Use a cron job that runs `gbrain doctor` every 6 hours to prevent auto-pause
- Upgrade to Supabase Pro plan (no auto-pause, connection pooler)

### PGLite Database Corruption

**Symptom:** `gbrain doctor` reports `WASM runtime pglite` / `database corrupted` / recurring `Aborted()` crashes.

**Fix sequence (try in order):**
```bash
# Step 1 — attempt auto-recovery
gbrain doctor --fix

# Step 2 — clear stale locks
rm -f ~/.gbrain/pglite/postmaster.pid
gbrain doctor

# Step 3 — if still corrupted, migrate to Supabase
gbrain migrate --to supabase \
  --supabase-url "$SUPABASE_URL" \
  --supabase-key "$SUPABASE_SERVICE_ROLE_KEY"
```

### Embeddings Failing (429 / Quota)

**Symptom:** `gbrain embed` returns HTTP 429 rate limit errors.

**Cause:** OpenRouter or embedding provider rate limits.

**Fix:**
```bash
# Slow down — embed in batches
gbrain embed --stale --batch-size 10

# Or switch provider
gbrain embed --provider openai

# Check quota:
curl -s https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### gbrain MCP Connection Issues

**Symptom:** Hermes can't connect to gbrain MCP. `hermes mcp list` shows gbrain as disconnected.

**Troubleshooting:**
```bash
# 1. Is gbrain running?
ps aux | grep "gbrain serve"

# 2. Start in foreground to see errors
gbrain serve --verbose

# 3. Test connectivity from another terminal
echo '{"jsonrpc":"2.0","id":1,"method":"ping"}' | nc -U /tmp/gbrain.sock 2>/dev/null

# 4. Check environment
echo "SUPABASE_URL=$SUPABASE_URL"
echo "SUPABASE_SERVICE_ROLE_KEY=${#SUPABASE_SERVICE_ROLE_KEY} chars"
echo "OPENROUTER_API_KEY=${#OPENROUTER_API_KEY} chars"
```

---

## Cron Integration

### Brain Sync Cron

Recommended — syncs brain content every 15-30 minutes (no_agent, cheap):

```bash
# Create the sync script
cat > ~/.hermes/scripts/brain-sync.sh << 'SCRIPT'
#!/usr/bin/env bash
cd ~/brain && gbrain sync && gbrain embed --stale
SCRIPT
chmod +x ~/.hermes/scripts/brain-sync.sh

# Schedule it
hermes cron create \
  --name "brain-auto-sync" \
  --schedule "*/15 * * * *" \
  --script brain-sync.sh \
  --no-agent \
  --deliver local
```

### Dream Cycle Cron

Nightly maintenance (runs on default profile):

```bash
hermes cron create \
  --name "gbrain-dream-cycle" \
  --schedule "0 2 * * *" \
  --prompt "Run the gbrain dream maintenance cycle. Execute: cd /path/to/brain && gbrain dream. This runs synthesis, consolidation, pruning, and optionally publishes the updated brain site. Keep the prompt concise — report only anomalies." \
  --deliver local
```

---

## Brain Site (Quartz Publishing)

To publish a browsable static site from your brain:

```bash
# Build the Quartz site
cd ~/brain-quartz
npx quartz build

# Serve locally
python3 -m http.server 8080 --directory public
```

Or publish via gbrain:
```bash
gbrain publish --output ~/public-brain
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `brain-compliance` | Page standards & validation |
| `brain-crosslinking` | Fix broken wikilinks & orphans |
| `department-scrum` | Cross-ref brain during scrum |
| `profile-enrichment` | Write enriched profiles to gbrain |