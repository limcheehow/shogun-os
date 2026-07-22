# Session DB Locking Incident — June 8, 2026

## Timeline

1. Gateway found dead at 09:19 — tmux server vanished, no shutdown log (likely SIGKILL)
2. Gateway restarted at 09:25, 09:50, 10:56 (multiple restarts for config changes)
3. User reports "session manager locked" across all chats
4. Errors log shows 40s timeouts on session_search with "locking protocol"
5. 350MB state.db had stale -wal and -shm files from unclean shutdowns
6. Removing WAL files didn't fix — database was corrupted ("database disk image is malformed")
7. Moved corrupted state.db aside (350MB), gateway recreated fresh one on restart
8. Issue resolved after restart

## Key Evidence

```
2026-06-08 11:25:14 WARNING: Tool session_search returned error (40.04s):
"Session database not available: OperationalError: locking protocol"
2026-06-08 11:38:34 WARNING: Tool session_search returned error (40.02s):
"Session database not available: OperationalError: locking protocol"
2026-06-08 11:40:10 WARNING: Tool session_search returned error (40.02s):
"Session database not available: OperationalError: locking protocol"
```

Three failures in 15 minutes, each blocking the agent for 40 seconds.

## Resolution

**What DIDN'T work:**
- Cleaning WAL files alone — DB was still corrupted
- Deleting state.db and letting gateway recreate — fresh DB was 0 bytes, session_search still failed
- Symlink to `/dev/shm` — session_search ignored the symlink
- Multiple gateway restarts — agent process held stale in-memory connection

**What DID work — restore from pre-update snapshot:**

```bash
# Step 1: Verify snapshot integrity
ls ~/.hermes/state-snapshots/
# Found: 20260607-062201-pre-update (351MB, WAL journal, integrity OK, 1535 sessions)

# Step 2: Restore
rm -f ~/.hermes/state.db ~/.hermes/state.db-*
cp ~/.hermes/state-snapshots/20260607-062201-pre-update/state.db ~/.hermes/state.db

# Step 3: Restart gateway + agent session
# Gateway restart alone NOT sufficient — agent's SessionDB holds stale connection
# Need /new or CLI restart for session_search to pick up restored DB
```

**Verification from Python (before agent restart — DB is fine but agent can't see it):**
```
Journal: ('wal',)
Integrity: ('ok',)
Sessions: 1535
Messages: 22685
```

## Root Cause Chain

1. Multiple `kill -9` gateway restarts in one morning interrupt SQLite writes
2. Database header corrupted — not just WAL files
3. WAL cleanup insufficient; fresh DB creation fails on wslfs
4. session_search fails with "database disk image is malformed" — 40s timeouts
5. Pre-update snapshots at `~/.hermes/state-snapshots/` are the recovery path
6. Agent process MUST restart after DB restore — stale SessionDB connection persists

## Prevention

- Avoid `kill -9` — prefer `tmux kill-session -t hermes-gateway` (SIGINT)
- Snapshots are created before Hermes upgrades — they're the last-known-good state
- If `kill -9` was used and session_search breaks, go straight to snapshot restore