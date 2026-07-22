# state.db Corruption from Stale Gateway After Postgres Migration

> Full incident: 2026-06-12. Postgres session store migration completed in code but gateway was never restarted. Old gateway ran for 4+ days with state.db, which grew to 359MB and catastrophically corrupted. Combined with Telegram network instability, response times exploded to 50 minutes.

## Timeline

```
June 10 23:33  → Gateway clean shutdown (old code, using state.db SQLite)
June 11 am     → Gateway restarts (still old code, still state.db)
June 11 18:24  → state.db becomes CORRUPTED (359MB, last modified timestamp)
June 11 pm     → Telegram reconnects every 12-20 min (6 times in 1 hour)
June 12 09:45  → Telegram timeout cascade begins (63 errors total)
June 12 11:06  → "session DB hiccup" — state.db corruption prevents session load
June 12 11:48  → 597s response time
June 12 12:36  → 2,232s response time
June 12 13:28  → 3,015s (50 min) response time — 1 API call
June 12 13:53  → Cron agent: "database disk image is malformed" + 50min wasted tokens
June 12 14:33  → Gateway FINALLY restarted → now uses Postgres (hermes_state_pg)
June 12 14:40  → Two more watchdog restarts (SIGINT/SIGTERM), then stable
```

## Root Cause Chain

1. Postgres migration was done in code (all 3 session DB handles switched to `hermes_state_pg`)
2. Gateway was never restarted — old process kept using `hermes_state` (SQLite state.db)
3. state.db grew to 359MB — at this size, SQLite is vulnerable to corruption
4. state.db became corrupted — `btreeInitPage() returns error code 11` (SQLITE_CORRUPT), 100+ orphan pages
5. Every session operation hit corrupted DB — session loading, session_search, message history, topic bindings, handoff — ALL returned errors
6. Telegram network instability compounded — messages queued behind failed sends

## Evidence Collected

### Check state.db integrity
```bash
sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"
# Output: btreeInitPage() returns error code 11 (SQLITE_CORRUPT)
#         100+ pages "never used"
#         Child page depth differs
```

### Check Postgres tables exist
```bash
PGPASSWORD='***' psql -h localhost -U hermes -d hermes_sessions -c "\dt"
# 11 tables: pg_session_sessions, pg_session_messages, pg_session_meta, etc.
```

### Verify all three session DB handles use Postgres
```bash
grep -n "from hermes_state_pg import" gateway/session.py gateway/run.py run_agent.py
# gateway/session.py:688 → SessionStore uses SessionDB from hermes_state_pg
# gateway/run.py:2037    → _session_db uses SessionDB from hermes_state_pg
# run_agent.py:497       → agent fallback uses SessionDB from hermes_state_pg
```

### Confirm nothing reads state.db post-restart
```bash
lsof ~/.hermes/state.db
# (no output — nothing has it open after gateway restart)
```

## Diagnostic Checklist

When user reports session amnesia, extreme latency, or "database disk image is malformed":

1. **Check state.db integrity**: `sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"`
2. **Check Postgres tables exist**: connect to `hermes_sessions` DB, run `\dt`
3. **Check which code is imported**: grep for `hermes_state_pg` vs `hermes_state` in gateway/*.py
4. **Check gateway uptime**: `ps -p <gateway_pid> -o etime` — compare against migration date
5. **Check if state.db is open**: `lsof ~/.hermes/state.db` — if nothing, gateway switched to Postgres
6. **Check recent gateway restarts**: `grep "Gateway running" ~/.hermes/logs/gateway.log | tail -5`

## Resolution

1. Restart the gateway (with user permission) — watchdog handles the restart
2. Verify Postgres is active: check `response ready` lines appear with normal latencies
3. Archive corrupted state.db: `mv ~/.hermes/state.db ~/.hermes/state.db.corrupted-backup`
4. Old session history in state.db is unrecoverable — SQLite integrity check fails catastrophically

## Pitfalls

- **The "Session storage:" log line is NOT a backend indicator.** `gateway/run.py` logs `Session storage: ~/.hermes/sessions/` regardless of whether Postgres or SQLite backs it. Check actual imports and `lsof` instead.
- **Gateway running ≠ using new code.** If the gateway was started before a code change (pip install, code edit, migration), it's running old code. Only reliable check is process start time vs code change time.
- **The password for `hermes` Postgres user is base64-encoded** in `hermes_state_pg.py` at line 30: `_PG_PASS_B64 = "aGVybWVzXzNzc3Npb25zXzIwMjY="`. Decode before using in psql.