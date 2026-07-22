---
name: hermes-data-migration
description: Migrate Hermes Agent internal data stores between backends (SQLite → PostgreSQL, or similar). Covers the architecture-aware approach needed because Hermes has multiple independent session databases.
category: devops
tags: [hermes, postgres, sqlite, migration, database, session]
---

# Hermes Internal Data Migration

Load this skill when migrating one of Hermes' internal data stores (session DB, kanban DB, cron DB, gbrain) from one backend to another — particularly SQLite → PostgreSQL.

## Architecture: Two Independent Session Databases

Hermes has TWO separate session stores that must be migrated independently:

| Layer | File | Used By | Purpose |
|-------|------|---------|---------|
| **Gateway SessionStore** | `gateway/session.py` | Session routing, indexing, platform message tracking | Uses `self._db` — migrates via patch to `from hermes_state_pg import SessionDB` |
| **Agent _session_db** | `gateway/run.py` + `run_agent.py` | FTS, undo, session search, telegram topics, handoffs, titles, token counts | Injected into AIAgent at `run.py:12729` — needs both the gateway init AND the agent fallback |

The gateway SessionStore was migrated first (it was already partially done). The agent `_session_db` requires a bigger effort because **the gateway's own `_session_db`** (init at `run.py:2046`) and **the agent's fallback** (`run_agent.py:497`) both import from `hermes_state` (SQLite).

**Critical finding:** The gateway passes its `_session_db` directly to `AIAgent` at `run.py:12729` — so fixing `run.py:2046` automatically fixes the agent path. But the agent's fallback at `run_agent.py:497` still needs patching for standalone CLI usage.

## Migration Steps

### 1. Build the New Backend Module

Create `hermes_state_pg.py` as a drop-in replacement for `hermes_state.SessionDB`. It must implement ALL methods that any caller uses:

```python
from hermes_state_pg import SessionDB
```

The full method surface is ~45 methods across 24+ files. Use `grep -rn "from hermes_state import"` to find all call sites.

### 2. Schema Migration: Existing Tables

**CRITICAL PITFALL:** `CREATE TABLE IF NOT EXISTS` does NOT backfill DEFAULT constraints on tables that already exist. If you add a DEFAULT to a column that was previously created without one, you must ALTER TABLE separately:

```python
def _init_schema(self):
    # CREATE TABLE IF NOT EXISTS handles new databases
    cur.execute(SCHEMA_SQL)
    
    # BUT existing tables need explicit ALTER for new defaults
    cur.execute(
        "SELECT column_default FROM information_schema.columns "
        "WHERE table_name = 'sessions' AND column_name = 'started_at'"
    )
    row = cur.fetchone()
    if row and row[0] is None:
        cur.execute("ALTER TABLE ... ALTER COLUMN ... SET DEFAULT ...")
```

### 3. psycopg2 Dict Serialization

psycopg2 cannot adapt Python `dict` or `list` values to Postgres parameters. Any `**kwargs` passed through `create_session()` or `ensure_session()` that contains a dict value (like `model_config`) will fail with `can't adapt type 'dict'`:

```python
for key, val in kwargs.items():
    if val is not None:
        if isinstance(val, (dict, list)):
            val = json.dumps(val)  # REQUIRED for psycopg2
        vals.append(val)
```

### 4. Import Path Sweeping

After building the backend module, replace every `from hermes_state import SessionDB` with `from hermes_state_pg import SessionDB` across the codebase. The most reliable way:

1. Find ALL occurrences: `grep -rn "from hermes_state import" --include="*.py" | grep -v "/tests/" | grep -v "/venv/"`
2. Use `patch` with `replace_all=true` per file
3. Keep `apply_wal_with_fallback` imports (SQLite-specific, used by kanban_db and holographic memory)
4. Keep `format_session_db_unavailable` unless you also add it to the new module

Files to patch (complete list from the 2026-06-11 migration):
- `gateway/run.py` (2 locations: _session_db init + _session_db for insights/title)
- `run_agent.py` (1: fallback `_get_session_db_for_recall`)
- `cli.py` (6: SessionDB imports + format_session_db_unavailable)
- `hermes_cli/main.py` (5: SessionDB imports)
- `hermes_cli/goals.py` (1: GoalManager)
- `hermes_cli/web_server.py` (16: dashboard endpoints)
- `hermes_cli/oneshot.py` (1: SessionDB factory)
- `tools/session_search_tool.py` (3: SessionDB + requirements check)
- `agent/tool_executor.py` (1: format_session_db_unavailable)
- `agent/agent_runtime_helpers.py` (1: format_session_db_unavailable)
- `gateway/mirror.py` (1: message mirroring)
- `gateway/platforms/api_server.py` (1: API server session db)
- `gateway/session.py` (1: SessionStore._db)
- `cron/scheduler.py` (1: cron session db)
- `tui_gateway/server.py` (4: TUI dashboard)
- `acp_adapter/session.py` (1: ACP adapter)
- `mcp_serve.py` (1: MCP server)
- `plugins/hermes-achievements/.../plugin_api.py` (1: achievements dashboard)

### 5. Testing

```python
from hermes_state_pg import SessionDB
db = SessionDB()

# Test core CRUD
assert db.session_count() > 0
assert db.get_session('some-existing-id') is not None
assert db.resolve_session_id('some-existing-id') is not None

# Test new methods
assert db.get_session_title('some-existing-id') is not None or False
assert db.is_telegram_topic_mode_enabled(chat_id='test', user_id='test') is False
assert db.list_pending_handoffs() == []

# Test token updates (both modes)
db.update_token_counts('some-existing-id', input_tokens=10, output_tokens=5, absolute=False)
db.update_token_counts('some-existing-id', input_tokens=42, output_tokens=7, absolute=True)

# Test handoff flow
db.request_handoff('some-existing-id', 'telegram')
assert db.get_handoff_state('some-existing-id') is not None
db.complete_handoff('some-existing-id')
```

### 6. Schema: New Tables for Postgres

The Postgres schema needs these additional tables beyond what SQLite used:

```sql
CREATE TABLE IF NOT EXISTS telegram_dm_topic_mode ( ... );
CREATE TABLE IF NOT EXISTS telegram_dm_topic_bindings ( ... );
```

Plus additional indexes: `idx_sessions_parent`, `idx_compression_locks_expires`, `idx_messages_platform_msg_id`, `idx_telegram_dm_topic_bindings_session`, `idx_telegram_dm_topic_bindings_user`.

## Verification

```bash
# Check gateway uses Postgres (no SQLite errors)
grep "database disk image\|malformed\|SQLite.*not available" ~/.hermes/logs/gateway.log | grep "$(date +%H)" || echo "Clean"

# Send a test message from Telegram/Slack and verify session in Postgres
sudo -u postgres psql -d hermes_sessions -c "SELECT id, source, started_at FROM sessions ORDER BY started_at DESC LIMIT 3;"

# Check the gateway log for Session DB errors
tail -20 ~/.hermes/logs/gateway.log | grep -i "session db"
```

## Pitfalls

- **`started_at` NOT NULL DEFAULT won't auto-apply to existing tables** — The `DEFAULT (extract(epoch from now()))` in `CREATE TABLE IF NOT EXISTS` only applies to newly created tables. For existing databases, ALTER TABLE is required. See step 2.
- **psycopg2 rejects Python dicts as parameters** — Unlike SQLite (which auto-stringifies), psycopg2 raises `can't adapt type 'dict'`. Always `json.dumps()` dict/list values before using them as INSERT/UPDATE parameters.
- **Two code paths for session creation** — Gateway passes `self._session_db` into AIAgent at `run.py:12729`. If the gateway's init fails, the agent falls back to its own import at `run_agent.py:497`. Both must be patched.
- **Your own shell matches `pgrep -f` patterns** — When using `pgrep -f "hermes gateway run" | xargs kill -9`, the command itself may match the pgrep pattern, killing your own terminal session with SIGKILL (-9). Always use targeted PID kill: `ps aux | grep "hermes gateway run" | grep -v grep | awk '{print $2}' | head -1 | xargs kill -9`.
- **`format_session_db_unavailable` must also be in the new module** — Several callers (cli.py, run.py, session_search_tool.py, tool_executor.py, agent_runtime_helpers.py) import this function separately from SessionDB. Add it to `hermes_state_pg.py` or keep importing from `hermes_state` for that specific function.
- **Kanban and holographic memory stay on SQLite** — `hermes_cli/kanban_db.py` and `plugins/memory/holographic/store.py` use `apply_wal_with_fallback` which is SQLite-specific. Do NOT switch those imports to Postgres.
- **Old corrupted state.db lingers on disk** — Post-migration, the corrupted SQLite `state.db` (~359MB) can be kept for forensics or deleted to reclaim space. Its WAL/SHM files also persist. The gateway no longer touches these files.

## Reference: Real Migration (June 2026)

See `references/2026-06-11-session-migration.md` for the actual transcript of the Hermes session storage migration — all 24+ files changed, bugs found during the process, and the post-migration state.