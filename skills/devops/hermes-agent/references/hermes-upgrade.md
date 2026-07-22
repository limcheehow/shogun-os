# Hermes Agent Upgrade Procedure

## Pre-Upgrade Checklist

Before every upgrade, verify the session-postgres plugin is safe:

```bash
# 1. Check plugin exists and is configured
grep "session-postgres" ~/.hermes/config.yaml
# Expected: `  - session-postgres` under `plugins:`

# 2. Verify backup exists (source files identical)
diff -rq ~/.hermes/plugins/session-postgres/ ~/.hermes/plugins/session-postgres.bak-YYYYMMDD/ \
  --exclude='__pycache__'
# Expected: no output (or only .pyc cache differences)

# 3. Confirm Postgres has live data (plugin is actually active)
PGPASSWORD=$(python3 -c "import base64; print(base64.b64decode('$(grep _PG_PASS_B64 ~/.hermes/plugins/session-postgres/hermes_state_pg.py | head -1 | cut -d\\\" -f2)').decode())") \
  psql -h 127.0.0.1 -U hermes -d hermes_sessions -c "SELECT count(*) FROM sessions;"

# 4. Verify session_search works (no SQLite WAL errors)
hermes chat -q "session search test" --no-stream 2>&1 | grep -v "WAL\|locking protocol"
```

### Plugin safety guarantee

The `session-postgres` plugin lives at `~/.hermes/plugins/` — **outside** the core repo at `~/.hermes/hermes-agent/`. An upgrade only touches the core repo; the plugin directory is untouched. If Hermes ever ships native Postgres support (`sessiondb.provider: postgresql` in config), disable the plugin and switch to the native provider — the schema should be compatible.

### What CAN break

| Risk | When | Fix |
|---|---|---|
| Venv rebuilt → psycopg2 lost | After `pip install -e .` | `./venv/bin/python3 -m pip install psycopg2-binary` |
| Hermes changes SessionDB ABC | Plugin needs update | `diff ~/.hermes/hermes-agent/hermes/hermes_state.py ~/.hermes/plugins/session-postgres/hermes_state_pg.py` and mirror new methods |
| Native Postgres support lands | Plugin monkey-patch conflicts | Disable plugin, switch to `sessiondb.provider: postgresql` in config |

## Primary: `hermes update` (auto)

```bash
hermes update
```

Pulls latest release, reinstalls via pip, reloads. If it times out (common on slower connections), use the manual fallback below.

## Fallback: Manual Upgrade

```bash
cd ~/.hermes/hermes-agent

# 1. Stash any local modifications (gateway patches, etc.)
git stash

# 2. Pull latest
git pull

# 3. Reinstall — MUST use venv Python (v0.15+ requires Python ≥3.11)
./venv/bin/python3 -m pip install -e .   # if pip missing: ./venv/bin/python3 -m ensurepip

# 4. Verify
hermes --version
```

## Pitfalls

- **System Python vs venv Python** — `pip install -e .` outside the venv picks up system Python (may be 3.10, too old for v0.15+). Always use `./venv/bin/python3 -m pip`.
- **venv pip may be missing** — some venvs ship without pip. Fix: `./venv/bin/python3 -m ensurepip` then retry install.
- **Local modifications block git pull** — any custom patches to gateway files (e.g., `gateway/platforms/slack.py`) will block `git pull`. Stash them first.
- **`hermes update` timeout** — the command can hang (>300s on slow connections). Manual `git pull + pip install` runs each step separately.
- **Provider type warnings are cosmetic** — `WARNING hermes_cli.config: providers.?: unknown config keys ignored: provider_type` is harmless and does not affect operation.

## Post-Upgrade: Gateway Restart

The running gateway runs old code. Restart:

```bash
tmux kill-session -t hermes-gateway
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
```

Wait 90s for Telegram/Slack to reconnect.

### Post-Upgrade Verification (session-postgres)

After restart, confirm the plugin loaded and Postgres is still the backend:

```bash
# Check gateway log for plugin init — no "falling back to SQLite" warnings
grep "session-postgres" ~/.hermes/logs/gateway.log | tail -3

# Verify session_search still works (no WAL locking protocol errors)
# Send a test message from Telegram and confirm it saves
PGPASSWORD=*** | base64 -d <<< "$(grep _PG_PASS_B64 ~/.hermes/plugins/session-postgres/hermes_state_pg.py | head -1 | cut -d'"' -f2)") \
  psql -h 127.0.0.1 -U hermes -d hermes_sessions \
  -c "SELECT session_id, source, created_at FROM sessions ORDER BY created_at DESC LIMIT 3;"
```

If the plugin ever fails to load (psycopg2 missing, Postgres down), it falls back to SQLite silently — the gateway still works but sessions go to `state.db`. To catch this, grep for `"keeping SQLite fallback"` in gateway logs after every restart.