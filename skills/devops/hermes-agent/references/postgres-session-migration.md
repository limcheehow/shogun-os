# Postgres Session Migration — Completed June 2026

## Two-Session-DB Architecture

Hermes has **two independent session databases** — migrating both is mandatory:

| Session DB | Used By | Backend After Migration |
|---|---|---|
| **Gateway SessionStore** (`gateway/session.py`) | Session indexing, routing, `session_search` tool | Postgres (`from hermes_state_pg import SessionDB`) |
| **Agent `_session_db`** (`gateway/run.py` + `run_agent.py`) | FTS, undo, session search, telegram topics, handoffs, titles, compression | Postgres (`from hermes_state_pg import SessionDB`) |

## Migration Scope

### Module: `hermes_state_pg.py`

Complete Postgres-backed SessionDB with ~45 methods including:

- Basic CRUD: `create_session`, `get_session`, `end_session`, `reopen_session`, `ensure_session`, `delete_session`
- Messages: `append_message`, `replace_messages`, `get_messages_as_conversation`, `get_messages`, `list_recent_user_messages`, `rewind_to_message`
- Titles: `sanitize_title` (static), `set_session_title`, `get_session_title`, `get_next_title_in_lineage`
- Session lookup: `session_count`, `resolve_session_id`, `resolve_session_by_title`, `get_session_by_title`, `resolve_resume_session_id`, `list_sessions_rich`
- Handoffs: `request_handoff`, `get_handoff_state`, `list_pending_handoffs`, `claim_handoff`, `complete_handoff`, `fail_handoff`
- Telegram topics: `enable_telegram_topic_mode`, `disable_telegram_topic_mode`, `is_telegram_topic_mode_enabled`, `get_telegram_topic_binding`, `list_telegram_topic_bindings_for_chat`, `get_telegram_topic_binding_by_session`, `bind_telegram_topic`, `is_telegram_session_linked_to_topic`, `list_unlinked_telegram_sessions_for_user`
- Compression: `get_compression_tip`, `finalize_orphaned_compression_sessions`, `prune_empty_ghost_sessions`, `maybe_auto_prune_and_vacuum`
- Metadata: `get_meta`, `set_meta`, `update_system_prompt`, `update_token_counts`
- Connection: `get_conn`, `close`
- Utility functions (module-level): `format_session_db_unavailable`, `get_last_init_error`, `_set_last_init_error`

### Database Tables

Beyond the basic `sessions`, `messages`, `state_meta`, `compression_locks`:
- `telegram_dm_topic_mode` — chat-level topic mode flag (chat_id PK)
- `telegram_dm_topic_bindings` — session-to-topic-thread bindings (chat_id, thread_id composite PK)

### Files Patched (24 files, ~50 import sites)

Core:
- `gateway/run.py` — `_session_db` init (was `from hermes_state import SessionDB`)
- `gateway/session.py` — `SessionStore._db` init
- `run_agent.py` — fallback `_get_session_db_for_recall`

CLI:
- `cli.py` — 7 import sites
- `hermes_cli/main.py` — 5 import sites
- `hermes_cli/goals.py` — 1 import site
- `hermes_cli/web_server.py` — 18 import sites
- `hermes_cli/oneshot.py` — 1 import site

Tools/Agents:
- `tools/session_search_tool.py` — 4 import sites + `check_session_search_requirements`
- `agent/tool_executor.py` — `format_session_db_unavailable`
- `agent/agent_runtime_helpers.py` — `format_session_db_unavailable`
- `agent/insights.py` — SessionDB import
- `tools/delegate_tool.py` — SessionDB import

Gateway components:
- `gateway/mirror.py` — 1 import site
- `gateway/platforms/api_server.py` — 1 import site
- `tui_gateway/server.py` — 4 import sites
- `acp_adapter/session.py` — 1 import site
- `mcp_serve.py` — 1 import site

Other:
- `cron/scheduler.py` — 1 import site
- `plugins/hermes-achievements/dashboard/plugin_api.py` — 1 import site

Not migrated (intentionally — SQLite WAL required):
- `hermes_cli/kanban_db.py` — uses `apply_wal_with_fallback`
- `plugins/memory/holographic/store.py` — uses `apply_wal_with_fallback`

## Key Pitfalls

1. **Blind INSERT with ON CONFLICT fails on Postgres** — Postgres validates NOT NULL constraints BEFORE checking the ON CONFLICT clause. A missing `started_at` will fail even though the row already exists. Use separate SELECT-then-INSERT or UPDATE-only patterns.

2. **Utility functions must be in the PG module** — `format_session_db_unavailable`, `get_last_init_error`, `_set_last_init_error` are referenced by 15+ files. Without them, import errors cascade.

3. **Connection attribute name mismatch** — PG module uses `_connection` not `_conn` (SQLite convention). The `close()` method must reference the correct attribute.

4. **Plan before charging in** — The most common failure mode: starting multi-step migrations without mapping scope first. The user will call you out. Load the brainstorming skill, write a plan, then execute.