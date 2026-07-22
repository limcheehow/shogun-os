# 2026-06-12: state.db Corruption + Background Review Incident

## Timeline

```
June 10 23:33  → Gateway clean shutdown (old code, state.db active)
June 11 am     → Gateway restarts (still state.db — code path uses old SQLite)
June 11 18:24  → state.db becomes CORRUPTED (SQLITE_CORRUPT, 100+ orphan pages)
June 11 pm     → Telegram reconnects every 12-20 min (6 times in 1 hour)
June 12 09:45  → Telegram timeout cascade begins (63 total errors)
June 12 11:06  → "session DB hiccup" — state.db corruption prevents session load
June 12 11:48  → 597s response time (messages stuck behind network + DB failures)
June 12 12:36  → 2,232s response time
June 12 13:28  → 3,015s (50 min) response time — messages backing up
June 12 13:53  → Cron agent: "database disk image is malformed" + 50min wasted
                 tokens from background self-improvement review forks
June 12 14:33  → Gateway FINALLY restarted → now uses Postgres (hermes_state_pg)
June 12 14:34  → Current user session: "gateway slow again" — investigation begins
```

## Root Cause Chain

```
Postgres migration done (code written, Postgres tables created)
  → Gateway NEVER restarted
    → Old gateway kept hitting SQLite state.db for EVERY session operation
      → state.db grew to 359MB → corrupted (June 11)
        → Every session lookup failed silently
          → Session amnesia in chats
            → Background review forks fired every 10 agent turns (default)
              → 3-5 forks per cron job × 16 API calls each = 50 min wasted tokens
                → All competing on same API key = gateway bandwidth eaten
                  → Telegram timeouts cascaded → 50-minute response times
```

## Key Evidence

### SQLite Integrity Check

```
$ sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"
*** in database main ***
Page 90812: btreeInitPage() returns error code 11
Page 2881: btreeInitPage() returns error code 11
On tree page 3 cell 1: Child page depth differs
Page 3116: btreeInitPage() returns error code 11
...100+ "Page N is never used" lines...
```

### Background Review Code Path

`agent/background_review.py` (`_run_review_in_thread`):
- Spawns `AIAgent(max_iterations=16)` as a daemon thread
- Inherits parent's model, provider, credentials, cached system prompt
- Restricted to `memory` and `skills` toolsets only
- Sets `set_thread_tool_whitelist()` — blocks ALL non-skill/memory tools for the duration
- Pitfall: if the review crashes, the `finally: clear_thread_tool_whitelist()` may not fire,
  leaving the parent session's thread unable to call terminal, read_file, write_file, etc.

```
review_whitelist = {t["function"]["name"] for t in get_tool_definitions(
    enabled_toolsets=["memory", "skills"], quiet_mode=True
)}
set_thread_tool_whitelist(review_whitelist, deny_msg_fmt="...Only memory/skill tools...")
```

### State of ALL Session DB Handles Post-Migration

| Handle | File | Current Import | Status |
|---|---|---|---|
| Gateway SessionStore | `gateway/session.py:688` | `from hermes_state_pg import SessionDB` | ✓ Postgres |
| Gateway `_session_db` | `gateway/run.py:2037` | `from hermes_state_pg import SessionDB` | ✓ Postgres |
| Agent fallback | `run_agent.py:497` | `from hermes_state_pg import SessionDB` | ✓ Postgres |

### Config Change Applied

```yaml
skills:
  creation_nudge_interval: 0   # added 2026-06-12

memory:
  nudge_interval: 0            # added 2026-06-12
```

### Cleanup Summary

| Action | Detail |
|---|---|
| state.db archived | `~/.hermes/state.db` → `state.db.corrupted-backup` (359MB) |
| Old skeletons deleted | 4.7GB of corrupted backups, snapshots, pre-vacuum copies |
| Backup script updated | `hermes-backup.sh` — state.db section removed, manifest updated |
| Gateway restarted | Telegram + Slack connected in 7s (was 65s) |

## Lessons Learned

1. **A migration is not done until the process is restarted** — code change ≠ activation
2. **Three handles, not one** — Postgres migration needs all three session DB entry points audited
3. **Background review at default 10 turns is too aggressive** — every cron job with 30+ turns spawns 3+ review forks that burn tokens for 50+ minutes
4. **The pgrep trap** — `pgrep -f "hermes gateway run"` in terminal() matches the CLI session itself, causing self-termination. Always use explicit PIDs from a separate `ps aux` check.
5. **Telegram timeouts are cumulative** — 63 timeout errors cascade into 50-minute response delays as messages queue behind failed sends