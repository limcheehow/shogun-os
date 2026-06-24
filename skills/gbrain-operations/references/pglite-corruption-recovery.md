# PGLite Database Corruption Recovery

## Symptoms

The PGLite WASM postgres engine crashes on startup when loading an existing data directory:

1. **`gbrain doctor` shows:**
   ```
   [WARN] connection: Could not connect to configured DB (URL from config-file-path); filesystem checks only
   ```

2. **`bun run src/cli.ts config list` crashes:**
   ```
   PGLite failed to initialize its WASM runtime.
   Original error: Aborted(). Build with -sASSERTIONS for more info.
   ```

3. **Direct `PGlite.create()` also fails:**
   ```js
   const db = await PGlite.create("/home/cheehow/.gbrain/brain.pglite");
   // Error: Aborted(). Build with -sASSERTIONS for more info.
   ```

4. **Fresh/empty PGLite database works fine** — the issue is specific to the existing data directory.

## Root Cause

The database was left in an inconsistent state after an ungraceful process termination (SIGKILL/SIGTERM). The `postmaster.pid` file shows PID `-42`, which is PostgreSQL's standard sentinel for "postmaster was killed without a clean shutdown." PGLite's WASM postmaster tries to replay WAL segments on startup but crashes.

**Common triggers:**
- Dream cycle killed mid-run (timeout)
- Background sync killed by shell timeout
- Multiple concurrent PGLite connections (exclusive file lock violation)
- `bun` or Node process crash while PGLite was mid-transaction

## Diagnosis

```bash
# 1. Check postmaster.pid — if PID is -42, it's stale
cat ~/.gbrain/brain.pglite/postmaster.pid

# 2. Check gbrain doctor — if connection check fails, proceed
cd ~/gbrain && bun run src/cli.ts doctor

# 3. Verify fresh PGLite works
cd ~/gbrain && bun -e '
const { PGlite } = await import("@electric-sql/pglite");
const db = await PGlite.create("/tmp/test-pglite-fresh");
await db.query("CREATE TABLE IF NOT EXISTS test (id int)");
const r = await db.query("SELECT * FROM test");
console.log("Fresh DB works:", JSON.stringify(r.rows));
await db.close();
'

# 4. Confirm old/existing DB specifically fails
cd ~/gbrain && bun -e '
const { PGlite } = await import("@electric-sql/pglite");
try {
  const db = await PGlite.create("/home/cheehow/.gbrain/brain.pglite");
  const r = await db.query("SELECT count(*) as cnt FROM pages");
  console.log("Connected:", JSON.stringify(r.rows));
  await db.close();
} catch (e) {
  console.error("Corrupted DB:", e.message);
}
'
```

If (3) works but (4) fails → **database corruption confirmed**.

### v0.40.8.1+ improvement: auto-cleanup on connect

The engine now auto-removes stale `postmaster.pid` before creating the PGLite WASM instance. If the crash only left a stale postmaster (not WAL corruption), the auto-cleanup may get the DB working again without a full recovery. Test:

```bash
cd ~/gbrain && bun run src/cli.ts doctor
# If [OK] connection: Connected — the auto-cleanup worked.
# If still [WARN] connection — WAL is corrupt, proceed with full recovery below.
```

Note: `gbrain config show` and `gbrain config list` now bypass the engine entirely (file-plane reads). These commands work even when the DB is dead, so they are NOT a valid test of DB health. Always use `gbrain doctor` (not `config show`) to check DB connectivity.

### WAL corruption as root cause

Even after auto-cleaning `postmaster.pid`, the engine connect may still fail with `Aborted()`. The remaining failure is **WAL corruption** — the Postgres WAL segments in `pg_wal/` cannot be replayed because the previous crash left them in an inconsistent state. PGLite's WASM postmaster tries WAL recovery on startup and aborts instead of skipping corrupt segments.

The only fix for WAL corruption is wiping and re-syncing (full recovery below). Unlike real PostgreSQL, PGLite has no `pg_resetwal` utility.

## Full Recovery Procedure

### Step 1: Backup the corrupted database

```bash
mv ~/.gbrain/brain.pglite ~/.gbrain/brain.pglite.corrupted-$(date +%Y%m%d)
```

### Step 2: Create a fresh PGLite database

```bash
cd ~/gbrain && bun run src/cli.ts init
```

This creates a new database at `~/.gbrain/brain.pglite/`, applies all 27+ migrations, and sets schema to the latest version. The engine is PGLite (local Postgres WASM).

### Step 3: Set the source local_path

Fresh init creates a "default" source with `local_path = null`. It must be set before sync:

```bash
cd ~/gbrain && bun -e '
const{PGlite}=await import("@electric-sql/pglite");
const db=await PGlite.create(process.env.HOME+"/.gbrain/brain.pglite");
await db.query("UPDATE sources SET local_path=$1 WHERE id=$2",[process.env.HOME+"/brain","default"]);
const r=await db.query("SELECT id, local_path FROM sources");
console.log("Updated:",JSON.stringify(r.rows));
await db.close();
'
```

### Step 4: Re-sync from brain directory

**IMPORTANT:** The `sync` command requires `--repo` even though `local_path` is set; without it you get "No repo path specified."

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  bun run src/cli.ts sync --repo ~/brain
```

For large brains (10,000+ files), run in background. Add `--skip-failed` if `gbrain doctor` shows unacknowledged FK violations:

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  bun run src/cli.ts sync --repo ~/brain --skip-failed &
```

**Expected duration:** ~1 file/sec on PGLite WASM. 18,000+ files take 2-3 hours.

### Step 5: Re-run embedding after sync

```bash
cd ~/gbrain && \
  OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
  OPENAI_API_KEY="" \
  bun run src/cli.ts embed --stale
```

### Step 6: Verify health

```bash
cd ~/gbrain && bun run src/cli.ts doctor
```

## Pitfalls

- ❌ **Don't try to fix in place** — removing `postmaster.pid` alone won't help if the WAL is corrupt. The WASM crash is a hard postmaster failure during recovery.
- ❌ **Don't delete the brain markdown files** — they are the source of truth; PGLite is just the search index.
- ❌ **Sync without `--repo` silently says nothing useful** — even with `local_path` set, it outputs "No repo path specified."
- ❌ **Fresh DB has no dream config** — after recovery, re-set `dream.synthesize.enabled`, `brain.dir`, and any other custom configs.
- ❌ **The old pglite directory at `~/.gbrain/pglite/` is an unrelated empty database** — not the same as `brain.pglite`. Don't confuse them.

## Verification: Don't Trust Cron Reports, Trust `gbrain doctor`

When PGLite is dead, the autopilot daemon enters a death-spiral restart loop. A cron job that reads the autopilot log might report:

> "Recovery underway: ... Re-sync in progress — importing 18,741 files at ~2/sec..."

This is **misleading** — the daemon is restarting, not re-syncing. ALL gbrain commands that touch the DB fail uniformly with `Aborted()`. No sync or embed can possibly happen while PGLite's WASM runtime is broken.

**Always verify the actual state yourself before reporting recovery progress:**
1. `gbrain doctor` — if it shows `[WARN] connection: Could not connect to configured DB`, the DB is dead
2. Every `gbrain sync`, `gbrain embed`, `gbrain init` call fails — the daemon is thrashing, not working
3. If `gbrain doctor` fails, no recovery step that touches PGLite will succeed

The ONLY signals that count:
- `gbrain doctor` shows green connection → PGLite alive
- The import-checkpoint.json changes over time → sync actually running
- `systemctl --user status gbrain-autopilot.service` shows `Active: active (running)` and stays there → daemon stable

## When to Migrate to Supabase (Instead of Local Recovery)

If this is the **2nd+ corruption event**, prefer switching to an existing Supabase project over local PGLite recovery.

**Signs of chronic PGLite instability:**
- Multiple corruption backups exist (`brain.pglite.corrupted-YYYYMMDD` directories pile up)
- Corruption happens on every ungraceful shutdown
- The machine is WSL (where WASM runtime termination is common)

**PGLite local recovery cost:** 2-3 hours of re-sync for ~18K files.
**Supabase switch cost:** ~5 minutes of config editing (if the Supabase project already has gbrain schema + data).

See `supabase-db-recovery.md` → "Recovery Path A-Prime: Switch Back to Existing Supabase" for the expedited procedure.

## Related

- `pglite-sync-lock-troubleshooting.md` — Stale lock management (lighter-weight issue)
- `dream-cycle-config.md` — Re-applying dream cycle configs after recovery
