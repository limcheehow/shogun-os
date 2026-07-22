# Hermes Session Storage: SQLite → PostgreSQL (2026-06-11)

## Scope

Migrated Hermes' session storage from SQLite `state.db` to PostgreSQL for **both** session stores — the gateway SessionStore AND the agent `_session_db`. The PG module existed but was incomplete (~21 of 45 methods) and only covered the gateway SessionStore. The agent loop was still hitting the corrupted `state.db`.

## Files Changed (24+)

### Core: `hermes_state_pg.py` (new module)
- Added `~4200` lines bringing total to ~1002 lines
- Added 32 missing methods including:
  - Session CRUD: `get_session`, `resolve_session_id`, `delete_session`, `set_session_title`, `get_session_title`, `get_session_by_title`, `resolve_session_by_title`, `get_next_title_in_lineage`, `sanitize_title`
  - Token tracking: `update_system_prompt`, `update_token_counts`
  - Compression: `get_compression_tip`, `finalize_orphaned_compression_sessions`, `prune_empty_ghost_sessions`, `maybe_auto_prune_and_vacuum`
  - Handoffs: `request_handoff`, `get_handoff_state`, `list_pending_handoffs`, `claim_handoff`, `complete_handoff`, `fail_handoff`
  - Telegram topics: `enable_telegram_topic_mode`, `disable_telegram_topic_mode`, `is_telegram_topic_mode_enabled`, `get_telegram_topic_binding`, `list_telegram_topic_bindings_for_chat`, `get_telegram_topic_binding_by_session`, `bind_telegram_topic`, `is_telegram_session_linked_to_topic`, `list_unlinked_telegram_sessions_for_user`
  - Session listing: `list_sessions_rich` with `order_by_last_active`
  - Text search: `search_messages` (ILIKE-based)
  - Scroll: `get_messages_around` (windowed scroll anchored on a message id)
  - Utility: `format_session_db_unavailable`, `get_last_init_error`, `_set_last_init_error`
- Added new tables: `telegram_dm_topic_mode`, `telegram_dm_topic_bindings` + indexes
- Added schema migration: ALTER TABLE for `started_at` DEFAULT

### Import patches (23 files)
All `from hermes_state import SessionDB` switched to `from hermes_state_pg import SessionDB`:
- `gateway/run.py` — gateway `_session_db` init + insights/title helpers
- `run_agent.py` — fallback `_get_session_db_for_recall`
- `cli.py` — 6 locations
- `hermes_cli/main.py` — 5 locations
- `hermes_cli/goals.py` — GoalManager
- `hermes_cli/web_server.py` — 16 dashboard endpoints
- `hermes_cli/oneshot.py` — SessionDB factory
- `tools/session_search_tool.py` — 3 locations + requirements check rewrite
- `agent/tool_executor.py` — format_session_db_unavailable
- `agent/agent_runtime_helpers.py` — format_session_db_unavailable
- `gateway/session.py` — already been patched (Postgres SessionStore)
- `gateway/mirror.py` — message mirroring
- `gateway/platforms/api_server.py` — API server session DB
- `cron/scheduler.py` — cron session DB
- `tui_gateway/server.py` — 4 locations
- `acp_adapter/session.py` — ACP adapter
- `mcp_serve.py` — MCP server
- `plugins/hermes-achievements/dashboard/plugin_api.py` — achievements dashboard

### Kept on SQLite (intentional)
- `apply_wal_with_fallback` imports (used by kanban_db, holographic memory store) — these are SQLite-specific WAL operations that don't apply to Postgres

## Bugs Found & Fixed During Migration

### 1. `started_at` DEFAULT not applied to existing tables
`CREATE TABLE IF NOT EXISTS sessions (... started_at DOUBLE PRECISION NOT NULL DEFAULT ...)` does NOT backfill DEFAULT on tables that already exist. The `started_at` column silently had `default=None` for existing databases, causing every `create_session()` to fail with NOT NULL violation.

**Fix:** Added schema migration that checks `information_schema.columns` and applies `ALTER TABLE sessions ALTER COLUMN started_at SET DEFAULT extract(epoch from now())` if the default is null.

### 2. psycopg2 can't adapt Python dicts
Unlike SQLite (which auto-stringifies), psycopg2 raises `can't adapt type 'dict'` when `model_config` or other dict-valued columns are passed as parameters. Every `**kwargs` path in `create_session()` and `ensure_session()` needs explicit `json.dumps()` on dict/list values.

### 3. Gateway `_session_db` vs agent fallback
The gateway passes its `_session_db` to `AIAgent` at `run.py:12729`. If the gateway's init fails (e.g., Postgres connection error), the fallback at `run_agent.py:497` also needs the PG import — otherwise it falls back to SQLite `hermes_state` which uses the corrupted `state.db`.

- **`search_messages` and `order_by_last_active` were added after initial restart**
  These are called by the `session_search` tool which the user tests interactively. The ILIKE-based search works but doesn't have CJK trigram support or FTS5 BM25 ranking — adequate for basic use.
- **`get_messages_around` was added after user testing** — the scroll mode of session search failed with "'SessionDB' object has no attribute 'get_messages_around'". Ported from SQLite version.

## Gateway Restart Self-Kill

When restarting the gateway, NEVER use `pgrep -f pattern | xargs kill -9` in the same terminal call as `tmux new-session`. The pgrep pattern matches your own shell's subprocesses, killing them before the kill command runs, which exits with SIGKILL (-9) and nukes the tmux server. Always:
1. Kill old gateway by targeted PID (separate terminal call)
2. Kill old tmux session (separate call)
3. Start fresh tmux (separate call)

## Verification Commands

```bash
# Check gateway is using Postgres (no SQLite errors)
grep "database disk image\|malformed\|SQLite.*not available" ~/.hermes/logs/gateway.log | grep "$(date +%H:%M)" || echo "Clean"

# Check new sessions land in Postgres
sudo -u postgres psql -d hermes_sessions -c "SELECT id, source, started_at, message_count FROM sessions ORDER BY started_at DESC LIMIT 3;"

# Test session search from CLI
hermes chat -q 'search for "model" in my sessions'

# Verify Postgres has sessions with messages
sudo -u postgres psql -d hermes_sessions -c "SELECT COUNT(*), source FROM sessions GROUP BY source;"
```

## Post-Migration State (June 11, 2026)

- Postgres: 830 sessions, 17,613 messages
- Telegram sessions now writing to Postgres: ✅
- CLI sessions now writing to Postgres: ✅
- Session search (ILIKE): working
- `list_sessions_rich` with `order_by_last_active`: working
- Handoffs: working
- Telegram topic mode: working
- Kanban/holographic memory: still on SQLite (intentional)
