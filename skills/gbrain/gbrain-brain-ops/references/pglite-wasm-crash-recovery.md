# PGLite WASM Crash Recovery

## Incident: 2026-06-11 — WSL2 Kernel Upgrade Breaks PGLite

### Timeline

- **Jun 5, 2026** — WSL2 kernel upgraded to `6.18.33.1-microsoft-standard-WSL2` (WSL 2.7.8.0)
- **Jun 10, 2026** — System ran fine, no apparent issues
- **Jun 11, 07:20** — WSL reboot (new boot after either Windows restart or WSL shutdown/restart)
- **Jun 11, 07:26+** — All gbrain cron jobs start failing with PGLite WASM abort

### Symptoms

Every gbrain operation that touches the database fails with:
```
PGLite failed to initialize its WASM runtime.
  This is most commonly the macOS 26.3 WASM bug: https://github.com/garrytan/gbrain/issues/223
  Run `gbrain doctor` for a full diagnosis.
  Original error: Aborted(). Build with -sASSERTIONS for more info.
```

**Affected cron jobs (all failing):**
| Job | Schedule | Failure Point |
|-----|----------|--------------|
| gbrain-live-sync (job 7269004d4020) | `*/15 * * * *` | `gbrain sync --repo ~/brain` fails at PGLite init |
| Collect Gmail to gbrain (job 8f11ab6b488a) | `0 8-19 * * 1-5` | Emails collected to disk, PGLite fails on write |
| Collect Calendar to gbrain (job 61c26c8d91d0) | `0 8-19 * * 1-5` | Events collected to disk, PGLite fails on write |
| gbrain autopilot (crontab) | `*/5 * * * *` | Repeated PGLite init failure |

Also indirectly affected:
- **Signal Monitor Watchdog** (job 7aadcadab060) — timed out after 120s because `gateway-signal-monitor.sh` is an infinite loop (while-true + sleep 5), designed as a daemon but configured as a cron `no_agent` script. This is a configuration bug, not a WASM issue.

### System State

```
Kernel:      6.18.33.1-microsoft-standard-WSL2 (x86_64)
WSL version: 2.7.8.0
Node:        v22.22.3
Bun:         1.3.14
PGlite:      @electric-sql/pglite@0.4.3
gbrain:      0.40.2.0
Data dir:    ~/.gbrain/brain.pglite (488MB, PG_VERSION=17)
Config:      engine: pglite, database_path: /home/tapway/.gbrain/brain.pglite
```

### Diagnosis Commands

Use these for quick triage in future incidents:

```bash
# 1. Check if PGLite CAN work at all (in-memory test)
cd ~/gbrain
export PATH="/home/tapway/.hermes/node/bin:$PATH"
bun -e "
const { PGlite } = require('@electric-sql/pglite');
const db = new PGlite();
db.query('SELECT 1').then(r => console.log('IN-MEMORY: OK')).catch(e => console.error('IN-MEMORY: FAIL'));
"

# 2. Check file-backed (the real test)
bun -e "
const { PGlite } = require('@electric-sql/pglite');
try {
  const db = new PGlite('/home/tapway/.gbrain/brain.pglite');
  db.query('SELECT 1').then(r => console.log('FILE-BACKED: OK')).catch(e => console.error('FILE-BACKED: FAIL:', e.message));
} catch(e) { console.error('FILE-BACKED: FAIL:', e.message); }
"

# 3. Try PGlite.create() (what gbrain actually uses)
bun -e "
const { PGlite } = require('@electric-sql/pglite');
const { vector } = require('@electric-sql/pglite/vector');
PGlite.create({
  dataDir: '/home/tapway/.gbrain/brain.pglite',
  extensions: { vector }
}).then(db => db.query('SELECT 1')).then(r => console.log('PGLITE.CREATE: OK')).catch(e => console.error('PGLITE.CREATE: FAIL:', e.message));
"

# 4. Remove stale postmaster.pid and retry
rm -f /home/tapway/.gbrain/brain.pglite/postmaster.pid
# Then retry test #2 or #3

# 5. Test fresh database (confirms PGLite itself works)
bun -e "
const { PGlite } = require('@electric-sql/pglite');
const db = new PGlite('/tmp/test-pglite');
db.query('CREATE TABLE IF NOT EXISTS test (id int); INSERT INTO test VALUES (42); SELECT * FROM test')
  .then(r => console.log('FRESH DB: OK', JSON.stringify(r.rows)))
  .catch(e => console.error('FRESH DB: FAIL:', e.message));
rm -fr /tmp/test-pglite
"

# 6. Check cron job status
hermes cron list

# 7. Check gbrain config
cat ~/.gbrain/config.json
```

### Key Diagnostic Finding

**In-memory PGLite: OK.** Fresh persistent DB (temp dir): **OK.**
**Existing persistent DB (`~/.gbrain/brain.pglite`): FAIL — Aborted().**

This pattern — `new PGlite()` works, `new PGlite('/path/to/existing/data')` fails — means the data directory is incompatible with the current WASM runtime. The WSL2 kernel upgrade changed something about how WASM handles file I/O or memory mapping for persistent storage.

### Root Cause Hypothesis

The WSL2 kernel upgrade from the previous version to `6.18.33.1` likely changed:
- **WASM memory mapping behavior** — PGLite uses WASM to run a full PostgreSQL instance. The WASM runtime maps the PostgreSQL shared buffers and WAL files. A kernel change in how `mmap` handles `MAP_ANONYMOUS` + `MAP_SHARED` for WASM could break existing data dirs.
- **Seccomp behavior** — The new kernel may apply stricter seccomp profiles for WASM execution. Even though `/proc/self/status` shows `Seccomp: 0`, the WSL hypervisor layer could impose restrictions visible only to WASM.

### Recovery Paths

**Path A: Migrate to native PostgreSQL in WSL** (recommended)
1. `apt install postgresql postgresql-contrib`
2. Create database user and database for gbrain
3. Enable `pgvector` extension
4. Point gbrain at the Postgres connection string (update `~/.gbrain/config.json`)
5. Run `gbrain sync --repo ~/brain` — full re-import from files
6. Re-enable all gbrain cron jobs

See `brain-database-migration` skill for detailed setup steps, vector search configuration, and HNSW index build.

**Path B: Re-init PGLite from scratch** (faster but less durable)
1. `mv ~/.gbrain/brain.pglite ~/.gbrain/brain.pglite.corrupted.$(date +%Y%m%d)`
2. gbrain will auto-create a new data dir on next `sync` call
3. Run `gbrain sync --repo ~/brain` — full re-import from files
4. All embeddings must be regenerated (embedding API cost + latency)

**Path C: Restore from gbrain DB backup** (if available)
Check `state-snapshots/` or any `.bak`/`.backup` files in `~/.gbrain/`.
→ Restore the data directory, test with the PGLite in-memory test above.