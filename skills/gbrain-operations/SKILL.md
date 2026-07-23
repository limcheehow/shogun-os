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

---

## Quick Reference

| Operation | Command | When |
|-----------|---------|------|
| Sync content | `gbrain sync` | After changing brain files |
| Generate embeddings | `gbrain embed` | After sync, to update vector search |
| Health check | `gbrain doctor` | Daily or when something feels wrong |
| Clean cycle | `gbrain dream` | Nightly maintenance |
| Serve MCP | `gbrain mcp` | For Hermes MCP connectivity |
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

**Embedding provider:** gbrain uses Backup Provider by default. Set `OPENROUTER_API_KEY` in the main `~/.hermes/.env`. To use a different provider:

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
hermes cron create "0 2 * * *" \
  --name "gbrain-dream-cycle" \
  --prompt "Run: cd /path/to/brain && gbrain dream" \
  --deliver local
```

### gbrain mcp (formerly gbrain serve)

Starts the MCP server for Hermes integration.

```bash
# Standard MCP serve
gbrain mcp

# With specific source
GBRAIN_SOURCE="hr" gbrain mcp

# With federated read
GBRAIN_FEDERATED_READ=true gbrain mcp
```

**Hermes config** (add to profile's `config.yaml` or `mcp_servers`):
```yaml
mcp_servers:
  gbrain:
    command: gbrain
    args: [mcp]
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

**Cause:** Backup Provider or embedding provider rate limits.

**Fix:**
```bash
# Slow down — embed in batches
gbrain embed --stale --batch-size 10

# Or switch provider
gbrain embed --provider openai

# Check quota:
curl -s https://backup-provider.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### gbrain MCP Connection Issues

**Symptom:** Hermes can't connect to gbrain MCP. `hermes mcp list` shows gbrain as disconnected.

**Troubleshooting:**
```bash
# 1. Is gbrain running?
ps aux | grep "gbrain mcp"

# 2. Start in foreground to see errors
gbrain mcp --verbose

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
hermes cron create "*/15 * * * *" \
  --name "brain-auto-sync" \
  --script brain-sync.sh \
  --no-agent \
  --deliver local
```

### Dream Cycle Cron

Nightly maintenance (runs on default profile):

```bash
hermes cron create "0 2 * * *" \
  --name "gbrain-dream-cycle" \
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

## Core Loop: Read → Enrich → Write


Every interaction with the brain follows this loop:

1. **Read** — search for existing pages, get page content, check timeline
2. **Enrich** — add new facts, update sections, fix errors, link entities
3. **Write** — put_page, add_link, add_timeline_entry, add_tag

## Sync Operations


### gbrain import — Large File Imports (Background Execution Required)

When importing thousands of files via `gbrain import <dir>/`, the operation can take **2+ hours**. The foreground terminal timeout (300s default) will kill it mid-import. Always run large imports in **background** with `notify_on_complete=true`.

**Pattern:**
```bash
# Run heavy import as background process
terminal(command="bash ~/.hermes/scripts/sync-personal-brain.sh", background=true, notify_on_complete=true, timeout=3600)
```

**Timing expectations** (real-world from sync-personal-brain.sh):
| Phase | Files | ~Time |
|-------|------:|------:|
| Companies | ~4,500 | 50-55 min |
| People | ~6,500 | 70-80 min |
| Deals | ~200 | 2-3 min |
| Meetings | ~40 | <1 min |
| Projects | ~7 | <1 min |
| Embeddings | varies | 15-30 min |
| **Total** | **~11,000** | **~2-2.5 hours** |

**Monitoring:** The log at the script's configured path (e.g. `~/.hermes/scripts/sync-personal-brain.log`) shows `[import.files] N/TOTAL (P%)` progress lines. Poll with `tail -1 <log>`.

See `references/sync-personal-brain.md` for the full sync-personal-brain script details (pipeline stages, config, runtime, log format).

**Pitfall:** Do NOT run large `gbrain import` in foreground — the 300s cap will SIGTERM it. Background with notify_on_complete is the only reliable pattern.

```bash
# Sync git repo → brain (incremental)
mcp_gbrain_sync_brain()                                   # incremental
mcp_gbrain_sync_brain(full=True)                          # full re-sync
mcp_gbrain_sync_brain(no_embed=True)                      # skip embedding generation
mcp_gbrain_sync_brain(dry_run=True)                       # preview changes
```

### Sync cadence
- **Brain repo (`~/brain/`)** — synced automatically by cron, or call `mcp_gbrain_sync_brain()` manually when you've made local edits
- **Marketing brain** — hourly 9am-6pm weekdays via `marketing-brain-sync` cron
- **Media/x/ chat** — markdown sources synced on write

## Brain Health


```bash
mcp_gbrain_get_health()       # Dashboard: embed coverage, stale pages, orphans
mcp_gbrain_run_doctor()       # Deep health check with auto-fix suggestions
mcp_gbrain_get_stats()        # Page count, chunk count, embeddings
```

### Health metrics to check
| Check | Tool | Action if bad |
|-------|------|---------------|
| Embed coverage | `get_health` → embed_coverage | Run `mcp_gbrain_submit_job(name="embed")` |
| Orphan pages | `get_health` → orphan_count | Use `mcp_gbrain_find_orphans()` then enrich |
| Stale pages | `get_health` → stale_count | Review and update old content |
| Sync drift | `sources_list` → status | Run full sync |

## Source Management


```bash
mcp_gbrain_sources_list()            # List all registered sources
mcp_gbrain_sources_status(id="...")  # Diagnostic per source
```

## Logging


After significant brain ops, log the event:
```bash
mcp_gbrain_log_ingest(
    source_type="sync",
    source_ref="manual",
    pages_updated=["page1", "page2"],
    summary="Synced brain repo — N pages updated"
)
```

## Engine Failure Recovery — PGLite WASM Crash


### Symptom

All gbrain operations (sync, autopilot, embed, dream cycle) fail with:
```
PGLite failed to initialize its WASM runtime.
  This is most commonly the macOS 26.3 WASM bug: https://github.com/garrytan/gbrain/issues/223
  Run `gbrain doctor` for a full diagnosis.
  Original error: Aborted(). Build with -sASSERTIONS for more info.
```

`gbrain doctor` will PASS (90/100) because it only does filesystem checks — it never actually opens PGLite. The real failure surfaces on any operation that touches the database.

### Diagnosis: In-Memory vs File-Backed Test

The key diagnostic is whether PGLite works in-memory but fails with the existing data directory:

```bash
cd ~/gbrain
export PATH="/home/your-company/.hermes/node/bin:$PATH"

# In-memory test (should work):
bun -e "
const { PGlite } = require('@electric-sql/pglite');
const db = new PGlite();
db.query('SELECT 1').then(r => console.log('OK:', JSON.stringify(r.rows))).catch(e => console.error('FAIL:', e.message));
"

# File-backed test (often fails after kernel upgrades):
bun -e "
const { PGlite } = require('@electric-sql/pglite');
const db = new PGlite('/path/to/.gbrain/brain.pglite');
db.query('SELECT 1').then(r => console.log('OK:', JSON.stringify(r.rows))).catch(e => console.error('FAIL:', e.message));
"
```

- **In-memory OK + file-backed FAIL** → data directory is corrupt or WASM-incompatible after a kernel/environment change (e.g. WSL2 upgrade). This is the most common pattern.
- **Both fail** → broader WASM runtime issue; check Node/Bun version and PGLite package version.
- **Both work** → the problem is upstream of PGLite (env vars, config, permission).

Also test with the newer `PGlite.create()` API that gbrain actually uses:
```bash
bun -e "
const { PGlite } = require('@electric-sql/pglite');
const { vector } = require('@electric-sql/pglite/vector');
PGlite.create({
  dataDir: '/path/to/.gbrain/brain.pglite',
  extensions: { vector }
}).then(db => db.query('SELECT 1')).then(r => console.log('OK')).catch(e => console.error('FAIL:', e.message));
"
```

Creating a **fresh** database in a temp directory should also work:
```bash
bun -e "
const { PGlite } = require('@electric-sql/pglite');
const db = new PGlite('/tmp/test-pglite');
db.query('CREATE TABLE IF NOT EXISTS test (id int); INSERT INTO test VALUES (42); SELECT * FROM test')
  .then(r => console.log('OK:', JSON.stringify(r.rows))).catch(e => console.error(e.message));
"
```

If a fresh DB works but the existing 488MB data dir doesn't, the data directory itself has a compatibility problem.

### Common Root Causes (WSL2 Context)

| Cause | Pattern | Recovery |
|-------|---------|----------|
| **WSL2 kernel upgrade** (e.g. 6.6.x → 6.18.x) | WASM memory mapping behavior changed. In-memory PGLite works, file-backed fails with Aborted(). | Migrate to native PostgreSQL in WSL (see `brain-database-migration` skill) |
| **Unclean PGLite shutdown** | WSL reboot while PGLite had open WAL. Stale `postmaster.pid` left behind. | Remove `postmaster.pid` and retry; if still fails, data dir may need re-init |
| **PGLite version mismatch** | PGLite WASM binary was updated but data dir was from an older PostgreSQL version | Check `~/.gbrain/brain.pglite/PG_VERSION` against what PGLite 0.4.x expects (PG17) |
| **filesystem/permission issue** | WSL 9P protocol can produce silent corruption on unclean unmount | Check `dmesg` for filesystem errors; try `fsck` on the WSL disk |

### Recovery Options

**Option A: Restore from backup** — If you have a state-snapshot or a gbrain backup, restore the data directory from before the kernel upgrade.

**Option B: Switch engine to native PostgreSQL** (recommended for WSL) — gbrain supports both PGLite and Postgres engines. Install PostgreSQL in WSL, create the schema, and point gbrain at it. See `brain-database-migration` skill and `references/pglite-wasm-crash-recovery.md`.

**Option C: Re-init PGLite from scratch** — Delete the corrupted data dir and re-sync from `~/brain/` files. Data is not permanently lost — gbrain's primary source is the file repo. But ALL embeddings must be regenerated (~1,000+ pages, dominated by embedding API latency).

### Migration Decision: PGLite vs PostgreSQL

| Factor | PGLite | PostgreSQL (local WSL) |
|--------|--------|----------------------|
| **Setup** | Zero config (bundled WASM) | `apt install postgresql` + DB creation |
| **Reliability** | Brittle — WASM runtime crashes after kernel upgrades, filesystem-level corruption | Native — proper MVCC, checkpointing, crash recovery |
| **Performance** | Single-threaded WASM, ~200-500ms queries | Multi-process native, ~10-50ms queries |
| **Disk usage** | 488MB for 1,097 pages + embeddings | Similar or better with proper shared_buffers |
| **Maintenance** | No service to manage | Requires `pg_ctl start/stop`, WAL management |
| **Kernel upgrade risk** | **HIGH** — WASM runtime behavior can change with kernel updates | **NONE** — PostgreSQL is a native kernel citizen |

**Recommendation for WSL:** If PGLite has failed once due to a kernel upgrade, migrate to local PostgreSQL. The migration cost (one-time re-embed) is far less than recurring outage recovery.

## Setting up git-synced content directories in the brain


The brain's `projects/` directory (and other subdirectories) can host content that syncs **bidirectionally** with an external git repo, while local-only directories coexist alongside. This is distinct from the gbrain MCP sync — it's about syncing raw files, not embedding them into the knowledge base.

**Use case:** When an external team maintains structured data (project plans, tickets, customer profiles) in a GitHub repo and the agent needs local read/write access.

### Setup pattern

1. **Clone the repo** into a temp location, then `rsync --exclude='.git'` the contents into the target brain subdirectory
2. **Init git** in the target dir and set the remote
3. **Create a `.gitignore`** with negation patterns to keep local-only dirs out of git:
   ```
   /*
   !/tracked-dir-1/
   !/tracked-dir-2/
   !.gitignore
   ```
   Any directory not explicitly un-ignored stays local-only.
4. **Create a sync script** at `~/.hermes/scripts/<name>.sh` that:
   - Fetches remote state
   - Commits local changes with auto-message
   - Pulls with rebase (layers local on top of remote)
   - Pushes to remote
   - On conflict: aborts rebase and exits with error
5. **Create a cron job** to run the script on schedule

### Key decisions

| Choice | Why |
|--------|-----|
| Standalone git (not submodule) | Submodules require the parent brain repo to track the ref, adding fragility. A nested independent repo is simpler. |
| Pull with rebase (not merge) | Keeps history linear — local commits sit on top of remote commits, avoiding merge bubbles. |
| Script in `~/.hermes/scripts/` | Cron jobs can reference it by filename (no path prefix needed). |
| `deliver: local` on the cron job | Silent on success, no Telegram spam. Conflict reports are the only alert. |

### Sync script template

See `references/git-synced-directory.md` for the full script template and `.gitignore` pattern used in production.

## Pitfalls


- ❌ Running full sync when incremental would do (slower, wastes embeddings)
- ❌ Ignoring health warnings about stale pages
- ❌ Not logging significant brain operations
- ❌ Confusing brain-ops sync with git operations on the local ~/brain/ repo
- ❌ Using `git pull` (merge) instead of `git pull --rebase` for two-way sync — merge commits clutter history
- ❌ Forgetting a `.gitignore` with `/*` negation — the parent brain repo's `.gitignore` won't hide local-only subdirs from the nested repo
- ❌ Assuming `gbrain doctor` detects database issues — it only does filesystem checks and will report 90/100 even when PGLite is broken
- ❌ Treating WSL2 kernel upgrades as transparent — they can break PGLite's WASM runtime for existing persistent databases (in-memory works, file-backed fails)
- ❌ Letting stale `postmaster.pid` linger after a WSL reboot — always check and remove it before diagnosing PGLite failures
- ❌ Migrating from PGLite to Postgres without first verifying that the data source (`~/brain/` files) is in good shape — gbrain re-syncs from files, not the DB
- ❌ Waiting for PGLite failures to accumulate before migrating to native PostgreSQL — the migration cost is the same whether you do it proactively or after the second crash
- ❌ Assuming `gbrain doctor` detects schema migration blocks — doctor reports 90/100 even when 66+ schema migrations are pending due to missing user privileges
- ❌ Relying on cron's minimal PATH to find `gbrain` from shell wrappers — cron's default PATH (`/usr/bin:/bin`) does not include `~/.local/bin`. The autopilot cron runs every 5 minutes and silently loops: "Could not resolve the gbrain CLI path." Fix: the gbrain wrapper at `~/.local/bin/gbrain` must prepend `~/.local/bin` to PATH, and autopilot-run.sh must be self-contained (no shell profile sourcing)
- ❌ Running `gbrain import` without first ensuring schema migrations are clean — importing 300+ files with a stuck schema migration (e.g., v24 BYPASSRLS) causes the import to hang indefinitely (0 CPU, idle Postgres connections). Kill the import (`kill <pid>`), fix the DB privileges, migrate, then re-run import
- ❌ Cron autopilot failing silently for weeks due to missing `~/.local/bin` on PATH — the `gbrain` wrapper (`~/.local/bin/gbrain`) must export `PATH="/home/your-company/.local/bin:$PATH"` so `which gbrain` resolves inside autopilot's worker spawns. The `autopilot-run.sh` script must also be self-contained (no reliance on `.zshrc`/`.bashrc` sourcing). Symptom: `Could not resolve the gbrain CLI path` repeated in `~/.gbrain/autopilot.log` with 18,000+ lines of the same error.
- ❌ Postgres `hermes` user lacking BYPASSRLS + SUPERUSER — the gbrain schema migration (v24 rls_backfill_missing_tables) requires both. Without them, autopilot starts but stalls on initSchema(). Fix: `sudo -u postgres psql -c "ALTER USER hermes WITH BYPASSRLS SUPERUSER;"` then `gbrain init --migrate-only`
- ❌ **Autopilot silently failing with `Could not resolve the gbrain CLI path`** — gbrain's autopilot uses `which gbrain` to spawn workers. In cron's minimal environment, `~/.local/bin` is not on `$PATH`. Fix: ensure the `gbrain` wrapper script (at `~/.local/bin/gbrain`) and the autopilot cron script (`~/.gbrain/autopilot-run.sh`) both export `PATH="/home/your-company/.local/bin:...:$PATH"`. Do NOT rely on sourcing `~/.bashrc`/`~/.zshrc` in cron — those profiles may not work in non-interactive mode. Symptom: 18,000+ log lines of identical failures with zero successful runs. Verify fix: `tail -5 ~/.gbrain/autopilot.log` should show dream-cycle phases, not CLI-path errors. Also clear stale lock files (`~/.gbrain/autopilot.lock`) and kill stuck autopilot processes before the fix takes effect.

## Related Skills

| Skill | Purpose |
|-------|---------|
| `brain-compliance` | Page standards & validation |
| `brain-crosslinking` | Fix broken wikilinks & orphans |
| `department-scrum` | Cross-ref brain during scrum |
| `profile-enrichment` | Write enriched profiles to gbrain |