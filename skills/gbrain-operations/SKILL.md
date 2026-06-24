---
name: gbrain-operations
version: 1.7.0
description: |
  GBrain operations: sync, embed, doctor, lock management, dream cycle,
  schema packs, brainstorm, autopilot, publish, capture, Supabase
  DB connection recovery, MCP server setup, brain-first lookup via
  Supabase REST, signal capture via filesystem, and the gbrain think
  subsystem. Covers running gbrain CLI commands with the correct
  environment variables (OpenRouter for embeddings), clearing stale
  database locks, Python wrapper for reliable API key injection,
  and troubleshooting common issues including PGLite lock contention
  and Supabase auto-pause.
triggers:
  - "brain site"
  - "brain website"
  - "browse brain"
  - "web ui"
  - "brain page viewer"
  - "gbrain web ui"
  - "gbrain serve"
  - "gbrain sync"
  - "gbrain embed"
  - "gbrain doctor"
  - "gbrain dream"
  - "gbrain schema"
  - "gbrain brainstorm"
  - "gbrain capture"
  - "gbrain publish"
  - "gbrain autopilot"
  - "gbrain sources status"
  - "gbrain features"
  - "gbrain report"
  - "gbrain integrations"
  - "brain sync"
  - "meeting notes sync"
  - "15 min sync"
  - "gbrain sync cron"
  - "incremental sync"
  - "gbrain-sync.sh"
  - "stale lock"
  - "sync lock"
  - "embedding failed"
  - "429 quota"
  - "openrouter embedding"
  - "pglite sync"
  - "dream synthesize"
  - "dream synthesis"
  - "meeting transcript synthesize"
  - "dream synthesize setup"
  - "openrouter anthropic proxy"
  - "anthropic sdk double-path"
  - "dream cycle setup"
  - "gbrain dream dry-run"
  - "gbrain dream --phase"
  - "brain.dir config"
  - "gbrain dream timeout"
  - "pglite corruption"
  - "pglite recovery"
  - "brain.pglite corrupted"
  - "Aborted() pglite"
  - "WASM runtime pglite"
  - "postmaster.pid -42"
  - "gbrain doctor connection failed"
  - "supabase paused"
  - "supabase auto-pause"
  - "supabase rest api"
  - "supabase already configured"
  - "supabase existing data"
  - "supabase pages count"
  - "reuse existing supabase"
  - "switch to supabase from pglite"
  - "pglite dead supabase alive"
  - "pglite corruption multiple times"
  - "chronic pglite corruption"
  - "migrate away from pglite"
  - "gbrain init fails aborted"
  - "supabase-sync-v2.py"
  - "supabase-watcher.py"
  - "supabase-full-sync.sh"
  - "supabase-brain-sync"
  - "cron job supabase-brain-sync"
  - "rest api sync"
  - "config.json password corruption"
  - "migrate --to supabase"
  - "pglite to postgres"
  - "migrate url format"
  - "user:@host"
  - "bun postgres url parsing"
  - "migration completed"
  - "pglite to postgres success"
  - "supabase pooler tenant not found"
  - "supabase free tier ipv6 only"
  - "supabase pooler requires pro"
  - "gbrain vs crm separate databases"
  - "pglite stable after lock fix"
  - "pglite postmaster.pid keeps reappearing"
  - "autopilot install"
  - "autopilot not installed"
  - "autopilot status"
  - "autopilot failed"
  - "autopilot exit code 127"
  - "systemd user service"
  - "gbrain wrapper"
  - ".local/bin/gbrain"
  - "pglite fallback"
  - "pglite recovery"
  - "switch to pglite"
  - "gbrain init"
  - "drive ingestion"
  - "drive folder to brain"
  - "document ingestion"
  - "meeting notes sync"
  - "config show pglite crash"
  - "config list no output"
  - "classifyPgliteInitError"
  - "postmaster.pid cleanup"
  - "pglite lock stolen"
  - "usage gap"
  - "what's not running"
  - "how much of gbrain"
  - "brain site password"
  - "brain page password"
  - "what's my password"
  - "gbrain audit"
  - "site password"
  - "brain score"
  - "brain-auth-proxy"
  - "BRAIN_PASS"
  - "encrypted-pages"
  - "brain-query"
  - "brain-capture"
  - "brain-think"
  - "gbrain-runner.py"
  - "python wrapper"
  - "gbrain mcp"
  - "gbrain serve"
  - "mcp server"
  - "gbrain mcp server"
  - "serve --http"
  - "brain-first lookup"
  - "signal detector"
  - "signal capture"
  - "ambient capture"
  - "shell escaping"
  - "stale lock sigterm"
  - "brain-first scripts"
  - "pglite vs supabase"
  - "why pglite"
tools:
  - terminal
  - file
mutating: true
---

# GBrain Operations

## Contract

This skill guarantees:
- gbrain commands are run from `~/gbrain/` directory using `bun run src/cli.ts <command>` (not a `gbrain` binary)
- Embeddings use **OpenRouter** as the preferred provider when `OPENROUTER_API_KEY` is available
- The `OPENAI_API_KEY` env var is exhausted (429 quota) — only suitable for keyword search, NOT for embeddings

## Engine Decision Framework

This user (CH) has **two separate data systems** using the same Supabase project. The brain data is synced to Supabase via REST API every 15 min for **read-only queries** — this is NOT the gbrain engine:

| Layer | Engine | What it stores | Connection | Status | Read/Write | Use for |
|-------|--------|----------------|------------|--------|------------|---------|
| **gbrain engine** | Postgres 16 + pgvector (local) | Brain knowledge graph, embeddings, symbolic edges, pattern memory, page links, timeline | `postgresql://gbrain@127.0.0.1:5432/gbrain` — trust auth, no password. Local Postgres on WSL. | 🟢 Running, autopilot stable | Read + Write | Search, think, extract, embed, dream cycle, graph, timeline, everything gbrain |
| **Brain → Supabase Sync** | REST API (HTTPS) | Pages table + content_chunks with embeddings (flat copy) | `supabase-sync-v2.py` runs every 15 min via cron. Always available, no lock contention. | 🟢 Live — incremental, 20K+ files, ~2s incremental run | Read-only | Brain-first lookup (brain-query.sh), CRM queries, Hermes brain lookups |

**⚠️ Key confusion point:** The Supabase sync puts brain data INTO Supabase, but gbrain reads from PGLite, NOT Supabase. You cannot query gbrain's link graph, timeline, think, or entity extraction through the Supabase REST API — it only has flat pages + embeddings. The two are independent pipelines sharing the same source (`~/brain/` markdown files).

### Can gbrain use Supabase as engine?

| Path | Works? | Why |
|------|--------|-----|
| Direct Postgres via `db.*.supabase.co:5432` | ❌ | IPv6-only. WSL has no global IPv6 address. |
| Supabase pooler via `aws-0-*-*.pooler.supabase.com:6543` | ❌ | Pooler requires a **Pro plan** (paid). Free tier returns: `FATAL: Tenant or user not found` |
| Supabase REST API as engine replacement | ❌ | gbrain needs pgvector, schema migrations, complex joins, transactions — REST is CRUD-only |
| Local Postgres on WSL (apt install postgresql-16-pgvector) | ✅ Fully migrated | All **27,471 pages** transferred with 100% embedding coverage (schema v92). Postgres 16 + pgvector running locally on WSL, **trust auth on 127.0.0.1** for user `gbrain` (no password needed). Config auto-updated to `engine: postgres` after migration. See `references/local-postgres-migration.md`. |
| PGLite (current) | ✅ | Works after lock fixes. Stable for autopilot. Fragile on crash/WAL corruption. |

**Bottom line:** If PGLite keeps corrupting, the best upgrade is **local Postgres on WSL** (requires sudo apt install), not Supabase remote. The REST sync to Supabase is a parallel data pipeline, not an engine replacement.

### Synptom: Pooler "Tenant or user not found"

When connecting to `aws-0-*-*.pooler.supabase.com:6543` with the correct credentials:
```
FATAL: Tenant or user not found
```
This means the **Supabase project is on the free tier** — the connection pooler is a Pro-plan feature. There is no alternative username format that bypasses this. The only direct Postgres option is via IPv6 (which requires a global IPv6 address on the client).

## Core Setup

### API Keys for Embeddings

gbrain embeds chunks using `text-embedding-3-large` via its embedding service (`src/core/embedding.ts`).

**Key priority in the code:**
1. If `OPENROUTER_API_KEY` is set → uses OpenRouter (`baseURL: 'https://openrouter.ai/api/v1'`)
2. Else → falls back to direct OpenAI (reads `OPENAI_API_KEY` from env)

**Critical: `OPENAI_API_KEY` is the one with the exhausted quota (429).** Never run `gbrain sync` or `gbrain embed` without the OpenRouter key.

### Where keys are stored

| Key | Location | Status |
|---|---|---|
| `OPENAI_API_KEY` | `~/.bashrc` (exported) | Exhausted quota — 429 errors |
| `OPENROUTER_API_KEY` | `~/.hermes/.env` (NOT exported) | Working — use for all gbrain operations |

Since `OPENROUTER_API_KEY` is NOT in the environment by default, you MUST pass it explicitly when running gbrain commands.

### Permanent gbrain Wrapper (recommended)

Instead of passing env vars every time, create a permanent wrapper on PATH that injects OpenRouter credentials. This is essential for systemd daemons (autopilot) which have a stripped environment:

```bash
# File: ~/.local/bin/gbrain
#!/bin/bash
export PATH="/home/cheehow/.local/bin:/home/cheehow/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
OP_KEY=$(grep -m1 '^OPENROUTER_API_KEY=*** /home/cheehow/.hermes/.env | cut -d= -f2-)
AN_KEY=$(grep -m1 '^ANTHROPIC_API_KEY=*** /home/cheehow/.hermes/.env | cut -d= -f2-)
exec env \
  OPENROUTER_API_KEY=*** \
  OPENAI_API_KEY=*** \
  ANTHROPIC_API_KEY=*** \
  OPENAI_BASE_URL="https://openrouter.ai/api/v1" \
  /home/cheehow/.npm-global/bin/bun run /home/cheehow/gbrain/src/cli.ts "$@"
```

> **Critical: Wrapper must pass BOTH `OPENROUTER_API_KEY` and `OPENAI_API_KEY`.** \
> gbrain v0.40+ reads `OPENROUTER_API_KEY` directly for embedding auth. \
> The old wrapper only set `OPENAI_API_KEY="$OPENROUTER_KEY"` which caused \
> **"Missing Authentication header"** on every embedding when run via the wrapper \
> (including autopilot). Either set both, or verify with:
> ```bash
> gbrain embed --stale 2>&1 | grep -c "Missing Authentication header"
> ```
> Should be 0 after the fix.

Make executable and verify:
```bash
chmod +x ~/.local/bin/gbrain
which gbrain             # must show ~/.local/bin/gbrain
gbrain doctor | head -5  # test it works
```

> **Important:** systemd user services run with `$PATH` limited to `/usr/local/bin:/usr/bin:/bin`. The `~/.npm-global/bin` directory is NOT on the systemd PATH. The wrapper above hardcodes absolute paths to `bun` and `src/cli.ts` so it works from systemd context.
>
> The autopilot `autopilot-run.sh` script generated by `gbrain autopilot --install` also needs manual PATH hardening — add an absolute export PATH at the top of the script after the `source` lines.

## PGLite Issues & Fixes (v0.40.8.1+)

Summary of the fix wave applied to this install:

### Fix 1: `config show` no longer triggers PGLite WASM init

`gbrain config show` and `gbrain config list` only read `~/.gbrain/config.json` (a text file). They used to go through `connectEngine()` which spins up PGLite's WASM runtime — crashing unnecessarily when the DB is corrupted.

**Fix** (`src/cli.ts`): Short-circuited before `connectEngine()` for `config show`/`config list`. These commands now execute instantly from the file system with a stub engine. No WASM init needed.

### Fix 2: Error messages are now platform-aware

The old catch-all: *"This is most commonly the macOS 26.3 WASM bug"* — even on Linux.

**Fix** (`src/core/pglite-engine.ts`): Added `classifyPgliteInitError()` and `buildPgliteInitErrorMessage()` — three verdict classes:
- **`bunfs`** → Bun VFS bundling bug (compiled binary missing `pglite.data`)
- **`stale-state`** → postmaster/WAL corruption from previous crash
- **`unknown`** → macOS 26.3 bug / generic fallback

### Fix 3: Stale `postmaster.pid` auto-cleaned on connect

When PGLite's embedded Postgres crashes, it leaves behind `postmaster.pid` with a dead PID. The next startup tries to bind to the stale PID and crashes again.

**Fix** (`src/core/pglite-engine.ts`): Added pre-connect cleanup in `PGLiteEngine.connect()` — checks for `postmaster.pid` with a dead PID and removes it before spinning up WASM. Cleans up orphaned lock directories too. Best-effort — never blocks connect.

### Fix 4: Lock stale threshold raised from 5 min to 120 min

The old 5-minute `STALE_THRESHOLD_MS` in `pglite-lock.ts` killed the autopilot's lock on long-running cycles. A second process would steal the lock from the live autopilot → two processes access PGLite simultaneously → `Aborted()`.

**Fix** (`src/core/pglite-lock.ts`): Raised threshold to 120 min. Primary stale-detection is PID-aliveness (instant and correct). Time-based fallback now only fires for processes truly stuck for 2+ hours.

### Fix 5: `gbrain config list` now works (was silent no-op)

`config list` wasn't a recognized subcommand — it silently returned with no output.

**Fix** (`src/cli.ts`): Mapped `list` → `show` action so `gbrain config list` shows the config file.

## Running Sync

### Pre-flight: Check source has a local_path

The "default" source **must have `local_path` set** or sync silently does nothing.
It shows "Already up to date" without importing anything.

**Check:**
```bash
cd ~/gbrain && bun run src/cli.ts sources list --json
```
If `local_path` is `null`, set it via:
```bash
cd ~/gbrain && bun run src/cli.ts sources add default --path ~/brain
```
If the `add` command fails with `"cannot remove the default source"`, the existing
record needs a direct SQL update (for Postgres engine):
```bash
cd ~/gbrain && bun -e '
const {Pool} = await import("pg");
const cfg = JSON.parse(await Bun.file(process.env.HOME+"/.gbrain/config.json").text());
const pool = new Pool({connectionString: cfg.database_url});
await pool.query("UPDATE sources SET local_path=$1 WHERE id=$2", [process.env.HOME+"/brain", "default"]);
const r = await pool.query("SELECT id, local_path FROM sources");
console.log("Updated:", JSON.stringify(r.rows));
await pool.end();
'
```

### Pre-sync: Check for sync failures first

Run `gbrain doctor` before sync — it may flag sync failures that block subsequent syncs:

```
cd ~/gbrain && bun run src/cli.ts doctor 2>&1 | grep sync_failure
```

If it shows `sync_failures: N unacknowledged sync failure(s)`, pass `--skip-failed` to bypass the broken files and let the rest proceed. The failed files remain logged in `~/.gbrain/sync-failures.jsonl` for later investigation.

### Post-Supabase sync (no embedding env vars needed)

After migration to Supabase (Postgres engine), the database URL is stored in
`~/.gbrain/config.json` and embeddings are handled by pgvector. Sync is simpler:

```bash
cd ~/gbrain && bun run src/cli.ts sync --repo ~/brain
```

No `OPENROUTER_API_KEY` or `OPENAI_API_KEY` gymnastics needed — the config
already points to the postgres engine which has pgvector built in.

### Correct command for PGLite engine (with OpenRouter embeddings + repo flag):

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  bun run src/cli.ts sync --repo ~/brain
```

> **Notes:**
> - `--repo ~/brain` is **always required** — sync refuses to run without it regardless of config
> - Use `grep -m1 '^OPENROUTER_API_KEY='` (with `^` anchor) to skip any commented-out lines
> - Pass `--skip-failed` if `gbrain doctor` reports unacknowledged sync failures

### Sync output format

The sync command produces real-time progress lines in this format:

```
[import.files] NNNNN/18285 (XX%) imported=NNNNN skipped=NNNNN errors=0
```

Where:
- `NNNNN/18285` — files scanned so far / total files found
- `imported=NNNNN` — files newly imported to the database
- `skipped=NNNNN` — files already in DB and unchanged
- `errors=0` — files that failed to import

At completion:

```
[import.files] 18285/18285 (100%) done

Import complete (6939.7s):
  16560 pages imported
  1725 pages skipped (1725 unchanged, 0 errors)
  16883 chunks created
Embedded 0 chunks (0 stale found)
First sync complete. Checkpoint: a701527d
  16560 file(s) imported, 16883 chunks, 16560 pages embedded
```

The **checkpoint hash** is a commit-like identifier for the sync batch. The **skipped** count represents files already present in the DB from a previous sync.

### For large syncs (5000+ files), run in background:

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  bun run src/cli.ts sync --repo ~/brain --skip-failed &
```

Expected duration: ~30-60 seconds per ~100 files (varies with embedding rate limits). For 15,000+ files, expect 1-3 hours.

### Sync outputs:

- Pages get added to the PGLite database (count visible via `gbrain doctor`)
- Embedding failures show as `[gbrain] embedding failed for <page> (N chunks): 429 ...`
- The page IS still imported to the DB even if embedding fails — only vector search is unavailable

## Running Doctor

```bash
cd ~/gbrain && bun run src/cli.ts doctor
```

Health checks include: resolver, skills, connection (page count), pgvector, embeddings, graph coverage, brain score, integrity.

Use `bun run src/cli.ts doctor --fix` to auto-fix fixable issues.

### Preview Remediation Plan (no side effects)

Run this before `--remediate` to see what steps will be taken and the max reachable score:

```bash
cd ~/gbrain && gbrain doctor --remediation-plan --json
```

Output shows a dependency-ordered plan with per-step estimates and a `max_reachable_score` ceiling. If the target score is above this ceiling (typically ~70 with PGLite content constraints), `--remediate` will bail immediately with `"target 90 unreachable; max autonomous = 70/100"` — the remaining 30 points need manually authored content (cross-links, frontmatter timeline dates).

### Verify Link/Timeline/Page Counts Directly

```bash
cd ~/gbrain && bun -e '
const{PGlite}=await import("@electric-sql/pglite");
const db=await PGlite.create(process.env.HOME+"/.gbrain/brain.pglite");
const r1=await db.query("SELECT COUNT(*) as count FROM links");
const r2=await db.query("SELECT COUNT(*) as count FROM timeline_entries");
const r3=await db.query("SELECT COUNT(*) as count FROM pages");
console.log("Links:", JSON.stringify(r1.rows[0].count));
console.log("Timeline:", JSON.stringify(r2.rows[0].count));
console.log("Pages:", JSON.stringify(r3.rows[0].count));
await db.close();
'
```

### Stop Autopilot Before Remediate

`gbrain doctor --remediate` needs exclusive PGLite access. If autopilot is running, the remediate command times out. Always stop it first:

```bash
systemctl --user stop gbrain-autopilot.service
# ... run gbrain doctor --remediate ...
systemctl --user start gbrain-autopilot.service
```

## PGLite Database Corruption Recovery

When PGLite's WASM postmaster crashes on startup with `Aborted()`, the database at `~/.gbrain/brain.pglite/` is likely corrupted (stale `postmaster.pid` with PID `-42`, unrecoverable WAL segments).

**Symptom:** `gbrain doctor` shows `[WARN] connection: Could not connect to configured DB` while pure filesystem checks pass. Direct `PGlite.create()` also fails with `Aborted()`, but a fresh/empty PGLite works fine.

**v0.40.8.1 improvement:** The stale `postmaster.pid` auto-cleanup (Fix 3) now handles the *common* case — when the PID is from a dead process, it's removed before WASM init. If the crash also corrupted WAL segments, this alone won't fix it; full recovery is still needed.

**ALL gbrain commands that touch the DB fail uniformly** — `gbrain sync`, `gbrain embed`, `gbrain init`, `gbrain doctor` all report the same `Aborted()` error. A cron job claiming "sync is in progress" while PGLite is dead is inaccurate — the daemon was in a death-spiral restart loop, not actually syncing. Always verify with a direct `gbrain doctor` call before trusting status output.

**Root cause:** Process killed ungracefully during sync, dream cycle, or embed — killed processes leave the postmaster.pid with PID `-42`, and the WAL can't be replayed on the next startup.

**No data loss:** The brain markdown files in `~/brain` are the source of truth. PGLite is just the search/embedding index.

**If this is the 2nd+ corruption event, prefer Supabase migration over local recovery.** This user (CH) has had 3 corruption events (May 15, 17, 28). PGLite's WASM runtime (`@electric-sql/pglite`) has a known instability on Linux/WSL when processes are killed — it's a design limitation, not a fluke. Each local recovery takes hours (re-sync of ~18K+ files). If a Supabase project already exists with gbrain schema, switching to it is far faster.

See `references/pglite-corruption-recovery.md` for the full step-by-step procedure.

### Quick Recovery Steps

1. **Backup corrupted DB:**
   ```bash
   mv ~/.gbrain/brain.pglite ~/.gbrain/brain.pglite.corrupted-$(date +%Y%m%d)
   ```

2. **Create fresh DB:**
   ```bash
   cd ~/gbrain && bun run src/cli.ts init
   ```

3. **Set source local_path** (fresh init leaves it null):
   ```bash
   cd ~/gbrain && bun -e '\nconst{PGlite}=await import("@electric-sql/pglite");\nconst db=await PGlite.create(process.env.HOME+"/.gbrain/brain.pglite");\nawait db.query("UPDATE sources SET local_path=$1 WHERE id=$2",[process.env.HOME+"/brain","default"]);\nawait db.close();\n'
   ```

4. **Re-sync all pages** (requires `--repo` flag; add `--skip-failed` if known FK violations):
   ```bash
   cd ~/gbrain && \
     OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
     OPENAI_API_KEY="" \
     bun run src/cli.ts sync --repo ~/brain
   ```

   For 10,000+ files, run in background — expect 2-3 hours at ~1-2 files/sec. Monitor via `process` poll or check `~/.gbrain/sync-failures.jsonl`.

5. **Re-embed and verify:**
   ```bash
   bun run src/cli.ts embed --stale && bun run src/cli.ts doctor
   ```

## Clearing Stale Cycle or Sync Locks (Postgres/Supabase)

### Symptom

When `bun run src/cli.ts sync` fails with:

```
Another sync is in progress (lock gbrain-sync held). Wait for it to finish, or run 'gbrain doctor' if it has been more than 30 minutes.
```

Or when `bun run src/cli.ts dream` fails with:

```
"cycle_already_running"
```

Even after the original process has died or timed out.

### Fix (Postgres)

Use Python with psycopg2 to inspect and clear stale locks directly:

```bash
# Check current locks
/usr/bin/python3 -c "
import psycopg2, json
cfg = json.load(open('/home/cheehow/.gbrain/config.json'))
conn = psycopg2.connect(cfg['database_url'], sslmode='require')
cur = conn.cursor()
cur.execute('SELECT * FROM gbrain_cycle_locks')
locks = cur.fetchall()
print(locks)
cur.close(); conn.close()
"

# Clear ALL locks (safe — only blocks concurrent syncs)
/usr/bin/python3 -c "
import psycopg2, json
cfg = json.load(open('/home/cheehow/.gbrain/config.json'))
conn = psycopg2.connect(cfg['database_url'], sslmode='require')
cur = conn.cursor()
cur.execute('DELETE FROM gbrain_cycle_locks')
print(f'Cleared {cur.rowcount} lock(s)')
conn.commit()
cur.close(); conn.close()
"

# Clear only expired locks (for automated scripts)
/usr/bin/python3 -c "
import psycopg2, json
cfg = json.load(open('/home/cheehow/.gbrain/config.json'))
conn = psycopg2.connect(cfg['database_url'], sslmode='require')
cur = conn.cursor()
cur.execute(\"DELETE FROM gbrain_cycle_locks WHERE ttl_expires_at < now() - interval '30 minutes'\")
print(f'Cleared {cur.rowcount} stale lock(s)')
conn.commit()
cur.close(); conn.close()
"
```

### Lock Table Schema (Postgres)

The `gbrain_cycle_locks` table has these columns:

| Column | Type | Description |
|---|---|---|
| `id` | TEXT | Lock name: `gbrain-sync` or `gbrain-cycle` |
| `holder_pid` | INTEGER | PID of the process holding the lock |
| `holder_host` | TEXT | Hostname of the process |
| `acquired_at` | TIMESTAMPTZ | When the lock was acquired |
| `ttl_expires_at` | TIMESTAMPTZ | When the lock auto-expires (usually 30 min) |

Note: There is **no** `lock_type` column in Postgres — the lock name is stored in `id`. The old PGLite-based lock commands using `PGlite.create()` are obsolete.

### Lock details

- **TTL:** 30 minutes (auto-expires, but the lock blocks new syncs/cycles until it does)
- **Cause:** Process timed out or crashed without calling release
- **Distinction:** `gbrain-sync` locks block sync commands; `gbrain-cycle` locks block dream cycle commands. Generic `DELETE FROM gbrain_cycle_locks` clears both safely.

### ⚠️ Critical: DB lock does NOT check PID liveness (unlike PGLite file lock)

The Postgres-backed lock (`tryAcquireDbLock`) only checks if `ttl_expires_at < NOW()` — it does **not** verify whether the holder PID is still alive on the system. The PGLite file lock (`acquireFileLock`) does check `process.kill(pid, 0)` — but the DB lock has no equivalent.

**Consequence:** If a dream, sync, or embed process crashes (SIGTERM/timeout/out-of-memory), its lock row persists in `gbrain_cycle_locks` blocking new operations for the full 30-minute TTL. All subsequent attempts report `cycle_already_running` even though no process is active.

**Diagnosis:**

```bash
# Check what locks exist and who holds them
psql -h localhost -U gbrain -d gbrain -c "SELECT * FROM gbrain_cycle_locks;"

# Check if the holder PID is actually alive
ps aux | grep <holder_pid>
```

**Manual fix (delete only the dead PID's lock):**

```bash
psql -h localhost -U gbrain -d gbrain \
  -c "DELETE FROM gbrain_cycle_locks WHERE id = 'gbrain-cycle' AND holder_pid = <dead-pid>;"
```

**Automated fix 🟢 (preferred — safe to run from cron):**

Use a conditional lock-cleanup that only deletes rows whose TTL has NOT expired but whose holder PID is no longer alive:

```
psql -h localhost -U gbrain -d gbrain -c "
DELETE FROM gbrain_cycle_locks l
WHERE l.ttl_expires_at > NOW()
  AND NOT EXISTS (
    SELECT 1 FROM pg_stat_activity a
    WHERE a.pid = l.holder_pid
  );
"
```

This targets only stale locks from dead processes, leaving live locks untouched.

## Incremental Sync Cron (Every 15 Minutes)

The brain syncs to both gbrain PGLite AND to Supabase REST API every 15 minutes.

### Supabase REST Sync (no_agent style)
A Python script at `~/.hermes/scripts/supabase-sync-v2.py` reads `~/brain/` markdown files,
chunks and embeds them via OpenRouter (text-embedding-3-large, 1536d), and upserts to
Supabase's `pages` and `content_chunks` tables via PostgREST.

**Hash-cache incremental:** A JSON cache at `~/.gbrain/supabase-hash-cache.json` tracks
`{slug: {mtime, size, hash}}` — files matching cached mtime+size are skipped entirely.
Typical incremental run: ~2 seconds for 20K files. Full re-sync: `rm -f ~/.gbrain/supabase-hash-cache.json`.

**Cron job:** `supabase-brain-sync` — runs every 15 minutes, delivers to `local` (silent when nothing changed, alerts on failure).

**Wrapper script:** `~/.hermes/scripts/supabase-full-sync.sh` (add `--full` flag to reset cache)

**Manual run (uses CRM_* vars with fallback chain — see `nextjs-supabase-dashboard` skill for the full multi-agent migration pattern):**
```bash
CRM_SUPABASE_SERVICE_KEY="your-key" CRM_SUPABASE_ANON_KEY="your-anon" \
  python3 ~/.hermes/scripts/supabase-sync-v2.py

# Or rely on the .env.local extraction (checks CRM_SUPABASE_SERVICE_KEY first)
CRM_ENV="$HOME/crm-dashboard/.env.local" python3 ~/.hermes/scripts/supabase-sync-v2.py
```

See `references/supabase-rest-api.md` for full documentation including gotchas (409 trigger noise, batch key uniformity, on_conflict parameter).

### gbrain PGLite Sync (no_agent style)
1. **Clears stale locks** older than 30 min (prevents lock build-up)
2. **Runs gbrain sync** with `--skip-failed` to bypass broken files
3. **Reports only meaningful events** — silent when nothing changed, noisy on failure

### Cron Setup

```bash
# View the job
cronjob action=list | grep gbrain-sync

# The job runs: */15 * * * *
# With: no_agent=true, script=gbrain-sync.sh
```

**Delivery semantics** (no_agent mode):
- Empty stdout → silent (nothing changed — healthy)
- Non-empty stdout → message delivered ("N new files imported" or error)
- Non-zero exit → error alert sent

### How It Works

```bash
# The wrapper script lives at:
/usr/bin/python3 /home/cheehow/.hermes/scripts/gbrain-sync.sh

# Which calls:
cd ~/gbrain && bun run src/cli.ts sync --repo ~/brain
```

The initial sync takes ~5-10 minutes for 18K+ files. Subsequent incremental syncs are faster as only changed files need re-importing. The lock mechanism prevents concurrent syncs from running simultaneously.

### Note

The Daily Dream Cycle cron (2 AM) also runs sync as part of its `lint → backlinks → sync → synthesize → ...` pipeline. The 15-min sync cron ensures the database is fresh between dream cycles, so CRM queries against Supabase always return current data.

### ⚠️ Multi-Agent Supabase Env Var Isolation

**Risk:** Multiple profiles (`default`, `coding-agent`) and the CRM dashboard all export `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` — if a second agent uses a different Supabase project, bare names clash.

**Current state (this WSL):** All configs point to `acfctcmxnfipihrdauxj.supabase.co`. Remote agents may differ.

**Isolation strategies (if two Supabase projects coexist):**

1. **Unique env var names per agent** — `BRAIN_SUPABASE_URL` vs `CRM_SUPABASE_URL`. Prevents accidental cross-write from wrong shell context.

2. **Profile isolation** — Each profile `.env` defines `SUPABASE_*` for its own project. Scripts launched within a profile context stay isolated.

3. **`source_id` per agent** — The script hardcodes `source_id: "default"`. Add `SOURCE_ID` env var override:
   ```python
   SOURCE_ID = os.environ.get("SOURCE_ID", "default")
   ```

**Pitfall — stale Windows cron path:** The supabase-brain-sync cron's last error: `Script timed out after 120s: /mnt/c/Users/cheeh/.hermes-windows/scripts/supabase-sync-v2.py`. On a remote Linux host (Azure), `/mnt/c/` doesn't exist. **Fix:** Update the cron job to remove the stale `script` field or point to the local `~/.hermes/scripts/supabase-sync-v2.py`.

**Pitfall — `.env.local` dependency:** The cron prompt extracts creds from `~/crm-dashboard/.env.local`. On a remote agent without the CRM repo cloned, this file is absent. Cron jobs must get Supabase creds from a source that exists on the target machine — profile `.env`, main `.hermes/.env`, or a dedicated `.env.supabase`.

## Running Embed

After sync, re-run embedding for any pages that failed:

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  bun run src/cli.ts embed --stale
```

## Prerequisite: sync.repo_path Config (brain directory)

The `dream` command requires `sync.repo_path` in the database config (NOT a file-config key like `brain.dir`). Without it, you get:

```
No brain directory found. Pass --dir <path> or configure one via `gbrain init`.
```

The dream cycle's `resolveBrainDir()` reads `engine.getConfig('sync.repo_path')` — stored in the database `config` table, NOT in `~/.gbrain/config.json`. The old `brain.dir` key is not read by the code.

Set it if not already configured:

```bash
cd ~/gbrain && \
  bun run src/cli.ts config set sync.repo_path /home/cheehow/brain
```

Verify:

```bash
cd ~/gbrain && \
  bun run src/cli.ts config get sync.repo_path
```

> **⚠️ Key confusion trap:** The config key is `sync.repo_path`, NOT `brain.dir`. Setting `brain.dir` has no effect — the dream cycle code specifically reads `sync.repo_path`. When migrating from PGLite to Postgres, this config key is NOT preserved by the migration — it must be re-set after migration.

## Daily Dream Cycle

The dream cycle (`gbrain dream`) runs:
lint → backlinks → sync → **synthesize** → extract → patterns → embed → orphans

### Running the dream cycle

**Correct command:**
```bash
cd ~/gbrain && gbrain dream
```

⚠️ **Do NOT use `python3 -m gbrain dreamcycle`** — gbrain is a Bun CLI binary, not a Python module, and there is no `dreamcycle` subcommand. The correct invocation is `gbrain dream` (run from `~/gbrain/` directory).

### Prerequisites for all phases to succeed

| Config | Needed for | How to set |
|--------|-----------|------------|
| `sync.repo_path` | All phases that read brain files | `gbrain config set sync.repo_path /home/cheehow/brain` |
| `models.tier.reasoning` | Patterns phase (fixes `PATTERNS_PHASE_FAIL`) | `gbrain config set models.tier.reasoning "openrouter:anthropic/claude-sonnet-4"` |
| `ANTHROPIC_API_KEY` in environment | Synthesize subagents | Add to gbrain wrapper at `~/.local/bin/gbrain` |
| `dream.synthesize.enabled` | Synthesize | `gbrain config set dream.synthesize.enabled true` |
| `dream.synthesize.session_corpus_dir` or `meeting_transcripts_dir` | Synthesize transcript source | Point at meeting notes directory |

### ⚠️ Synthesize requires valid Anthropic API key (not replaceable with OpenRouter)

The synthesize phase spawns subagent processes that are **hard-pinned to Anthropic-direct API**. The gbrain code at `src/core/minions/handlers/subagent.ts` calls `isAnthropicProvider()` which only accepts bare model names starting with `claude-` or models with the `anthropic:` provider prefix. OpenRouter-prefixed models (`openrouter:anthropic/claude-sonnet-4`) fail this check.

The `agent.use_gateway_loop` config flag exists in gbrain (v0.38 S1.10) to route subagent jobs through a provider-agnostic gateway loop. However:
- Setting it via `gbrain config set agent.use_gateway_loop true --force` stores a boolean value that the code rejects via `typeof === 'string'` check
- Inserting it directly into PGLite as text `"true"` passes the type check, but the underlying gateway auth chain still fails with OpenRouter 401
- The gbrain source comment confirms this is still experimental: "Relaxing the gate is a deeper architectural change tracked in TODOS.md"

**Bottom line:** Synthesize requires a **valid Anthropic API key** from console.anthropic.com. OpenRouter proxying will NOT work. If the key is expired or invalid, tell the user and accept that the synthesize phase will be skipped (all 14 other phases work fine).

**To verify the Anthropic key:**
```python
import requests
resp = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={"x-api-key": "your-key", "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
    json={"model": "claude-sonnet-4-6", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]}
)
```
HTTP 200 = key works. HTTP 401 = key invalid.

### Dream cycle output interpretation

A healthy dream cycle summary looks like:
```
Dream cycle in 3-120s:
  ! lint        0 fix(es) applied, 25228 remaining
  ✓ backlinks   464 missing back-link(s) found (audit-only)
  ✓ sync        +0 added, ~0 modified, -0 deleted
  - synthesize  dream.synthesize.session_corpus_dir is unset (or ✓ or ✗)
  ✓ extract     0 link(s), 0 timeline entries
  ✓ patterns    0 pattern page(s) written/updated
  ✓ embed       0 chunk(s) newly embedded
  ! orphans     26684 orphan page(s) out of 27614 total
  ✓ purge       purged 0 source(s)
```

Key things to check:
- **Synthesize:** `-` (skipped, dir unset), `✗` (failed, bad API key or PGLite worker issue), or `✓` (working)
- **Patterns:** Must be `✓` — if `✗` with model error, fix the reasoning tier config
- **Orphans `!`**: 26K+ is normal (report-only)
- **Timing:** First run may take 100-120s with patterns actually processing. Subsequent runs are 3-20s (cached/incremental)

**Correct command:**
```bash
cd ~/gbrain && gbrain dream
```

⚠️ **Do NOT use `python3 -m gbrain dreamcycle`** — gbrain is a Bun CLI binary, not a Python module, and there is no `dreamcycle` subcommand. The correct invocation is `gbrain dream` (run from `~/gbrain/` directory).

**Cron job configuration:**
The cron job for the dream cycle should have:
- Prompt: `cd /home/cheehow/gbrain && gbrain dream`
- Schedule: `0 2 * * *` (daily at 2 AM)
- Deliver: `local` (output captured by cron, no delivery needed)
- No tool restrictions needed (gbrain CLI only)
- The job runs in the default Hermes profile (not a dedicated gbrain profile)
- Output is captured by the cron system — errors appear in the job's last_status field

**Verifying the cron job works:**
```bash
cronjob action=list | grep -A5 "gbrain dream"
```
Look for `last_status: ok` rather than `error`. On first run, check the `Dream cycle (partial) in Ns:` summary for failed phases.

### Prerequisites for all phases to succeed

| Config | Needed for | How to set |
|--------|-----------|------------|
| `sync.repo_path` | All phases that read brain files | `gbrain config set sync.repo_path /home/cheehow/brain` |
| `models.tier.reasoning` | Patterns phase | `gbrain config set models.tier.reasoning "openrouter:anthropic/claude-sonnet-4"` |
| `ANTHROPIC_API_KEY` in environment | Synthesize subagents | Add to gbrain wrapper at `~/.local/bin/gbrain` |
| `dream.synthesize.enabled` | Synthesize | `gbrain config set dream.synthesize.enabled true` |
| `dream.synthesize.session_corpus_dir` or `meeting_transcripts_dir` | Synthesize transcript source | Point at meeting notes dir |

### ⚠️ Synthesize requires valid Anthropic API key (not replaceable with OpenRouter)

The synthesize phase spawns subagent processes that are **hard-pinned to Anthropic-direct API**. The gbrain code at `src/core/minions/handlers/subagent.ts` calls `isAnthropicProvider()` which only accepts bare model names starting with `claude-` or models with the `anthropic:` provider prefix. OpenRouter-prefixed models (`openrouter:anthropic/claude-sonnet-4`) fail this check.

The `agent.use_gateway_loop` config flag exists in gbrain (v0.38 S1.10) to route subagent jobs through a provider-agnostic gateway loop. However:
- Setting it via `gbrain config set agent.use_gateway_loop true --force` stores a boolean value that the code rejects via `typeof === 'string'` check
- Inserting it directly into PGLite as text `"true"` passes the type check, but the underlying gateway auth chain still fails with OpenRouter 401
- The gbrain source comment confirms this is still experimental: "Relaxing the gate is a deeper architectural change tracked in TODOS.md"

**Bottom line:** Synthesize requires a **valid Anthropic API key** from console.anthropic.com. OpenRouter proxying will NOT work. If the key is expired or invalid, tell the user and accept that the synthesize phase will be skipped (all 14 other phases work fine).

**To verify the Anthropic key:**
```python
import requests
resp = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={
        "x-api-key": "your-key",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    },
    json={
        "model": "claude-sonnet-4-6",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "hi"}]
    }
)
```
HTTP 200 = key works. HTTP 401 = key invalid.

### Updating the gbrain wrapper to pass ALL API keys

The wrapper at `~/.local/bin/gbrain` must pass all three keys for full gbrain functionality:

```bash
#!/bin/bash
export PATH="/home/cheehow/.local/bin:/home/cheehow/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
OP_KEY=$(grep -m1 '^OPENROUTER_API_KEY=*** /home/cheehow/.hermes/.env | cut -d= -f2-)
OP_KEY=$(grep -m1 '^OPENROUTER_API_KEY=*** /home/cheehow/.hermes/.env | cut -d= -f2-)
AN_KEY=$(grep -m1 '^ANTHROPIC_API_KEY=*** /home/cheehow/.hermes/.env | cut -d= -f2-)
exec env \
  OPENROUTER_API_KEY=*** \
  OPENAI_API_KEY=*** \
  ANTHROPIC_API_KEY=*** \
  OPENAI_BASE_URL="https://openrouter.ai/api/v1" \
  /home/cheehow/.npm-global/bin/bun run /home/cheehow/gbrain/src/cli.ts "$@"ehow/.hermes/.env | cut -d= -f2-)
exec env \
  OPENROUTER_API_KEY=*** \
  OPENAI_API_KEY=*** \
  ANTHROPIC_API_KEY=*** \
  OPENAI_BASE_URL="https://openrouter.ai/api/v1" \
  /home/cheehow/.npm-global/bin/bun run /home/cheehow/gbrain/src/cli.ts "$@"
```

⚠️ **Redaction pitfall:** The `write_file` and `patch` tools may corrupt API keys in the wrapper by injecting `***` into grep patterns (e.g. turning `'^OPENROUTER_API_KEY=*** into `'^OPENROUTER_API_KEY=*** After writing, ALWAYS verify with `head -5 ~/.local/bin/gbrain | xxd | head -3` to check the actual bytes. The correct grep pattern is `'^OPENROUTER_API_KEY=*** with NO key value inside the quotes.

**Preferred approach:** Use a heredoc in terminal rather than write_file to avoid redaction corruption:
```bash
cat > ~/.local/bin/gbrain << 'SCRIPT_END'
#!/bin/bash
...
SCRIPT_END
```

### Patterns phase failure fix (common)

If the patterns phase fails with:
```
[InternalError/PATTERNS_PHASE_FAIL] subagent job rejected: data.model "claude-sonnet-4-6" references an unknown provider.
```

This is a model resolution chain issue. The fix is to set the reasoning tier with an explicit `provider:model` string in the gbrain PGLite config DB:

```bash
cd ~/gbrain && gbrain config set models.tier.reasoning "openrouter:anthropic/claude-sonnet-4"
```

Unlike synthesize, the patterns phase tolerates OpenRouter-proxied Anthropic models — only the subagent dispatch (synthesize) requires direct Anthropic access.

**To verify the fix:**
```bash
cd ~/gbrain && timeout 180 gbrain dream 2>&1 | grep -E "patterns|synthesize"
```
Expected: `✓ patterns 0 pattern page(s) written/updated` (not failed). The very first run after fixing may take longer (patterns actually processes pages); subsequent runs are fast (cached/incremental).

### Dream cycle output interpretation

### ⏱️ Patterns phase runtime — scales with brain size

The patterns phase is the most computationally expensive step and its runtime scales linearly with page count. **This is the critical timing bottleneck for the dream cycle on large brains.**

| Brain size | Expected patterns runtime | Notes |
|---|---|---|
| 1K–5K pages | 10–60s | Fast, completes within foreground timeout |
| 5K–15K pages | 1–5 min | May approach 600s foreground limit |
| 15K–30K pages | 5–15 min | **Will exceed default foreground timeout** |
| 30K+ pages | 15–30+ min | **Must run in background** — see below |

For this user's brain (~32K pages, 31K+ orphans), the patterns phase consistently takes **20+ minutes** and WILL be killed by the 600s foreground timeout.

### Running the dream cycle on large brains (30K+ pages)

**Two strategies to avoid timeout mid-cycle:**

**Strategy A — Full cycle in background (recommended for cron):**
```bash
cd ~/gbrain && gbrain dream
```
This needs the session's foreground timeout (max 600s). If patterns exceeds that, fall back to Strategy B. For cron jobs, the default 30-min cron timeout is usually sufficient for a full cycle.

**Strategy B — Run phases individually (recovery after timeout):**
When the full `gbrain dream` times out during patterns (SIGTERM), the remaining phases (embed, orphans) are skipped. Resume by running the timed-out phase plus remaining phases separately:

```bash
# Run the timed-out phase with sufficient time:
cd ~/gbrain && timeout 1800 gbrain dream --phase patterns
# Then run remaining phases:
cd ~/gbrain && gbrain dream --phase embed
cd ~/gbrain && gbrain dream --phase orphans
```

Available phase names: `lint`, `backlinks`, `sync`, `synthesize`, `extract`, `extract_facts`, `extract_atoms`, `resolve_symbol_edges`, `patterns`, `synthesize_concepts`, `recompute_emotional_weight`, `consolidate`, `propose_takes`, `grade_takes`, `calibration_profile`, `conversation_facts_backfill`, `enrich_thin`, `skillopt`, `embed`, `orphans`, `schema-suggest`, `purge`.

Pass a single phase at a time: `gbrain dream --phase <name>` (comma-separated is NOT supported).

**Strategy C — Background terminal + notify (for ad-hoc runs from inside a Hermes session):**
Use `terminal(background=true, notify_on_complete=true)` with a generous timeout (e.g. 3600s) to let a phase run without blocking the conversation.

### Timing note — empty runs are fast

After the first successful patterns run, subsequent full dream cycles are fast (3–20s) because patterns is cached/incremental. If you haven't run patterns successfully yet (e.g. after a fresh sync), the first run will be the slow one.

### Config deprecation note

The dream cycle emits a deprecation warning:
```
[models] deprecated config "dream.synthesize.model" ignored;
"models.dream.synthesize" is set and wins. Remove "dream.synthesize.model"
from your config in v0.30.
```
To clean this up, unset the old key:
```bash
cd ~/gbrain && gbrain config delete dream.synthesize.model
```

### Dream cycle output interpretation

A healthy dream cycle summary looks like:
```
Dream cycle in 3-120s:
  ! lint        0 fix(es) applied, 25228 remaining
  ✓ backlinks   464 missing back-link(s) found (audit-only)
  ✓ sync        +0 added, ~0 modified, -0 deleted
  - synthesize  dream.synthesize.session_corpus_dir is unset  (or ✓ or ✗)
  ✓ extract     0 link(s), 0 timeline entries
  ✓ patterns    0 pattern page(s) written/updated
  ✓ embed       0 chunk(s) newly embedded
  ! orphans     26684 orphan page(s) out of 27614 total
  ✓ purge       purged 0 source(s)
  totals: lint=0 backlinks=0 synced=0 extracted=0 embedded=0 orphans=26684 synth=0 patterns=0
```

Key things to check:
- **Lint `!`** (warning): 25K+ remaining is normal — pre-existing issues, not new
- **Synthesize:** `-` (skipped, dir unset) or `✗` (failed, bad API key) or `✓` (working)
- **Patterns:** Must be `✓` — if `✗` with model error, fix the reasoning tier config. If the cycle timed out (SIGTERM), patterns likely was the blocker — use Strategy B above
- **Orphans `!`**: 26K+ is normal (report-only)
- **Timing:** First run may take 100-120s with patterns actually processing. Subsequent runs are 3-20s (cached/incremental)

> **Note:** The dream cycle's orphans phase is **report-only** — it detects and counts orphan pages but does not cross-link them. For the actual cross-linking workflow (adding `[[wikilinks]]` to orphan pages), see the `brain-crosslinking` skill in the `note-taking` category.

## gbrain MCP Tools: Native Hermes Integration

When gbrain's MCP server is wired into a Hermes profile's `config.yaml`:

```yaml
mcp_servers:
  gbrain:
    command: "gbrain"
    args: ["mcp"]
    env:
      GBRAIN_SOURCE: "hr"        # Scope to department source
```

All 30+ gbrain tools become native Hermes tools prefixed `mcp_gbrain_*`.

### Core Tools Reference

| MCP Tool | What It Does | Replaces |
|---|---|---|
| `mcp_gbrain_put_page` | Write/update a brain page. Auto-chunks, embeds into pgvector, reconciles tags, extracts graph edges from wikilinks. **Canonical write path.** | `write_file` + manual sync |
| `mcp_gbrain_get_page` | Get a page by slug with full content | `read_file` + find |
| `mcp_gbrain_search` | Hybrid search (vector + BM25 + RRF). Returns ranked results with evidence tags and `create_safety` hints | `grep`, `find`, manual search |
| `mcp_gbrain_think` | Synthesize answer across results with citations + gap analysis. Tells you what's stale, uncited, contradictory, or missing | Manual synthesis across files |
| `mcp_gbrain_list_pages` | List pages by type, tag, date range, sort | `find`, `ls` |
| `mcp_gbrain_find_experts` | Find people connected to a topic via graph edges | Manual people search |
| `mcp_gbrain_graph_query` | Multi-hop graph traversal (e.g. "who works_at X and attended Y?") | Manual cross-referencing |
| `mcp_gbrain_get_brain_identity` | Confirm which brain/source you're connected to | — |
| `mcp_gbrain_list_skills` | List available published skills | — |

### Source Scoping (Per-Department)

Each Hermes profile should get its own gbrain source. This is configured via `GBRAIN_SOURCE` env var in the profile's `config.yaml`:

```yaml
mcp_servers:
  gbrain:
    command: "gbrain"
    args: ["mcp"]
    env:
      GBRAIN_SOURCE: "hr"         # isolated to hr/ source
```

Create sources per department:
```bash
gbrain sources add hr --path ~/brain/hr
gbrain sources add projects --path ~/brain/projects
gbrain sources add finance --path ~/brain/finance
gbrain sources add procurement --path ~/brain/procurement
```

**Each profile then maps to its source:** HR → `GBRAIN_SOURCE=hr`, Projects → `GBRAIN_SOURCE=projects`, etc. Every `search`, `put_page`, `think` automatically targets only that department's data.

### Cross-Source Queries

When an agent needs to search across departments:

```bash
# Via CLI — query a specific source
gbrain search "query" --source projects

# Query all sources (no --source flag defaults to all accessible)
gbrain search "query"

# Via MCP — the GBRAIN_SOURCE env var scopes the MCP connection.
# To query outside the scope, use the CLI with explicit --source.
```

### Refactoring Patterns: Replace File Ops with gbrain MCP

**Write path:** Instead of writing files then waiting for sync:
```
OLD: write_file path=~/brain/projects/tasks/PROJ-42.md content="..."
NEW: mcp_gbrain_put_page(slug="projects/tasks/PROJ-42", content="# PROJ-42...\n")
```

**Read path:** Instead of grep+finding across files:
```
OLD: grep -r "blocker" ~/brain/projects/tasks/
NEW: mcp_gbrain_search(query="blocked tasks")
```

**Synthesis path:** Instead of manually connecting dots across multiple files:
```
OLD: Read 3 files manually, synthesize by hand
NEW: mcp_gbrain_think(query="What's the status of Project X and its blocked tasks?")
```

**Admin path:** Instead of ls/find:
```
OLD: find ~/brain/projects/ -name "*.md"
NEW: mcp_gbrain_list_pages(type="task", limit=50, sort="updated_desc")
```

### Why This Matters

| Pattern | Old (file ops) | New (gbrain MCP) |
|---|---|---|
| Writes | Bare files, no embedding | Auto-chunks, embeds, graph edges |
| Reads | grep/find, no ranking | Hybrid vector + BM25 + RRF |
| Synthesis | Manual, no citation tracking | Automated with gap analysis |
| Scoping | Convention-only (folder naming) | Database-enforced per source |

## gbrain think — Multi-hop Synthesis

`gbrain think` synthesizes across pages, takes, and the link graph to produce
cited answers with conflict + gap analysis. Requires a model configured for
the LLM role.

### Configuring think

The think subsystem needs a model capable of multi-turn synthesis:

```bash
cd ~/gbrain && gbrain config set models.think "openrouter:anthropic/claude-sonnet-4"
```

Also set `models.default` as a fallback:

```bash
cd ~/gbrain && gbrain config set models.default "openrouter:anthropic/claude-sonnet-4"
```

These go in the PGLite config DB, not the JSON file. Verify with:

```bash
cd ~/gbrain && bun -e '
const{PGlite}=await import("@electric-sql/pglite");
const db=await PGlite.create("/home/cheehow/.gbrain/brain.pglite");
const r=await db.query("SELECT * FROM config WHERE key LIKE $1", ["models.%"]);
console.log(JSON.stringify(r.rows, null, 2));
await db.close();
'
```

### Running think

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  OPENAI_BASE_URL="https://openrouter.ai/api/v1" \
  gbrain think "What do I know about Tapway's competitors?" --save
```

- `--save` persists the synthesis as a brain page in `synthesis/<slug>`
- `--anchor <slug>` pulls the entity subgraph around a specific page
- `--take` appends a take row to the anchor page (requires `--anchor`)

### Warning: PGLite lock contention

`gbrain think` needs the PGLite lock. If autopilot is running, it times out
with `"Timed out waiting for PGLite lock"`. Pause autopilot first (see the
section below on autopilot pause/resume). Alternatively, use the Supabase REST
query script for quick brain-first lookups that don't need synthesis.

### What think returns

A structured answer with:
- **Answer** section — synthesized from pages, takes, and graph
- **Gaps** section — what the brain didn't know (material for follow-up capture)
- No LLM available warning — means `models.think` is not configured or no API key

## ❗ gbrain serve --http: Admin Dashboard, NOT a Brain Page Website

**⚠️ CRITICAL DISTINCTION:** `gbrain serve --http` starts an **MCP admin server** for registering API keys, OAuth clients, and managing agent tokens at `http://localhost:<port>/admin`. It is **NOT** a web UI for browsing or rendering your brain pages as HTML. There is no gbrain command that produces a browsable website of brain pages.

| What you want | Which tool | Notes |
|---|---|---|
| 📖 Browse brain pages as HTML website | Custom renderer (e.g. `brain-site-server.py` at `~/brain-site/`) | Renders `.md` → HTML on-the-fly. No build step. Built separately — not a gbrain feature. |
| 📎 Share single brain page as encrypted HTML | `gbrain publish <page.md>` | Standalone AES-256-GCM file. No server needed. |
| 🔑 Register MCP agents / manage tokens | `gbrain serve --http` | Admin dashboard at `/admin`. Handles API keys, OAuth clients, scope management. |
| 🔍 Search brain pages (zero contention) | `~/.hermes/scripts/brain-query.sh <term>` | Supabase REST — always available, no lock contention. |
| 🧠 Cross-reference synthesis | `gbrain think "..."` | Multi-hop across 27K pages. Requires pausing autopilot. |

**Bottom line:** If someone asks for a "web UI" for the brain, they mean a website that renders `.md` files as HTML pages. That is **NOT** `gbrain serve --http`. Use the custom `brain-site-server.py` or `gbrain publish` for individual pages. The gbrain admin dashboard only manages MCP/OAuth access.

### Starting the server

```bash
cd ~/gbrain && bun run src/cli.ts serve --http --port 8779 --bind 127.0.0.1
```

Admin dashboard at `http://localhost:8779/admin`, MCP endpoint at `http://localhost:8779/mcp`.
The admin token is printed on startup.

Available ports (from registry): 8779 is free (8760-8779 backend API range).
- Engine info (Postgres/PGLite, page count, embedding coverage)

The MCP endpoint (for Hermes tools) is at `http://localhost:<port>/mcp`.
Health check at `http://localhost:<port>/health`.

Admin token is printed on startup — paste into the `/admin` login prompt.
Available ports (from registry): 8779 is free (8760-8779 backend API range).

### Adding to Hermes config.yaml

```yaml
mcp_servers:
  gbrain:
    url: "http://localhost:8779/mcp"
    timeout: 120
    connect_timeout: 60
```

After adding, restart the Hermes gateway. On startup it connects to gbrain's MCP
server, discovers all tools, and registers them as `mcp_gbrain_*`.

### PGLite lock contention with autopilot

The MCP server connects to PGLite, which has an exclusive lock. If autopilot is
running, the MCP server will fail to start because autopilot holds the lock.

**Two patterns for coexistence:**

1. **Dedicated service (replaces autopilot):** Stop autopilot, start MCP server.
   Schedule sync/extract/embed as separate cron jobs that stop the MCP server,
   run the operation, then restart it.

2. **On-demand (current setup):** Don't run a persistent MCP server. Use the
   brain-query.sh (Supabase REST) for always-available brain lookups, and
   brain-think.sh (pauses autopilot, runs think, restarts) for synthesis.

### Creating a systemd service

```bash
# File: ~/.config/systemd/user/gbrain-mcp.service
[Unit]
Description=GBrain MCP Server
After=network.target

[Service]
Type=simple
ExecStart=/home/cheehow/gbrain/bin/gbrain-mcp.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

Where `~/gbrain/bin/gbrain-mcp.sh` is a wrapper that injects the OpenRouter key
and starts the HTTP server. Requires autopilot to be stopped first.

### Security note

The HTTP MCP server uses OAuth 2.1 with bearer tokens. For local-only access
(loopback), the admin token on startup is sufficient. For remote access, generate
access tokens: `gbrain auth create --label "hermes-gateway" --scopes "search,query,get_page,think"`

Many gbrain commands (extract, think, embed, doctor --remediate) need exclusive
PGLite access. Autopilot holds the lock in a ~12s cycle every ~150s, so
concurrent CLI calls time out waiting.

### Pattern: pause → operate → resume

```bash
# Stop autopilot (may need -9 if stop-sigterm hangs)
systemctl --user stop gbrain-autopilot.service
# If it hangs in deactivating:
kill -9 <PID>  # find PID via systemctl --user status

# Run your exclusive operation
cd ~/gbrain && gbrain extract all

# Restart autopilot
systemctl --user start gbrain-autopilot.service

# Re-enable (if you disabled it)
systemctl --user enable --now gbrain-autopilot.service
```

### Pitfalls

- ❌ `systemctl --user stop` can hang if autopilot is mid-cycle. After 60s, use
  `kill -9` on the bun PID.
- ❌ After kill, the systemd state becomes `failed (Result: signal)` — that's
  fine. `systemctl --user start` works normally.
- ❌ Disabling autopilot with `--now` is safer for long operations (extract,
  embed) since systemd won't restart it. Re-enable afterward.
- ❌ `gbrain doctor` will report `[WARN] connection: Could not connect` if
  autopilot holds the lock — check with `systemctl --user is-active` first.

## Brain-First Lookup via Supabase REST (Zero Contention)

Since PGLite has lock contention issues, **brain-first lookups** for people,
companies, and concepts go through the Supabase REST API which is always
available. The Supabase sync runs every 15 minutes independently.

### Quick query script

```bash
~/.hermes/scripts/brain-query.sh "search term" [limit]
```

Returns JSON with slug, title, updated_at for matching pages.
Uses ILIKE on slug + title columns.

### Capture script (filesystem direct)

```bash
~/.hermes/scripts/brain-capture.sh "Title" "Content" [folder]
```

Writes markdown directly to `~/brain/<folder>/` — no lock contention.
Autopilot picks it up on its next cycle, Supabase sync within 15 min.
Default folder: `inbox`. Other folders: `ideas`, `concepts`, `people`, `companies`.

### When to use which

| Need | Tool | Why |
|------|------|-----|
| Quick lookup (person, company, topic) | `brain-query.sh` | No lock contention, instant |
| Capture original idea or signal | `brain-capture.sh` | Writes directly, async sync |
| Deep synthesis across 27K pages | `gbrain think` (pause autopilot) | Full cross-reference + gap analysis |
| Structural extraction | `gbrain extract all` (pause autopilot) | Updates link graph + timeline |

## Autopilot (systemd Service, Recommended)

Autopilot replaced the old 2AM dream-cycle cron. It runs as a continuous systemd user service that does sync → extract → embed on a configurable interval (default 5 min).

### Install

```bash
cd ~/gbrain && gbrain autopilot --install --repo ~/brain
```

This creates:
- `~/.config/systemd/user/gbrain-autopilot.service` — systemd unit
- `~/.gbrain/autopilot-run.sh` — wrapper script that sources shell profiles
- `~/.gbrain/autopilot.log` — main log
- `~/.gbrain/autopilot.err` — error log

### PATH Hardening (Critical for WSL/systemd)

systemd user services strip `$PATH` to `/usr/local/bin:/usr/bin:/bin`. If `bun` and `gbrain` are in `~/.npm-global/bin/` or `~/.local/bin/`, the service exits immediately with code 127.

**Fix the autopilot-run.sh** after install — add absolute PATH and absolute gbrain path:
```bash
# In ~/.gbrain/autopilot-run.sh, after the source lines, add:
export PATH="/home/cheehow/.local/bin:/home/cheehow/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
# The gbrain wrapper at ~/.local/bin/gbrain also must use absolute paths (see "Permanent gbrain Wrapper" above)
```

**Fix the gbrain wrapper** to use absolute paths and pass BOTH keys:
```bash
OP_KEY=$(grep -m1 '^OPENROUTER_API_KEY=*** /home/cheehow/.hermes/.env | cut -d= -f2-)
AN_KEY=$(grep -m1 '^ANTHROPIC_API_KEY=*** /home/cheehow/.hermes/.env | cut -d= -f2-)
exec env \
  OPENROUTER_API_KEY=*** \
  OPENAI_API_KEY=*** \
  ANTHROPIC_API_KEY=*** \
  OPENAI_BASE_URL="https://openrouter.ai/api/v1" \
  /home/cheehow/.npm-global/bin/bun run /home/cheehow/gbrain/src/cli.ts "$@"
```

> **Critical:** gbrain v0.40+ reads `OPENROUTER_API_KEY` directly for embedding auth. \
> The old wrapper (only `OPENAI_API_KEY="$OPENROUTER_KEY"`) causes \
> **"Missing Authentication header"** on every embedding via systemd/autopilot. \
> The wrapper must set **BOTH** env vars. Verify with:
> ```bash
> gbrain embed --stale 2>&1 | grep -c "Missing Authentication header"
> ```
> Should be 0 after the fix.

### Verify

```bash
systemctl --user status gbrain-autopilot.service
# Look for: Active: active (running)
tail -5 ~/.gbrain/autopilot.log
# Look for: [cycle] score=... elapsed=... next=...
```

### Limitations with PGLite

PGLite uses an exclusive file lock, so autopilot falls back to **inline mode** (sync → extract → embed runs inline, not via subagent dispatch). This is fine for single-user brains — no synthesize or patterns phases run. To use the full subagent architecture, migrate to Supabase (Postgres).

### Uninstall

```bash
gbrain autopilot --uninstall
```

## Model Resolution Chain Failure (prefixWithProviderFrom + TIER_DEFAULTS)

### Symptom

Dream cycle phases fail with specific errors:

**patterns phase:** `PATTERNS_PHASE_FAIL` — `data.model "claude-sonnet-4-6" references an unknown provider. Use format provider:model where provider matches a recipe in src/core/ai/recipes/.`

**propose_takes phase (silent):** 100/100 page extractions fail with `[chat(openai:claude-sonnet-4-6)] claude-sonnet-4-6 is not a valid model ID` — every page produces 0 proposals.

### Root Cause (7-step chain)

1. `reconfigureGatewayWithEngine()` calls `resolveModel()` with `tier: 'reasoning'` and `fallback: cfg.chat_model` (which is `openai:gpt-5.2` from config.json)
2. No DB-level config overrides exist (`models.default`, `models.tier.reasoning`, `models.chat` are all unset)
3. Resolution falls through to **step 7**: `TIER_DEFAULTS.reasoning` = `'claude-sonnet-4-6'` (bare model, NO provider prefix)
4. Back in `reconfigureGatewayWithEngine`, the resolved model is `'claude-sonnet-4-6'` — does NOT contain `:`
5. `prefixWithProviderFrom('openai:gpt-5.2', 'claude-sonnet-4-6')` extracts the `openai:` provider prefix from the original `chat_model` config and prepends it → **`'openai:claude-sonnet-4-6'`**
6. This invalid model string becomes the gateway's `_config.chat_model`
7. All `gateway.chat()` calls without an explicit model override route to OpenRouter with model=`claude-sonnet-4-6`, which OpenRouter rejects (it expects `anthropic/claude-sonnet-4-6`)

**patterns phase also fails independently:** the patterns code passes `data.model = 'claude-sonnet-4-6'` (bare) to the subagent handler. The handler calls `classifyCapabilities()` → `parseModelId()` which requires `provider:model` format (colon separator). Bare `claude-sonnet-4-6` has no colon → `classifyCapabilities` returns `'unknown'` → subagent job rejected.

### Why `TIER_DEFAULTS` has bare models

The `TIER_DEFAULTS` map (`src/core/model-config.ts`) stores bare model names without provider prefixes:
```typescript
export const TIER_DEFAULTS: Record<ModelTier, string> = {
  utility:   'claude-haiku-4-5-20251001',
  reasoning: 'claude-sonnet-4-6',
  deep:      'claude-opus-4-7',
  subagent:  'claude-sonnet-4-6',
};
```

These work fine for the original Anthropic-direct code paths (where `isAnthropicProvider()` recognizes `claude-*` prefix). But when run through an OpenAI-proxied gateway (OpenRouter), `prefixWithProviderFrom` mixes provider prefixes with inappropriate models.

### Fix

Set the reasoning tier to a valid `provider:model` pair (one that matches the actual LLM provider):

```bash
# Option A (recommended — Anthropic model routed through OpenRouter):
cd ~/gbrain && bun run src/cli.ts config set models.tier.reasoning "anthropic:claude-sonnet-4-6"

# Option B (use the configured OpenAI model directly):
cd ~/gbrain && bun run src/cli.ts config set models.tier.reasoning "openai:gpt-5.2"

# Option C (set global default — catches all tiers without overrides):
cd ~/gbrain && bun run src/cli.ts config set models.default "anthropic:claude-sonnet-4-6"
```

Verify the fix:
```bash
cd ~/gbrain && bun run src/cli.ts doctor 2>&1 | head -5
# Then run a dream dry-run:
cd ~/gbrain && bun run src/cli.ts dream --dry-run --json 2>&1 | grep -E '"status":"fail"'
# Should show no failures (except expected skips like synthesize)
```

After fixing `models.tier.reasoning`, re-run the dream cycle:
```bash
cd ~/gbrain && /home/cheehow/.hermes/scripts/gbrain-runner.py dream --json
```

The **propose_takes** phase will also recover because it uses `gateway.chat()` without a model override, which falls through to the gateway's `chat_model` — which is now correctly `anthropic:claude-sonnet-4-6` after `reconfigureGatewayWithEngine` re-resolves.

### Debugging the resolution chain

To trace which model is active, check the gateway's resolved chat model:
```bash
# Inspect gateway config (g-brain level, after reconfigureGatewayWithEngine):
cd ~/gbrain && bun -e '
const{Pool}=await import("pg");
const cfg=JSON.parse(await Bun.file(process.env.HOME+"/.gbrain/config.json").text());
const pool=new Pool({connectionString: cfg.database_url});
const r=await pool.query("SELECT key, value FROM config WHERE key LIKE $1", ["models.%"]);
console.log(JSON.stringify(r.rows, null, 2));
await pool.end();
'
```

If no `models.%` rows exist, the gateway is using `TIER_DEFAULTS` combined with `prefixWithProviderFrom`. The fix is one of the set commands above.

## Dream Synthesize Phase

The **synthesize** phase (v0.23) reads conversation/meeting transcripts and distills them into permanent knowledge pages in the brain.

### Architecture Limitation: Subagents Require a Separate Worker

GBrain's native synthesize implementation uses a **MinionQueue subagent architecture** (`src/core/cycle/synthesize.ts`): it submits one `subagent` job per transcript via `MinionQueue.add`, then waits via `waitForCompletion`. Jobs are processed by a **separate worker process** (`bun run src/cli.ts jobs work`) that must run as a daemon.

**⚠️ This does NOT work with PGLite.** The exclusive file lock means only one process can connect at a time. The dream cycle orchestrator holds the lock while submitting+waiting, so a concurrent worker can't connect. Jobs sit in "waiting" forever and time out after ~35 min.

When synthesize is enabled with a valid Anthropic key but no worker, the dream cycle summary will show:
```
  ✗ synthesize  synthesize phase failed
      [InternalError/SYNTH_PHASE_FAIL] ...
```
And the dream-cycle-summaries/ page will say "N failed/timeout" (around 86 children for 63 meetings).

**There is no inline-synthesis patch in the current codebase.** The code is pure subagent dispatch. On PGLite, the synthesize phase will submit jobs that never complete. The 14 other dream phases (lint, backlinks, sync, extract, patterns, embed, orphans, propose_takes, etc.) all work fine.

**Solution: PostgreSQL** (Postgres + pgvector) enables the full subagent architecture with a separate worker daemon. Or wait for a future inline-synthesis patch (direct Sonnet/API calls inside the orchestrator process).

### Significance Filter (Stage 1)

Evaluates each transcript via a cheap model verdict: *"Is this worth saving?"* It scores for:
- New ideas, mental models, theses
- Self-reflection, personal patterns, emotional processing
- Deep discussion of people/companies/decisions

Results are cached in `dream_verdicts` to avoid re-judging transcripts. Discards routine ops, code debugging, short exchanges.

### Synthesis (Stage 2)

One Sonnet subagent per transcript (30 min timeout, 30 turns max). Writes pages
via `brain_put_page` tool in two categories:
- **Reflections** → `wiki/personal/reflections/<date>-<topic>-<hash>/`
- **Originals** → `wiki/originals/ideas/<date>-<idea>-<hash>/`

**On PGLite, this phase fails silently** — subagent jobs are submitted but no
worker can connect to process them. A future inline-synthesis patch (direct
Sonnet calls inside the orchestrator) could enable it on PGLite.

### Summary Index (Stage 3)

Writes a summary index at `dream-cycle-summaries/<date>` and a completion timestamp (`dream.synthesize.last_completion_ts`) on success.

### Configuration

| Config Key | Default | Description |
|---|---|---|
| `dream.synthesize.enabled` | `false` | Must set to `true` |
| `dream.synthesize.session_corpus_dir` | unset | Dir of `.txt` transcripts (from Hermes sessions etc.) |
| `dream.synthesize.meeting_transcripts_dir` | unset | Dir of `.md` meeting transcripts (alternative to above) |
| `dream.synthesize.model` | `claude-sonnet-4-6` | Model for subagent synthesis (OpenRouter name if proxied) |
| `dream.synthesize.verdict_model` | `claude-haiku-4-5-20251001` | Model for significance filter |
| `dream.synthesize.cooldown_hours` | `12` | Cooldown between runs |
| `dream.synthesize.min_chars` | `2000` | Minimum transcript length to consider |
| `dream.synthesize.exclude_patterns` | `["medical","therapy"]` | Word-boundary patterns to skip |

### Setup Steps

1. **Enable synthesize:**
   ```bash
   python3 ~/.hermes/scripts/gbrain-runner.py config set dream.synthesize.enabled true
   ```

2. **Point at transcript source** (choose one or both):
   ```bash
   # Meeting transcripts:
   python3 ~/.hermes/scripts/gbrain-runner.py config set dream.synthesize.meeting_transcripts_dir /home/cheehow/brain/meetings
   # Session corpus:
   python3 ~/.hermes/scripts/gbrain-runner.py config set dream.synthesize.session_corpus_dir /home/cheehow/.hermes/sessions
   ```

3. **Set cooldown and min chars:**
   ```bash
   python3 ~/.hermes/scripts/gbrain-runner.py config set dream.synthesize.min_chars 2000
   python3 ~/.hermes/scripts/gbrain-runner.py config set dream.synthesize.cooldown_hours 12
   ```

4. **Test with dry-run (all phases):**
   ```bash
   python3 ~/.hermes/scripts/gbrain-runner.py dream --dry-run
   ```
   On PGLite, the dry-run passes all 8 phases (subagents not spawned in dry mode).

5. **Run for real:**
   ```bash
   python3 ~/.hermes/scripts/gbrain-runner.py dream
   ```
   On PGLite, subagent phases (synthesize) submit jobs that sit in waiting
   indefinitely — expected, no worker can connect. Other phases (lint, backlinks,
   sync, extract, patterns, embed, orphans) complete successfully.

## Bulk Import of Markdown Files

To add a large number of .md files to the brain and sync to PGLite:

1. Copy files to the brain directory:
   ```bash
   cp -n /source/path/*.md ~/brain/companies/
   cp -n /source/path/*.md ~/brain/people/
   ```

2. Run sync (see "Running Sync" above)

**For backup zips** (companies+persons .md files sent as archives), see `references/bulk-import-from-zip.md` for the full workflow including extracting, copying, and cleaning up.

## Checking Page Count

```bash
cd ~/gbrain && bun run src/cli.ts doctor 2>&1 | grep "connection"
```

Shows: `[OK] connection: Connected, NNN pages`

## Data Ingestion from External Sources

GBrain can ingest content from external pipelines. Each pipeline combines a **deterministic sync script** (mechanical: list, read, format files) with an **agent prompt** (judgment: entity extraction, page creation). Start with `references/drive-api-patterns.md` for the API-level details, then `references/meeting-notes-implementation.md` for a concrete working example.

## v0.40+ CLI Surface (new features)

The brain is now on gbrain **v0.40.8.1** (upgraded from ~v0.35). These major CLI verbs are available:

### Schema Cathedral (v0.40.7.0)
Custom page types with prefixes, link verbs, expert routing, and agent-authored mutations.
```bash
gbrain schema active --json                    # Current pack identity
gbrain schema stats --json                     # Per-type page counts + typed coverage
gbrain schema add-type researcher --primitive person --prefix people/researchers/ --extractable --expert
gbrain schema add-link-type invested_in --inverse funded_by
gbrain schema lint --with-db                   # 11 lint rules (DB-aware)
gbrain schema sync --apply                     # Backfill page.type on matching pages
gbrain schema detect                           # Cluster pages by path → suggest types
gbrain schema fork gbrain-base mine            # Fork bundled pack to editable copy
gbrain schema use mine                         # Activate a forked pack
```
See `skills/schema-author/SKILL.md` in the gbrain repo for the full agent workflow.

### Brainstorm & LSD (v0.37.1.0 / v0.39.0.0)
```bash
gbrain brainstorm "how to expand tapway into retail AI"    # Bisociation idea generator
gbrain lsd "what if AI agents didn't exist"                 # Lateral Synaptic Drift (inverted-judge)
gbrain capture "thought or note" --type idea                # Single entrypoint to inbox/
gbrain capture --file ./notes.md --slug daily/2026-05-24    # From file with explicit slug
```

### Autopilot (v0.11.1+)
Self-maintaining brain daemon — replaces manual dream cycle cron.
```bash
gbrain autopilot --status --json                # Check if running
gbrain autopilot --install --repo ~/brain       # Install as systemd service
gbrain autopilot --uninstall                    # Remove
gbrain autopilot --interval 60                  # Custom interval in minutes
```
**Prerequisites:** Postgres engine (active DB), `gbrain jobs work` minion for full features.
**Limitation with PGLite:** Falls back to inline sync→extract→embed (no subagent dispatch).

### Publish (v0.29+) — Share Brain Pages as HTML

Share individual brain pages as self-contained password-protected HTML files. No server needed — the output is a standalone file.

```bash
# Basic publish (auto-generates password, prints it)
gbrain publish ~/brain/companies/acme.md --title "Acme Analysis" --out /tmp/share.html

# Set your own password
gbrain publish ~/brain/companies/acme.md --password "mypass" --title "Acme Analysis" --out /tmp/share.html

# Use an existing generated password
gbrain publish ~/brain/companies/acme.md --password "A3bK9x" --title "Acme Analysis" --out /tmp/share.html
```

What gets stripped from the output:
- Frontmatter (YAML between `---` delimiters)
- `[Source:]` citation footnotes
- Confirmation numbers, internal IDs
- Brain-internal `[[wikilinks]]` (converted to plain text)
- Timeline sections (deduplicated interaction logs)
- Private notes marked with `private:` or `_private:`

**Default is ALWAYS encrypted.** The password is printed to stdout when auto-generated — save it or share it with the recipient separately.

Best use cases:
- Share a person/company profile with a colleague
- Export a trip itinerary for family
- Send a deal summary to a client
- Create a one-page brief from a longer brain page

For batch publishing (e.g., all meeting notes for a month), loop over files:
```bash
for f in ~/brain/meetings/2026/05/*.md; do
  gbrain publish "$f" --out "/tmp/share/$(basename "$f" .md).html"
done
```

### Report (v0.38+) — Timestamped Structured Reports

Save a timestamped report to `brain/reports/`. Good for weekly summaries, incident post-mortems, trip debriefs, decision records.

```bash
# Save a report with frontmatter metadata
gbrain report --type weekly-review --content "..." --slug weekly-review/2026-05-24

# View recent reports
ls ~/brain/reports/
```

**When to use report vs a regular brain page:**
- **Report**: Time-bound, timestamped, metadata-rich — weekly reviews, trip debriefs, decision records, incident RCAs
- **Regular page**: Evergreen reference — company profile, person bio, concept definition, idea note
- **Daily page**: What happened today — briefings, tasks, EOD summaries (see `brain-folder-organization`)

### Capture (v0.38+) — Unified Entrypoint

Single command to get content into the brain. Writes to `brain/inbox/` by default unless `--type` is specified.

```bash
# Capture a quick thought
gbrain capture "What if we built a WhatsApp bot for teh tarik orders" --type idea

# Capture from a file
gbrain capture --file ./notes.md --slug daily/2026-05-24

# Save a web search result as a concept
gbrain capture "Jevons Paradox: when efficiency increases usage instead of decreasing it" --type concept --slug concepts/jevons-paradox

# Save an email insight to ideas
gbrain capture "Tapway x ITMAX: use existing camera infra for retail people counting" --type idea --slug ideas/retail-people-counting
```

Available types: `idea` (your own sparks), `concept` (frameworks others coined), `wiki` (evergreen reference), `inbox` (uncategorized). See the Authorship Test in `brain-folder-organization` for the decision tree.

**From email → brain:** Use Himalaya to read work email, then `gbrain capture` to save insights or contacts:
```bash
himalaya envelope list --folder INBOX --page-size 5
gbrain capture "Email from X about Y — interested in partnership" --type concept --slug concepts/tapway-partnership-X
```

### Other new verbs
```bash
gbrain features --json                   # Scan usage → recommend unused features
gbrain sources status --json             # Per-source health dashboard (multi-source brains)
gbrain integrations list                 # Pre-built integration recipes
gbrain eval trajectory <entity-slug>     # Chronological metric history with regressions
gbrain report --type weekly-review --content "..."    # Timestamped reports
gbrain doctor --remediate --target-score 90           # One-command health improvement loop
```

## Usage Gap Audit — What's Running vs Available

When a user asks "how much of gbrain are we using?" or "what's not running?", run this check first:

```bash
cd ~/gbrain && bun run src/cli.ts doctor 2>&1 | grep -E "\[(OK|WARN|FAIL)\]"
```

Then cross-reference against the gap categories below.

### Quick Scoring Reference

| Category | Max Score | Notes |
|----------|-----------|-------|
| Embeddings | 27/35 | Missing → `gbrain embed --stale` |
| Entity links | 2/25 | 2% coverage (1,720 links from 20K pages after `extract all`) |
| Timeline | 0/15 | 1% coverage (381 entries after `extract all`) |
| Dead links | 10/10 | Existing links are clean |
| Orphans | 1/15 | Report-only in PGLite |
| **Brain Score** | **40–70/100** | Autonomous max ~70; 90 requires manual content |

Note: The `extract all` command is idempotent (safe to rerun anytime). Each run
scans all 20K+ pages and adds any newly discovered links/timeline entries. Score
may increase gradually as pages gain more frontmatter dates and `[[wikilinks]]`.

### Integration & Service Status

| Component | Status | Location / Notes |
|-----------|--------|------------------|
| Autopilot | ✅ Running | Postgres inline mode (sync→extract→embed), systemd user service |
| Brain site (Quartz, being evaluated) | ✅ Live, ⚠️ Scaling limit | `cheehow-brain.gotapway.com` ← Cloudflare tunnel → localhost:8766 (auth proxy) → 8767 (static server). **Known: Quartz times out for 20K+ files** — the git-date warnings flood output and build hangs at 5+ min. User evaluating replacement (dynamic renderer or gbrain-based solution). See `references/brain-site-architecture.md`. |
| Brain auth proxy | ✅ Active | HTTP Basic Auth, user=`cheehow`, pass in systemd env `BRAIN_PASS`. Port 8766 → proxies to 8767. Systemd service: `brain-auth-proxy.service`. Auth proxy at `~/brain-site/brain-auth-proxy.py`. |
| Brain static server | ✅ Active (Quartz) | Python HTTP on 8767 serving `~/brain-quartz/public/`. Systemd service: `brain-site-server.service`. Being evaluated for replacement due to 20K+ file scaling. |
| gbrain MCP server | ✅ Running (CRM) | Port 8768, serves `crm.gotapway.com` tunnel route. Has an admin dashboard at `/admin` (React SPA) showing token management, client connections, health. Engine: Postgres. MCP endpoint at `/mcp`. |
| Email-to-brain | ❌ Not set up | Needs credential-gateway (Gmail OAuth) |
| Calendar-to-brain | ❌ Not set up | Needs credential-gateway |
| X-to-brain | ❌ Not set up | Twitter API keys needed |
| Meeting-sync | ❌ Not set up | Circleback webhook bridge |
| Dream cycle | ✅ Running (2AM cron) | `gbrain dream` via cron job. Autopilot handles continuous sync/extract/embed. Patterns ✅ fixed (model config). Synthesize ⚠️ PGLite worker limitation. |
| Git pre-commit hook | ❌ Not installed | `gbrain frontmatter install-hook` |
| Schema packs | ❌ Not active | No custom page types defined |
| Takes / hunches | ❌ No content | Knowledge claims not in use |
| Quartz encrypted-pages | ❌ Disabled | Plugin `enabled: false` in `quartz.config.yaml` |
| Per-page gbrain publish | ✅ Works standalone | Password-protected HTML, independent of Quartz |
| Integrations (6 built-in) | ❌ None active | credential-gateway, ngrok-tunnel, etc. all `AVAILABLE` |
| Minions / subagents | ❌ Not configured | Requires Postgres; PGLite file-lock prevents concurrent workers |
| Brain-folder activity | ✅ Synced | 27K+ pages in PGLite, parallel REST sync to Supabase every 15 min |

### Three-Layer Password System

This user has three independent protection layers on their brain — don't conflate them:

| Layer | Mechanism | Active? | Where credential lives | Purpose |
|-------|-----------|---------|----------------------|---------|
| **Site-wide auth** | HTTP Basic Auth reverse proxy (port 8766) | ✅ | systemd `BRAIN_PASS` in `brain-auth-proxy.service` | Protects the entire Quartz-published brain site (`cheehow-brain.gotapway.com`) |
| **Quartz per-page encryption** | `encrypted-pages` plugin (AES-256, passwordField) | ❌ Disabled | N/A — plugin set to `enabled: false` | Individual page passwords on the Quartz site |
| **gbrain publish** | Standalone AES-256-GCM HTML files | ✅ On demand | Password printed to stdout on publish (auto-generated or user-set) | Share individual brain pages as self-contained HTML files |

When user asks "what's my brain page password", clarify which layer they mean:
1. **The whole site** → Basic Auth: `cheehow` / `<BRAIN_PASS from systemd>`
2. **A specific standalone HTML file** → The password printed when `gbrain publish` was run (e.g., `Q4Cc4aEnzanJbFzW`)
3. **Per-page encryption on the live site** → Not set up (plugin disabled)

### Pitfalls

- ❌ **gbrain doctor is the single source of truth for health** — systemd status and cron logs can show a running process even when PGLite is dead in a restart loop. Always verify with `gbrain doctor` directly before reporting health.
- ❌ **Brain score of 37 doesn't mean the brain is broken** — it means embedding + link + timeline features are underutilized. The brain has 27K+ pages of solid content, just not cross-linked.
- ❌ **The Quartz encrypted-pages plugin is DISABLED** (`enabled: false` in quartz.config.yaml). Per-page password encryption via gbrain publish still works independently — it produces standalone HTML files not hosted on the site.
- ❌ **Don't conflate gbrain publish with Quartz site encryption** — `gbrain publish` produces standalone encrypted HTML files (self-contained, no server needed). The `encrypted-pages` Quartz plugin would require user password input on the live site. They are completely independent mechanisms.

## Cron-to-Brain Writing Pattern

When cron jobs that write summaries or digests are updated to also persist brain pages, see the `brain-folder-organization` skill in the `productivity` category for the canonical pattern. It covers the folder mapping table, frontmatter conventions, and implementation template. This gbrain-operations skill only handles the gbrain-specific parts (sync, dream cycle indexing).

## Pitfalls

- ❌ **`gbrain config show` used to crash when PGLite is corrupted** — Fixed in v0.40.8.1 by short-circuiting before connectEngine. If running a pre-fix version, use `gbrain doctor --fast` instead.
- ❌ **`gbrain doctor --remediate` times out under PGLite when autopilot is running** — The remediate loop needs exclusive PGLite access, but autopilot holds the lock. **Fix:** `systemctl --user stop gbrain-autopilot.service` before running `gbrain doctor --remediate`, then restart afterward.
- ❌ **Brain score ceiling of ~70 with PGLite** — `gbrain doctor --remediate --target-score 90` reports "target 90 unreachable; max autonomous = 70/100". The remaining 30 points require manually authored content (cross-links, timeline dates in frontmatter). The remediate command can only score what's already in markdown, it cannot generate new content.
- ❌ **PGLite sync skips in-place file edits** — PGLite tracks by git commit, not mtime. After patching .md files (adding wikilinks), `gbrain sync` reports "Already up to date". Fix: `cd ~/brain && git add -A && git commit -m "..."` first, then sync.
- ❌ **Autopilot status/cron reports can be misleading when PGLite is dead** — The daemon restart loop looks like activity, but ALL gbrain commands fail uniformly with `Aborted()`. A cron reading the autopilot log may claim "sync in progress" when nothing is actually happening. Always verify with an actual `gbrain doctor` call (not just systemd status or log tails) before claiming recovery progress.
- ❌ **Supabase free tier DB auto-pauses after ~1 week of inactivity** — Recovery paths: switch to PGLite (fallback), use Supabase REST API, or hit the Supabase dashboard health endpoint to wake.
- ❌ **`~/.gbrain/config.json` password can become corrupted** — The password field is stored as `***` in the config file, which causes `password authentication failed`. The real URL is not recoverable from the corrupted config. Use `session_search query="supabase database setup"` to recover the original connection string, or check `~/.hermes/.env` / Supabase dashboard.
- ❌ **`gbrain embed --stale` and `gbrain migrate` leave stale PGLite lock after SIGTERM** — When the terminal timeout kills a foreground command (e.g. 600s limit), the bun process dies leaving a `.gbrain-lock` directory at `~/.gbrain/brain.pglite/.gbrain-lock/`. The lock file contains the PID of the killed process. The next gbrain command reports `"GBrain: Timed out waiting for PGLite lock"`. **Fix:**
  ```bash
  rm -rf ~/.gbrain/brain.pglite/.gbrain-lock
  ```
  After cleanup, progress is preserved — if a migrate manifest exists (`migrate-manifest.json`), it resumes from the last completed page.

- ❌ **`migrate --to supabase` data copy times out for 27K+ pages** — The `gbrain migrate` command copies pages one-by-one from PGLite to Postgres. For 27K+ pages it exceeds the 600s terminal timeout after copying ~0. The schema migration completes instantly (already applied), but the data copy is a separate phase. After partial migration, `config.json` auto-flips to `postgres` engine with `database_url` set, making `gbrain doctor` report "Connected, 0 pages". The PGLite data at `~/.gbrain/brain.pglite/` is still intact. To retry: revert config to PGLite, run in background with no timeout. See `references/local-postgres-migration.md`.

- ❌ **bun postgres library URL parsing requires `user:password@host` format** — The bun `postgres` library does NOT support the standard `user@host` shorthand (e.g. `postgresql://gbrain@127.0.0.1:5432/gbrain`). Without a `:` separator, it parses the entire string including `@host` as the username. **Fix:** always include a colon separator. With trust auth (no password), use `user:@host` (trailing colon, empty password): `postgresql://gbrain:@127.0.0.1:5432/gbrain`. This affected `gbrain serve --http` and `gbrain migrate --to supabase --url ...`. The `DATABASE_URL` env var suffers the same issue — never rely on `user@host` shorthand.

- ❌ **Shell escaping with API keys is fragile** — `OPENROUTER_API_KEY=$(grep ...)` in bash
  mangles when the key contains special characters (shell metacharacters, quotes). The
  `~/.local/bin/gbrain` wrapper uses `grep -m1 '^OPENROUTER_API_KEY='` with single quotes
  which mostly works, but background mode and `bash -c` wrappers still fail. **Better
  approach:** Use the Python wrapper at `~/.hermes/scripts/gbrain-runner.py` which reads
  the key safely via Python's file I/O. All gbrain commands go through this when the
  shell route is unreliable. See `references/python-wrapper-pattern.md`.

- ❌ **`gbrain embed --stale` times out on large backlogs (6000+ chunks)** — The first pass persists progress incrementally even when it times out mid-run. Just run it again — it picks up only the remaining stale chunks. Expect ~4 chunks/sec throughput; a backlog of ~700 remaining chunks completes in ~3 min. Always verify final coverage with `gbrain doctor` after all passes complete.

- ❌ **`gbrain serve --http` shares the PGLite lock with autopilot** — Cannot run both simultaneously. If the MCP server is needed, autopilot must be stopped first. The Supabase REST API (brain-query.sh) is the always-available alternative for read-only lookups.

- ❌ **`OPENAI_API_KEY` is exported in `~/.bashrc`** — every new shell picks it up, making the fallback path always active unless you explicitly override it with `OPENAI_API_KEY=""`
- ❌ Using `grep OPENROUTER_API_KEY` without the `^` anchor — picks up commented-out lines first
- ❌ **Assuming the "default" source has a `local_path`** — if it's null, `gbrain sync` runs to completion and outputs only `Already up to date.` without importing anything.
- ❌ Running large syncs (>5000 files) in the foreground with default 300s timeout — it WILL time out and leave a stale lock
- ❌ **Anthropic SDK double-path bug** — when setting `baseURL: 'https://openrouter.ai/api/v1'`, the SDK appends `/v1/messages` producing `https://openrouter.ai/api/v1/v1/messages` (404). Always use `baseURL: 'https://openrouter.ai/api'` (without `/v1`).
- ❌ **Subagent dispatch requires a separate worker process** — with PGLite, a concurrent worker can't connect due to the exclusive file lock. All subagent jobs sit in "waiting" forever and time out (~35 min).
- ❌ **Dream cycle with synthesize can take 1-2+ hours** — 20 Sonnet subagents × up to 30 min each. Default terminal timeout (600s) will kill it mid-synthesis leaving a stale `gbrain-cycle` lock.
- ❌ **`brain.dir` must be set** — the `dream` command requires `brain.dir` config. Without it, `dream --json` fails with "No brain directory found."\n- ❌ **Quartz build times out for 20K+ files** — Quartz v5 checks git dates on every file, emitting a warning per untracked file. With 20K+ files in `~/brain/` that aren't all git-tracked, the output floods and `npx quartz build` times out after 5+ min. The `public/` directory may be deleted by the failed build. Fix: either git-track all files (suppresses warnings) or switch to a dynamic renderer that reads `~/brain/` on-the-fly.\n- ❌ **PGLite lock was being stolen by the 5-min stale threshold** — the old `STALE_THRESHOLD_MS = 5 * 60 * 1000` killed the autopilot's lock, causing simultaneous PGLite access → `Aborted()`. Fixed to 120 min in v0.40.8.1+.
- ❌ **`agent.use_gateway_loop true` is NOT a working fix for OpenRouter subagent dispatch on PGLite.** The flag exists in the gbrain source but: (1) `gbrain config set --force` stores a boolean value in the PGLite config table, but the subagent handler checks `typeof === 'string'` — it must be stored as SQL text `"true"` via direct DB query. (2) Even then, the OpenRouter key injection via the gbrain wrapper fails for spawned subagent processes. (3) The source code comment says it's experimental. **Bottom line:** Synthesize requires a valid `ANTHROPIC_API_KEY` and a running `gbrain jobs work` daemon — neither OpenRouter proxying nor PGLite's exclusive lock supports this.
- ❌ **`gbrain config set --force` writes to the JSON config file (~/.gbrain/config.json), NOT the PGLite DB config table.** The dream cycle and autopilot read from the PGLite `config` table via `engine.getConfig()`. If `gbrain config get` shows a value but the dream cycle still acts like it's unset, the JSON file has the value but the DB doesn't. Fix by writing directly to PGLite:
  ```bash
  cd ~/gbrain && bun -e '
  const {PGlite} = await import("@electric-sql/pglite");
  const db = await PGlite.create(process.env.HOME+"/.gbrain/brain.pglite");
  await db.query("INSERT INTO config (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = $2",
    ["agent.use_gateway_loop", "true"]);
  await db.close();
  '
  ```
- ❌ **`gbrain config set` (without --force) writes to the PGLite DB via the CLI.** This works for known keys like `models.*`, `dream.synthesize.*`, etc. But `gbrain config set agent.use_gateway_loop true --force` bypasses validation AND writes to the JSON file, NOT the DB. For unknown/experimental DB config keys, always write directly via `bun -e` + `PGlite.create()` + SQL INSERT.
- ❌ **API key corruption from write_file/patch redaction.** The `write_file` and `patch` tools redact API key values in their output, and may inject `***` into the actual file content. After modifying the gbrain wrapper at `~/.local/bin/gbrain`, ALWAYS verify the actual bytes with `head -5 ~/.local/bin/gbrain | xxd | head -3`. The hex should show `5e4f 5045 4e....45 593d 27` (the grep pattern without key values). Preferred approach: use a heredoc in terminal (`cat > file << 'EOF'`) instead of write_file for files containing API key references.
- ❌ **Subagent model config (`models.subagent`) is separate from `models.tier.reasoning`.** Fixing only `models.tier.reasoning` fixes the patterns phase but leaves the subagent dispatch tier with a bare model name. The autopilot status report will show "Subagent jobs failing — model needs agent.use_gateway_loop true or an Anthropic-direct model." Fix both:
  ```bash
  cd ~/gbrain && gbrain config set models.tier.reasoning "openrouter:anthropic/claude-sonnet-4"
  cd ~/gbrain && gbrain config set models.subagent "anthropic:claude-sonnet-4-6"
  ```
- ❌ **`gbrain dream` cron command must be correct.** The cron prompt was originally `python3 -m gbrain dreamcycle` which silently fails because: (1) gbrain is a Bun CLI, not a Python module, (2) there is no `dreamcycle` subcommand. The correct prompt for the 2AM cron: `cd /home/cheehow/gbrain && gbrain dream`. Verify with `cronjob action=list | grep dream` and check `last_status` is `ok` not `error`.
- ❌ **Syncing brain edits: git commit BEFORE gbrain sync.** After editing .md files (adding wikilinks, cross-linking), `gbrain sync` reports "Already up to date" if you haven't committed. PGLite tracks by git commit hash, not POSIX mtime. Always: `cd ~/brain && git add -A && git commit -m "..." && cd ~/gbrain && gbrain sync --repo ~/brain`. The sync output's "Extracted: N links, M timeline entries" line shows how many new links/timeline entries were discovered from the markdown content.

## Reference Files

- `references/pglite-corruption-recovery.md` — Full recovery procedure for corrupted PGLite databases (WASM Aborted() crash, postmaster.pid -42)
- `references/pglite-sync-lock-troubleshooting.md` — Full guide for lock issues
- `references/dream-cycle-config.md` — Dream cycle configuration and the script fix details
- `references/crm-data-model.md` — CRM data model in the `pages` table
- `references/bulk-import-from-zip.md` — Workflow for importing large batches of .md files from a backup zip
- `references/openrouter-anthropic-proxy.md` — Full patching guide for routing gbrain's Anthropic SDK calls through OpenRouter
- `references/drive-api-patterns.md` — Google Drive/Docs API patterns for brain ingestion
- `references/meeting-notes-implementation.md` — Concrete meeting notes sync implementation
- `references/supabase-db-recovery.md` — Supabase auto-pause recovery, config.json password corruption fix, WSL IPv6/portproxy troubleshooting
- `references/supabase-rest-api.md` — Supabase REST API sync fallback
- `references/brain-folder-conventions.md` — Semantic folder map for `~/brain/`
- `references/publish-report-capture.md` — Detailed guide for gbrain publish, report, and capture commands
- `references/python-wrapper-pattern.md` — Python wrapper for reliable API key injection (avoids bash shell escaping issues)
- `references/local-postgres-migration.md` — Full install, config, and migration guide for local PostgreSQL 16 + pgvector on WSL (schema applied, data copy pending)
- `references/brain-first-scripts.md` — Companion scripts for brain-first lookup (Supabase REST), signal capture (filesystem), and think (autopilot pause)\n- `references/brain-site-architecture.md` — Full brain web infrastructure: Cloudflare tunnel, auth proxy (8766), site server (8767), gbrain MCP (8768), systemd services, port mapping, Quartz scaling limitations\n- `references/model-resolution-chain.md` — Full debugging walkthrough of the `TIER_DEFAULTS` + `prefixWithProviderFrom` bug producing `openai:claude-sonnet-4-6`; trace of 7-step resolution chain, key source files, and why both patterns + propose_takes fail