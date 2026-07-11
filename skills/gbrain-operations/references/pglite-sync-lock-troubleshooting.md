# PGLite Sync Lock Troubleshooting

## Symptom

Running `gbrain sync` fails with:

```
Another sync is in progress (lock gbrain-sync held). Wait for it to finish, or run 'gbrain doctor' if it has been more than 30 minutes.
```

Even after the original sync process has died or timed out.

## Root Cause

gbrain stores sync locks in the `gbrain_cycle_locks` table inside the PGLite database. When a sync process crashes or times out without releasing its lock, the stale lock row persists with a 30-minute TTL.

The original process (PID) is dead but the lock row lives on.

## Fix

Manually delete the stale lock row from the PGLite database:

1. Create a small script at `/tmp/release-lock.ts`:

```typescript
import { PGlite } from '@electric-sql/pglite';

async function main() {
  const dbPath = process.env.HOME + '/.gbrain/brain.pglite';
  const db = new PGlite(dbPath, { dataDir: dbPath });
  
  // Check current locks
  const locks = await db.query(
    'SELECT id, holder_pid, ttl_expires_at FROM gbrain_cycle_locks'
  );
  console.log('Current locks:', JSON.stringify(locks.rows, null, 2));

  // Delete the stale sync lock
  await db.query("DELETE FROM gbrain_cycle_locks WHERE id = 'gbrain-sync'");
  console.log('Deleted gbrain-sync lock');
  
  await db.close();
}
main().catch(e => console.error(e));
```

2. Run it from the gbrain project directory:
```bash
cd ~/gbrain && bun run /tmp/release-lock.ts
```

3. Clean up:
```bash
rm /tmp/release-lock.ts
```

4. Retry the sync with the correct environment variables (see SKILL.md for the full command with Backup Provider key).

## Prevention

- Large syncs with 5000+ files may exceed the default 300s timeout. Run in background with `notify_on_complete: true` and a `timeout` of 600s or more.
- gbrain doctor (`bun run src/cli.ts doctor`) does NOT automatically clear stale sync locks — it only checks health.
- The lock table is `gbrain_cycle_locks` (used for both `gbrain-cycle` and `gbrain-sync` lock types).
- Always run sync with `OPENROUTER_API_KEY` set and `OPENAI_API_KEY` cleared to avoid 429 embedding errors that slow the sync down.
