# Hermes Session Database Duality — Partial Postgres Migration

> Date: 2026-06-11
> Context: User reported Postgres was migrated but "database disk image is malformed" errors persisted. Investigation revealed the migration was partial.

## The Core Problem

Hermes has **two independent session databases** that serve different components:

| # | Component | File | Purpose |
|---|-----------|------|---------|
| 1 | **Gateway SessionStore** | `gateway/session.py` | Session indexing, routing, key→ID mapping |
| 2 | **Gateway `_session_db`** | `gateway/run.py` | `session_search`, FTS, telegram topics, handoffs, titles |
| 3 | **Agent loop fallback** | `run_agent.py` | Session creation, message append, undo/rewind |

Only #1 was migrated to Postgres. #2 and #3 still use the SQLite `state.db` which corrupts on WSL.

## Diagnostic Walkthrough (as performed 2026-06-11)

### Step 1 — Check what the gateway actually reports

```bash
grep "Session storage:" ~/.hermes/logs/gateway.log | tail -3
```

Always shows `~/.hermes/sessions` directory. This is the JSONL fallback path. It is NOT evidence that Postgres failed — it's the directory where session indexes live regardless of backend.

### Step 2 — Check tmux pane for hidden errors

The gateway's SessionDB init uses `print()` (not `logger`) for errors, so they never reach `gateway.log`:

```bash
tmux capture-pane -t hermes-gateway -p -S -200 2>/dev/null | grep -i "Session DB\|database disk image\|FOREIGN KEY\|falling back"
```

If you see:
- `Session DB creation failed (will retry next turn): database disk image is malformed` → the agent's `_session_db` is hitting corrupted SQLite
- `Session DB append_message failed: FOREIGN KEY constraint fail` → session wasn't created in Postgres before messages were appended

### Step 3 — Find the import sites

```bash
grep -n "from hermes_state import SessionDB\|from hermes_state_pg import SessionDB" \
  ~/.hermes/hermes-agent/gateway/run.py \
  ~/.hermes/hermes-agent/gateway/session.py \
  ~/.hermes/hermes-agent/run_agent.py \
  ~/.hermes/hermes-agent/hermes_cli/main.py \
  ~/.hermes/hermes-agent/hermes_cli/goals.py 2>/dev/null
```

Key locations found on 2026-06-11:

| File | Line | Import | Patched? |
|------|------|--------|----------|
| `gateway/session.py` | 688 | `from hermes_state_pg import SessionDB` | ✅ Yes |
| `gateway/run.py` | 2046 | `from hermes_state import SessionDB` | ❌ No |
| `run_agent.py` | 497 | `from hermes_state import SessionDB` | ❌ No (fallback) |
| `hermes_cli/main.py` | 989, 1128, 1181, 15092 | `from hermes_state import SessionDB` | ❌ No |
| `hermes_cli/goals.py` | 220 | `from hermes_state import SessionDB` | ❌ No |

### Step 4 — Verify Postgres actually works

```bash
python3 -c "
import sys
sys.path.insert(0, '/home/tapway/.hermes/hermes-agent')
from hermes_state_pg import SessionDB
db = SessionDB()
print(f'Postgres sessions: {db.session_count()}')
"
```

On 2026-06-11 this returned 830 sessions. Postgres was working — the gateway SessionStore was using it — but the agent loop was not.

### Step 5 — Check method coverage gap

The gateway calls 27 distinct methods on `self._session_db` in `run.py`. The Postgres module only implements ~21. That means even if you switch the import, several features break:

```bash
# Methods called on self._session_db in run.py
grep -oP 'self\._session_db\.\w+' ~/.hermes/hermes-agent/gateway/run.py | sort -u

# Methods defined in hermes_state_pg.SessionDB  
grep -oP 'def \w+' ~/.hermes/hermes-agent/hermes_state_pg.py | sort -u
```

Missing methods include: `is_telegram_topic_mode_enabled`, `bind_telegram_topic`, `list_pending_handoffs`, `claim_handoff`, `complete_handoff`, `fail_handoff`, `get_compression_tip`, `get_session`, `get_session_title`, `set_session_title`, `list_sessions_rich`, `resolve_session_id`, `resolve_session_by_title`, `resolve_resume_session_id`, `sanitize_title`, `enable_telegram_topic_mode`, `disable_telegram_topic_mode`, `get_telegram_topic_binding`, `get_telegram_topic_binding_by_session`, `is_telegram_session_linked_to_topic`, `list_unlinked_telegram_sessions_for_user`, `maybe_auto_prune_and_vacuum`.

## The Module Architecture

```python
# File: ~/.hermes/hermes-agent/hermes_state_pg.py

PG_HOST = "127.0.0.1"
PG_PORT = 5432
PG_USER = "hermes"
_PG_PASS_B64 = "aGVybWVzX3Mzc3Npb25zXzIwMjY="  # base64("hermes_s3ssions_2026")
PG_DATABASE = "hermes_sessions"
```

Connects via TCP to localhost Postgres using scram-sha-256 auth. The password is base64-encoded to avoid Hermes' secret redaction filter.

The `SessionDB` class has a module-level connection singleton (`_connection = None`) with a thread lock. Schema is auto-created on first init via `_init_schema()`.

## Data State (2026-06-11)

| Source | Sessions | Messages | Notes |
|--------|----------|----------|-------|
| Postgres `hermes_sessions` | 830 | 17,613 | Mostly cron jobs (540), some Slack (227), few Telegram (56) |
| SQLite `state.db` (corrupted) | ~1,571 (before corruption) | ~23,602 | Includes Slack (418), Telegram (84) — most recent from June 10 |
| JSONL `~/.hermes/sessions/` | 0 | 0 | Empty — gateway never wrote to JSONL on this system |
| `state.db.pre-wsl2-backup` | 1,571 | 23,602 | Clean (0 integrity errors), 353MB |

The **pre-wsl2-backup** is the best recovery source for the SQLite path. It has more sessions than Postgres including Telegram and Slack conversations.

## Recovery Commands

### Check backup health

```bash
for f in ~/.hermes/state.db.pre-*; do
  [ -f "$f" ] && echo -n "$(basename $f): " && \
  sqlite3 "$f" "PRAGMA integrity_check;" 2>&1
done
```

### Restore from clean backup

```bash
# Stop gateway first (user permission required)
tmux kill-session -t hermes-gateway 2>/dev/null

# Backup current corrupted file
cp ~/.hermes/state.db ~/.hermes/state.db.corrupted.$(date +%Y%m%d-%H%M%S)

# Restore
cp ~/.hermes/state.db.pre-wsl2-backup ~/.hermes/state.db

# Clean stale WAL/SHM
rm -f ~/.hermes/state.db-wal ~/.hermes/state.db-shm

# Verify
sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"
sqlite3 ~/.hermes/state.db "SELECT COUNT(*) FROM sessions;"
sqlite3 ~/.hermes/state.db "SELECT COUNT(*) FROM messages;"

# Restart gateway
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
```

## Complete Import Site List

For a full Postgres migration, patch ALL these locations:

1. `gateway/session.py:688` — ✅ Already done
2. `gateway/run.py:2046` — `from hermes_state import SessionDB` → `from hermes_state_pg import SessionDB`
3. `run_agent.py:497` — fallback in `_get_session_db_for_recall()`
4. `hermes_cli/main.py:989` — CLI session commands
5. `hermes_cli/main.py:1128` — CLI session commands
6. `hermes_cli/main.py:1181` — CLI session commands
7. `hermes_cli/main.py:15092` — CLI session commands
8. `hermes_cli/goals.py:220` — GoalManager

Also: the gateway code at `run.py:2036-2044` calls `cleanup_gateway_wal()` (SQLite WAL/SHM cleanup) and `PRAGMA wal_checkpoint(TRUNCATE)` — these are SQLite-specific and must be guarded when switching to Postgres.
