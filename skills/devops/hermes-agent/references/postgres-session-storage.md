# Postgres Session Storage — Complete Migration Guide

> Last updated: 2026-06-11

## Architecture: Three Session DBs (Not One)

Hermes has three independent session database handles. Prior to the full migration, only `gateway/session.py` was switched to Postgres; the other two still hit corrupted SQLite `state.db`.

| Session DB handle | File & line | Used for |
|---|---|---|
| Gateway SessionStore | `gateway/session.py:688` | Session indexing, routing store |
| Gateway `_session_db` | `gateway/run.py:2046` | FTS, session_search, topics, handoffs, titles, pruning |
| Agent fallback | `run_agent.py:497` | Lazy recall for one-shot, cron, delegate subagents |

The gateway's `_session_db` is passed to AIAgent at `run.py:12729` as `session_db=self._session_db`.

## Pitfall: Thinking One Patch Completes the Migration

The #1 mistake: patching only `gateway/session.py` and assuming the migration is done. The agent loop and CLI ALL still hit SQLite. Audit first:

```bash
grep -rn "from hermes_state import" hermes-agent/ --include="*.py" | grep -v /tests/ | grep -v hermes_state.py
```

Every hit (40-50 across 20+ files) needs switching to `hermes_state_pg`. Only three files keep `hermes_state` — they use `apply_wal_with_fallback()` for SQLite WAL:
- `gateway/platforms/api_server.py`
- `plugins/memory/holographic/store.py`
- `hermes_cli/kanban_db.py`

## Postgres vs SQLite: Gotchas

- **NOT NULL constraints fire BEFORE ON CONFLICT**: `INSERT ... ON CONFLICT DO NOTHING` still validates NOT NULL in Postgres. Blind inserts that work in SQLite (`INSERT OR IGNORE`) fail. Don't do blind inserts; UPDATE returns 0 rows silently if session doesn't exist.
- **`db_path` silently ignored**: PG SessionDB accepts `db_path` but ignores it. Callers passing `Path(profile_home)/state.db` still work.
- **No WAL cleanup needed**: Gateways don't need `cleanup_gateway_wal()` or `PRAGMA wal_checkpoint(TRUNCATE)`. Remove those blocks.
- **`format_session_db_unavailable` and friends**: `hermes_state_pg.py` must export `format_session_db_unavailable`, `get_last_init_error`, `_set_last_init_error` — many callers import these separately.
- **pg_hba.conf peer auth vs TCP**: `psql -U hermes` uses Unix socket + peer auth (fails with non-postgres user). The module connects via TCP 127.0.0.1 + scram-sha-256. Always test with the same transport.

## The "Session storage:" Log Line Is Not a Backend Indicator

`gateway/run.py:4324` logs `logger.info("Session storage: %s", self.config.sessions_dir)`. This shows `~/.hermes/sessions/` regardless of whether Postgres or SQLite backs the sessions. It's the JSONL index directory, not the backend. Check for warnings like "Postgres session store not available" to determine actual backend.