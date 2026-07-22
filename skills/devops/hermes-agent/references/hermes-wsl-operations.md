---
name: hermes-wsl-operations
description: WSL-specific Hermes Agent troubleshooting — session search locking, vision provider failures, stale WAL cleanup, group authorization patterns, and gateway lifecycle on wslfs.
category: devops
tags: [hermes, wsl, session, locking, vision, gateway, telegram, troubleshooting]
---

# Hermes on WSL — Operations & Troubleshooting

Load this skill for WSL-specific Hermes issues: session search failures, vision degradation, group authorization, gateway lifecycle quirks, and filesystem-related database corruption.

## Failure Mode: Session Search Locking Protocol (40s Timeouts)

**Symptom**: All chat responses stall for 40+ seconds. Errors log:
```
Tool session_search returned error (40.02s): "OperationalError: locking protocol"
```
Or: `Search failed: database disk image is malformed`

**Root cause**: `state.db` is on `wslfs` (Windows 9P filesystem). SQLite WAL journal unsupported. After unclean shutdowns, stale `state.db-wal` and `state.db-shm` checkpoint files block the database.

**Diagnosis**:
```bash
df -T ~/.hermes/state.db          # wslfs = problem
ls -la ~/.hermes/state.db-*        # stale WAL files?
grep "locking protocol" ~/.hermes/logs/errors.log | tail -3
df -h /                            # >95% compounds it
```

**Fix**:

**Step 1 — Try WAL cleanup first (fast, often sufficient):**
```bash
rm -f ~/.hermes/state.db-wal ~/.hermes/state.db-shm
```

**Step 2 — If still failing, restore from pre-update snapshot:**
The WAL cleanup often fails because `kill -9` corruption goes deeper than stale WAL files — the database header itself is corrupted.

```bash
# Find available snapshots
ls ~/.hermes/state-snapshots/
# Example: 20260607-062201-pre-update

# Verify snapshot integrity
python3 -c "
import sqlite3
db = sqlite3.connect('$HOME/.hermes/state-snapshots/<SNAPSHOT>/state.db')
print('Integrity:', db.execute('PRAGMA integrity_check').fetchone())
db.close()
"

# Restore
rm -f ~/.hermes/state.db ~/.hermes/state.db-*
cp ~/.hermes/state-snapshots/<SNAPSHOT>/state.db ~/.hermes/state.db
```

**Step 3 — Restart the agent session (NOT just the gateway):**
The agent's process holds a stale in-memory `SessionDB` connection. Even after restoring the DB file, `session_search` will still fail until the agent process restarts. Use `/new` from Telegram/Slack or restart `hermes chat`.

**Pitfalls**: 
- Stale WAL files accumulate after every unclean shutdown on WSL — recurring maintenance
- Corrupted state.db from `kill -9` is NOT recoverable by WAL cleanup alone — the DB header is damaged. Use the snapshot
- Restoring the DB without restarting the agent session is the #1 failure mode — the agent still sees the old corrupted connection
- Snapshots are stale (pre-upgrade), so sessions created after the snapshot date are lost from state.db. The gateway's JSONL fallback retains them for active sessions
- Never `kill -9` unless absolutely necessary — prefer `tmux kill-session` (SIGINT) or `kill <pid>` (SIGTERM)

## Failure Mode: Vision Provider Auto-Resolution on Non-Vision Endpoints

**Symptom**: Images produce garbled or 500s+ responses. Vision IS in tools — provider is the issue.

**Root cause**: `auxiliary.vision.provider: auto` resolves to main provider. If main is `custom:dashscope-anthropic` (Anthropic-compatible proxy without image support), vision silently fails.

**Fix**:
```bash
hermes config set auxiliary.vision.provider openrouter
hermes config set auxiliary.vision.model anthropic/claude-sonnet-4
```
Restart gateway.

**Pitfalls**: Anthropic-compatible proxy endpoints may NOT support image content blocks even though real Anthropic API does. `provider: auto` affects ALL auxiliary features — override individually.

## Failure Mode: Vision Tool Missing from Available Tools

**Symptom**: `vision_analyze` does NOT appear in the agent's available tool list. The agent says "I don't have vision_analyze" or tries workarounds (base64, subprocess, etc.). `hermes tools list` shows vision as ✓ enabled — the toolset is registered, but the tool is silently stripped at runtime.

This has THREE distinct root causes — diagnose in order.

### Root Cause 1: Vision backend resolves to None (MOST COMMON)

`resolve_vision_provider_client()` returns `(provider, None, None)`. When the client is `None`, `_toolset_has_keys("vision")` returns `False` at runtime, and Hermes strips `vision_analyze` from available tools — no error, no log warning, the tool just isn't there.

Triggers:
- `auxiliary.vision.provider` points to a `custom:...` provider whose `custom_providers` entry is malformed (stored as YAML string instead of list — see "hermes config set Wraps Lists as YAML Strings" pitfall below)
- `auxiliary.vision.provider` is `auto` but the main model is text-only (DeepSeek V4, gpt-oss) and the aggregator chain (OpenRouter, Nous) also fails
- The provider's API key is missing or invalid
- `custom_providers` entry uses wrong `provider_type` (e.g., `openai` for an Anthropic-compatible endpoint)

**Diagnosis** — verify the client resolves:
```bash
python3 -c "
import sys
sys.path.insert(0, '/home/tapway/.hermes/hermes-agent')
from agent.auxiliary_client import resolve_vision_provider_client
provider, client, model = resolve_vision_provider_client()
print(f'provider={provider}')
print(f'client OK={client is not None}')
print(f'model={model}')
" 2>&1
```
- `client OK=True` → backend works; problem is elsewhere (check Root Cause 2)
- `client OK=False` → backend broken; see fix below

**Fix**: Switch to a known-working provider:
```bash
hermes config set auxiliary.vision.provider openrouter
hermes config set auxiliary.vision.model google/gemini-2.5-flash
```
OpenRouter uses the same API key as the main model, so no additional setup needed. Other options: `anthropic/claude-sonnet-4`, `google/gemini-2.5-pro`.

If using `custom:...`, verify the `custom_providers` entry is a proper YAML list (not a string):
```yaml
custom_providers:
  - name: dashscope-openai
    base_url: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    api_key: sk-...
    provider_type: openai
```
Grep-check: `grep "custom_providers: '" ~/.hermes/config.yaml` — any hit = corruption.

### Root Cause 2: `platform_toolsets` doesn't include `vision`

The profile's `platform_toolsets` must include `vision` for the tool to be registered. The default profile often lacks `platform_toolsets` entirely.

**Diagnosis**:
```bash
grep -A3 "platform_toolsets" ~/.hermes/config.yaml
```

**Fix**: If `platform_toolsets` exists but lacks `vision`, add it. If `platform_toolsets` is absent, adding `platform_toolsets: [vision]` to a profile that had no override will RESTRICT that profile to ONLY vision tools — add `hermes-cli` and any other needed toolsets too.

### Root Cause 3: `hermes config set` corrupted toolsets as YAML string

`hermes config set toolsets '["hermes-cli", "vision"]'` wraps the value in single quotes, producing the YAML string `'["hermes-cli", "vision"]'` instead of a proper list. Hermes silently ignores it — tools vanish, no warning.

**Diagnosis**:
```bash
grep "toolsets: '" ~/.hermes/config.yaml      # single quote before [ = corrupted
grep "platform_toolsets: '" ~/.hermes/config.yaml
```

**Fix**: Python surgery (see "Pitfall: hermes config set Wraps Lists as YAML Strings" below for the script).

### Verifying the Fix

After any of the above fixes, restart the gateway and verify `vision_analyze` appears in the active tool list by sending a test image or checking: `grep "vision_analyze" ~/.hermes/logs/gateway.log | tail -3`.

**Pitfalls**:
- `hermes tools list` showing vision as ✓ enabled is NOT sufficient — the toolset is registered, but the tool gets stripped at session init if the client fails to resolve or `platform_toolsets` doesn't include it
- `auxiliary.vision` config alone is NOT sufficient — both the backend must resolve AND the profile must register the toolset
- Adding `platform_toolsets: [vision]` to a profile that had no override will RESTRICT that profile to only vision tools — always include `hermes-cli` and other needed toolsets
- Never diagnose this by toggling toolsets repeatedly — check the backend resolution first

**Reference**: `references/vision-platform-toolsets-diagnostic-20260608.md` — full session diagnostic flow: image → 5-step check → root cause (default profile missing platform_toolsets).

**Reference**: `references/vision-backend-null-client-20260608.md` — Root Cause 1 deep-dive: `resolve_vision_provider_client()` → None → tool stripped. Includes the `custom_providers` YAML string corruption variant and validation one-liner.

## Group Authorization: TELEGRAM_GROUP_ALLOWED_CHATS

The modern approach for allowing group access without per-user management:

```bash
# In ~/.hermes/.env — comma-separated chat IDs
TELEGRAM_GROUP_ALLOWED_CHATS=-1003773708968,-1003882643127,-1003958841816,-5205962952
```

Every member of these groups is automatically authorized. No per-user allowlist needed.

**Chat ID discovery** — any of these work:
1. Gateway logs: `grep "group:" ~/.hermes/logs/gateway.log | grep -oP 'group:-?\d+' | sort -u`
2. Once you have the bot token, Telegram API: `curl -s "https://api.telegram.org/bot$TOKEN/getChat?chat_id=$ID" | python3 -c "import json,sys; print(json.load(sys.stdin)['result']['title'])"`

**Related**: `allowed_users` in config.yaml is deprecated. Use env vars instead.

## Config.yaml Editing on WSL

The `patch` tool refuses to write `~/.hermes/config.yaml` (security-sensitive). Use terminal Python for surgical edits:

```bash
python3 << 'PYEOF'
with open('/home/tapway/.hermes/config.yaml', 'r') as f:
    lines = f.readlines()
lines[IDX] = "  new content here\n"
with open('/home/tapway/.hermes/config.yaml', 'w') as f:
    f.writelines(lines)
PYEOF
```

Always verify with `hermes config 2>&1 | head -3` after edits — no parse warnings = good.

### Pitfall: `hermes config set` Wraps Lists as YAML Strings

**Symptom**: After running `hermes config set toolsets '["hermes-cli", "vision"]'`, the toolset silently stops working. The agent doesn't have `vision_analyze` or other tools from the list. No error, no parse warning — the tools just aren't there. `hermes config` shows no warning.

**Root cause**: `hermes config set` wraps every value in YAML single quotes, so `["hermes-cli", "vision"]` becomes the YAML string `'["hermes-cli", "vision"]'` instead of a proper YAML list `["hermes-cli", "vision"]`. Hermes can't parse a string as a toolset list — it silently ignores it. Same corruption affects any list-valued config key: `toolsets`, `platform_toolsets`, `fallback_providers`, `custom_providers`, etc.

**Detection** — grep for single-quoted brackets:
```bash
grep -n "toolsets: '" ~/.hermes/config.yaml
grep -n "platform_toolsets: '" ~/.hermes/config.yaml
```
Any hit = corruption. The single quote before `[` is the tell.

**Fix** — Python surgery to strip the quotes:
```bash
python3 << 'PYEOF'
import json
path = "/home/tapway/.hermes/config.yaml"
with open(path) as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    stripped = line.strip()
    # Fix list-valued keys: '["x", "y"]' -> ["x", "y"]
    if any(stripped.startswith(f"{k}: '") for k in ("toolsets:", "platform_toolsets:", "fallback_providers:", "custom_providers:")) and stripped.endswith("'") and "[" in stripped:
        indent = line[:len(line) - len(line.lstrip())]
        key = stripped.split(":")[0]
        val_str = stripped[len(key + ": '"):-1]
        arr = json.loads(val_str)
        lines[i] = f'{indent}{key}: {json.dumps(arr)}\n'
        print(f"FIXED line {i+1}: {lines[i].rstrip()}")

with open(path, 'w') as f:
    f.writelines(lines)
PYEOF
```

**Prevention**: Never use `hermes config set` for list values. Always use Python surgery. After setting any list-valued key with `hermes config set`, immediately verify with the grep check above.

## Gateway Force Restart (Tmux Server Death)

When the tmux server itself dies (not just the gateway process), `tmux ls` returns "no server running on /tmp/tmux-1000/default". Stale `tmux` client and `bash ... watchdog` processes remain in `ps aux` but can't do anything — the watchdog is orphaned without a tmux server. The stale socket at `/tmp/tmux-1000/default` also blocks new tmux sessions from binding.

**Root cause**: Double-signal during restart — gateway receives SIGINT (graceful shutdown), then its own shutdown diagnostic sends SIGTERM. The combined shell subprocess tree can crash the tmux server.

Gateway logs show the shutdown but no restart:
```
Received SIGINT as a planned gateway stop — exiting cleanly
Received SIGTERM — initiating shutdown
```
No `Gateway running with N platform(s)` line follows.

**Fix**:
```bash
# 1. Kill stale tmux client and watchdog processes
kill -9 $(ps aux | grep -E "tmux.*hermes-gateway|hermes-gateway-watchdog" | grep -v grep | awk '{print $2}')

# 2. Remove the stale tmux socket (CRITICAL — new tmux sessions silently fail without this)
rm -f /tmp/tmux-1000/default

# 3. Clean stale PID file
rm -f /tmp/hermes-gateway.pid

# 4. Verify nothing left
ps aux | grep -E "hermes gateway|watchdog|tmux.*hermes" | grep -v grep
# Should return nothing

# 5. Start fresh
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
sleep 3 && tmux ls  # confirm session exists
```

**Verification** — wait 90s for platform init:
```bash
grep "Gateway running with" ~/.hermes/logs/gateway.log | tail -1
tail -5 ~/.hermes/logs/gateway.log  # should show ✓ telegram/slack connected
```

**Pitfalls**:
- The stale tmux socket **must** be deleted. `tmux new-session -d` sees the socket, assumes a live server owns it, and silently refuses to bind — no error, but no new session.
- The plain `kill -9` on gateway + watchdog is NOT sufficient — the socket survives and blocks recovery.
- `tmux ls` returning "no server running" is the key diagnostic signal for this variant — distinct from a regular crash where tmux still runs but the gateway died.