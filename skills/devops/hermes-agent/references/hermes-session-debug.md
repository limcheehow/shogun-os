---
name: hermes-session-debug
description: Debug Hermes session storage issues — state.db corruption, Postgres migration verification, background self-improvement review diagnosis, SQLite heap analysis, and Telegram network timeout investigation.
category: devops
tags: [hermes, session, postgres, state-db, background-review, sqlite, corruption, troubleshooting]
---

# Hermes Session & Storage Debugging

Load this skill when dealing with slow gateways, session amnesia, "database disk image is malformed" errors, background review fork blocking, Postgres migration questions, or Telegram timeout cascades.

## Fundamentals: Three Session DB Handles

Hermes has three independent session database handles. A migration is not complete until ALL three are switched:

| Handle | File & Approx Line | Used for |
|---|---|---|
| Gateway SessionStore | `gateway/session.py:688` | Session indexing, routing store |
| Gateway `_session_db` | `gateway/run.py:2046` | FTS, session_search, topics, handoffs, titles, pruning |
| Agent fallback | `run_agent.py:497` | Lazy recall for one-shot, cron, delegate subagents |

**Migration check:**
```bash
grep -rn "from hermes_state import" hermes-agent/ --include="*.py" | grep -v /tests/ | grep -v hermes_state.py
```
Every hit that's NOT one of the three WAL-fallback files needs switching to `hermes_state_pg`. Post-migration, the only files keeping `hermes_state` should be:
- `gateway/platforms/api_server.py`
- `plugins/memory/holographic/store.py`
- `hermes_cli/kanban_db.py`

These use `apply_wal_with_fallback()` for SQLite WAL — they do NOT need migration.

## Background Self-Improvement Review

Hermes' `agent/background_review.py` spawns a daemon-thread agent fork after every N turns to review skills and memory.

### Mechanism

| Detail | Value |
|---|---|
| Config keys | `skills.creation_nudge_interval` (default 10), `memory.nudge_interval` (default 10) |
| What fires | A full AIAgent fork (16 max iterations) with memory/skills tools only |
| It shares | Same API key, same model, same credentials as the parent turn |
| Thread type | Daemon thread — blocks tool dispatch via `set_thread_tool_whitelist` |
| Objective | Review conversation, create/update skills, update memory entries |
| Output | "💾 Self-improvement review: Memory updated · Skill XYZ created" |

### How It Causes Slowness

- Each fork makes up to 16 API calls — competing with the main agent
- On a cron job with 30+ turns, 3+ reviews fire = 48+ extra API calls
- The fork sets a `thread_tool_whitelist` that blocks ALL non-skill/memory tools — if the fork hasn't finished, the parent's next tool calls get denied
- 50-minute "skill library review" phase is the accumulated runtime of multiple background forks

### How to Disable

```yaml
skills:
  creation_nudge_interval: 0   # disable auto skill review

memory:
  nudge_interval: 0            # disable auto memory review
```

Apply via:
```bash
hermes config set skills.creation_nudge_interval 0
hermes config set memory.nudge_interval 0
```

Restart gateway for changes to take effect on gateway traffic. CLI sessions must also restart.

### Verification

```bash
grep -A7 "^skills:" ~/.hermes/config.yaml
# Should show: creation_nudge_interval: 0
```

## state.db Corruption Diagnosis

### Detection

```bash
# 1. Check file exists
ls -lh ~/.hermes/state.db

# 2. Run SQLite integrity check
sqlite3 ~/.hermes/state.db "PRAGMA integrity_check;"

# 3. Corrupted DB shows:
#   - btreeInitPage() returns error code 11  (SQLITE_CORRUPT)
#   - Child page depth differs
#   - Page N is never used (hundreds of orphan pages)
```

### Cleanup Procedure

1. **Verify nothing has the file open:**
   ```bash
   lsof ~/.hermes/state.db
   ```

2. **Archive the file:**
   ```bash
   mv ~/.hermes/state.db ~/.hermes/state.db.corrupted-backup
   ```

3. **Delete 4.7GB of skeletons** (old backups, snapshots, pre-vacuum copies):
   ```bash
   rm -rf ~/.hermes/state.db.corrupted.* ~/.hermes/state.db.pre-* \
     ~/.hermes/state.db.pre-delete-check ~/.hermes/state-snapshots/
   ```

4. **Clean backup script references** — remove state.db copying from `~/.hermes/scripts/hermes-backup.sh`:
   - Remove the `if command -v sqlite3 ... .backup` block
   - Remove `state.db` from the manifest.json entries

### What NOT to Do

- Deletion only the `-wal` and `-shm` files (those are checkpoint artifacts, not the DB itself). The main file is `state.db`.
- Do NOT delete `~/.hermes/sessions/state.db` — that's the JSONL sessions index, a different database.

## Slow Response Diagnosis

### 1. Check Response Times

```bash
grep "response ready" ~/.hermes/logs/gateway.log | tail -20
```

Key metrics: `api_calls=N` + `time=Xs`. If `api_calls=1` and `time>10s`, the bottleneck is the model. If `api_calls=N` and `time=extreme`, the bottleneck is the agent loop or background review.

### 2. Check for Background Reviews

```bash
grep -i "background_review\|Self-improvement\|spawn_background.*review" ~/.hermes/logs/agent.log | tail -10
```

If you see 💾 Self-improvement review entries, the background review is active and competing for API calls.

### 3. Check for Telegram Network Timeouts

```bash
grep -c "Timed out\|RemoteProtocolError\|send_path_degraded\|ConnectTimeout" ~/.hermes/logs/gateway.log
```

High counts (50+) indicate Azure VM → Telegram API connectivity issues. Messages queue behind failed sends.

### 4. Check for Concurrent Agent Forks

```bash
grep "API call #" ~/.hermes/logs/agent.log | awk '{print $NF}' | sort | uniq -c | sort -rn
```
Multiple thread IDs with API calls interleaved = background review fork competing.

## Pitfalls

- **pgrep self-termination in terminal()**: `pgrep -f "hermes gateway run" | head -1` inside a terminal() call matches YOUR current CLI session, not just the gateway. This kills your own chat session. Always check PID with a separate `ps aux` call first, then `kill -INT <pid>` with the explicit PID.
- **Gateway restart kills the config's effect until restart**: Setting `creation_nudge_interval: 0` in config.yaml has NO effect on the currently running gateway. You must restart the gateway for the change to take effect.
- **"Session storage: ~/.hermes/sessions" does NOT show the backend**: That line logs the JSONL index directory, not whether the session DB is SQLite or Postgres. Check for "Postgres session store" or "state.db" warnings instead.
- **The 90-second wait rule**: After a gateway restart, do NOT spawn diagnostic gateways within 90s. A diagnostic gateway claims the Telegram bot token and causes the real gateway to crash-loop.