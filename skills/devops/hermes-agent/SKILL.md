---
name: hermes-agent
description: Manage Hermes Agent itself — CLI, gateway lifecycle, platform connections (Telegram, Slack, etc.), configuration, and troubleshooting.
category: devops
tags: [hermes, gateway, telegram, slack, platform, troubleshooting, config]
---

# Hermes Agent — Operations & Troubleshooting

Load this skill whenever the user asks about configuring, troubleshooting, or managing Hermes Agent itself — its gateway, platform connections, CLI, config, or setup.

## Quick Reference

| Action | Command |
|---|---|
| Start gateway (foreground) | `hermes gateway run` |
| Create watchdog script | Copy from `scripts/hermes-gateway-watchdog.sh` to `~/.local/bin/hermes-gateway-watchdog` and `chmod +x` |
| Start gateway (persistence, with auto-restart) | `tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'` |
| Start gateway (attach, auto-restart) | `tmux new-session -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'` then Ctrl+B D |
| Restart gateway | Kill old tmux session: `tmux kill-session -t hermes-gateway && tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'` |
| Check gateway status | `ps aux \| grep hermes` — look for `hermes gateway run` |
| Check gateway logs | `tail -30 ~/.hermes/logs/gateway.log` |
| Check tmux sessions | `tmux ls` |
| View live tmux output | `tmux capture-pane -t hermes-gateway -p \| tail -10` |
| Attach to tmux gateway | `tmux attach -t hermes-gateway` |
| View config | `~/.hermes/config.yaml` |
| View env secrets | `~/.hermes/.env` |

| Upgrade Hermes | See `references/hermes-upgrade.md` — manual fallback when `hermes update` times out |

## Critical: WSL Process Isolation

**On WSL, `terminal(background=true)` creates a child of the current chat session.** When the chat session's terminal closes or the process group is reaped, the gateway receives SIGTERM and dies. Evidence:

```
Shutdown context: signal=SIGTERM parent_pid=16416 parent_name=hermes
parent_cmdline='.../hermes chat'
```

The ONLY reliable isolation is a tmux session, because the tmux server is parented by init (PID 1), not by any chat session.

## Gateway Lifecycle

### Starting the Gateway (WSL)

Since systemd is not available on WSL, gateways MUST run inside a **dedicated tmux session** to survive chat session termination. **Two variations exist:**

**Option A — Simple (no auto-restart):**
```bash
tmux new-session -d -s hermes-gateway 'hermes gateway run'
```
⚠ If `hermes gateway restart` is called (e.g., during Slack setup), the process dies and tmux exits — gateway does NOT come back. Good for one-shot demos.

**Option B — Watchdog loop (recommended for production):**
\`\`\`bash
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
\`\`\`
The watchdog script (\`scripts/hermes-gateway-watchdog.sh\` in this skill) wraps \`hermes gateway run\` in a \`while true\` loop. After any exit (restart, crash, SIGTERM), it waits 3 seconds and relaunches. This is the correct setup for a gateway that needs to survive restart operations.

**Signal handling**: the watchdog traps only \\`SIGINT\\` for clean shutdown (Ctrl+C). It explicitly IGNORES both \\`SIGTERM\\` and \\`SIGHUP\\` with \\`trap '' SIGTERM SIGHUP\\`. This serves two purposes: (1) \\`hermes gateway restart\\` (which sends SIGTERM) kills only the gateway child — the while-loop catches the exit and restarts. (2) If the tmux server restarts or crashes, the SIGHUP it sends to children is ignored — the watchdog survives. Only SIGINT ends the watchdog permanently.

- The tmux server is PID 1's child → gateway survives chat exit
- The watchdog reincarnates the gateway after any restart command kill
- Name the session `hermes-gateway` (or any unique name) — avoid session name collisions with other tmux sessions
- **Do NOT use `terminal(background=true, command="hermes gateway run")`** — this creates a child of the chat session that will die when the chat ends

### Auto-Start on WSL

WSL has no native boot-time mechanism for user scripts. Two complementary approaches exist:

#### Method A — `~/.bashrc` (lodged in a shell — starts when you open a terminal)

Add this to `~/.bashrc` so any new terminal auto-starts the gateway if it isn't already running:

```bash
# ── Auto-start Hermes Gateway (Telegram/Slack) ────────────────────────
if command -v hermes &>/dev/null && ! tmux has-session -t hermes-gateway 2>/dev/null; then
  WATCHDOG="$HOME/.local/bin/hermes-gateway-watchdog"
  if [ -x "$WATCHDOG" ]; then
    tmux new-session -d -s hermes-gateway "$WATCHDOG" 2>/dev/null
  else
    tmux new-session -d -s hermes-gateway 'hermes gateway run' 2>/dev/null
  fi
fi
```

This is idempotent (guards with `! tmux has-session`). It handles: WSL restart, terminal close, restart commands, or any event that kills the gateway — **but only after a terminal is opened**.

**Limitation**: If the host VM reboots and no one opens a terminal, the gateway stays down. That's where Method B is needed.

#### Method B — Windows Task Scheduler (boot-time — starts on Windows logon, no terminal needed)

Register a scheduled task that calls `wsl.exe` to launch the watchdog inside WSL. This survives full Windows VM restarts and doesn't depend on anyone opening a terminal.

**Create the task** (requires Administrator):

```powershell
# From an elevated PowerShell or cmd.exe:
schtasks /Create /SC ONLOGON /TN "Hermes Gateway" ^
  /TR "wsl.exe -d Ubuntu bash -l -c '~/.local/bin/hermes-gateway-watchdog &'" ^
  /DELAY 0000:01 /F
```

**Verification**:
```cmd
schtasks /Query /TN "Hermes Gateway" /FO LIST
```

Expected output:
```
Status:        Ready
Logon Mode:    Interactive only
```

**Run immediately (test)**:
```cmd
schtasks /Run /TN "Hermes Gateway"
```

**Delete the task**:
```cmd
schtasks /Delete /TN "Hermes Gateway" /F
```

**How it works**:
- Task Scheduler fires `ONLOGON` (when the Windows user logs in, which typically happens on boot)
- 1-second delay (`/DELAY 0000:01`) gives WSL time to initialize
- `wsl.exe -d Ubuntu bash -l -c '...'` starts a login shell inside WSL and runs the watchdog
- The watchdog runs `hermes gateway run` in a `while true` loop — process stays alive via `&`
- Method A (`.bashrc`) serves as a fallback if you open a terminal before the task fires, or if the task somehow didn't start

**Pitfalls**:
- `schtasks /Create` requires Administrator rights. From WSL, use `Start-Process -Verb RunAs`:
  ```powershell
  powershell.exe -Command "Start-Process schtasks.exe -ArgumentList '/Create /SC ONLOGON /TN \"Hermes Gateway\" /TR \"wsl.exe -d Ubuntu bash -l -c ''~/.local/bin/hermes-gateway-watchdog &''\" /DELAY 0000:01 /F' -Verb RunAs -Wait"
  ```
- If the Windows user does NOT have auto-login, the task fires on first interactive logon, not at raw boot.
- `schtasks.exe` from inside WSL works but prompts UAC elevation. If that fails interactively, write a `.bat` to Desktop and instruct the user to right-click → Run as Administrator.
- The WSL distro name may differ (check with `wsl.exe -l -v`). Adjust the `-d` argument as needed.
### Checking Gateway Health

```bash
# 1. Verify the process exists
ps aux | grep "hermes gateway run" | grep -v grep

# 2. Check the tmux session
tmux ls | grep hermes-gateway

# 3. View live tmux output
tmux capture-pane -t hermes-gateway -p | tail -10

# 4. Check logs
tail -20 ~/.hermes/logs/gateway.log
```

Wait for log lines:
```
✓ telegram connected
✓ slack connected
Gateway running with 2 platform(s)
```

### Stopping / Restarting

- From the TUI: `/gateway stop` or `/gateway restart`
- From CLI: `kill <gateway_pid>` then start fresh (sends SIGTERM — gateway logs a clean shutdown)
- The gateway logs a clean shutdown line when SIGTERM is received:
  ```
  Received SIGTERM as a planned gateway stop — exiting cleanly
  ```
- **To stop the watchdog permanently**: SIGTERM does NOT work — the watchdog traps it (`trap '' SIGTERM`). Use `kill -9 <watchdog_pid>` (SIGKILL) or `tmux kill-session -t hermes-gateway` (sends SIGINT to the tmux pane). Verify it's dead:
  ```bash
  ps aux | grep watchdog | grep -v grep   # should return nothing
  rm -f /tmp/hermes-gateway.pid            # clean stale PID file
  ```

## Common Failure Modes

### 1. Zombie Gateway Blocks Bot Token

**Symptom**: New gateway fails to connect with:
```
Telegram bot token already in use (PID X). Stop the other gateway first.
```

**Root cause**: A previous gateway process is defunct/zombie (`<defunct>` or `Zs` status in `ps aux`) but the Telegram API still sees the token as active. This happens when `hermes gateway restart` was run inside tmux — the old process gets SIGTERM but the replacement never starts.

**Fix**:
1. `ps aux | grep hermes | grep -v grep` — find the defunct processes show as `<defunct>` or `Zs`
2. `kill -9 <PID>` — kill the zombie to release the Telegram token
3. Check for leftover tmux sessions: `tmux ls` — kill stale ones with `tmux kill-session -t <name>` if attempting a clean restart
4. Start fresh in a fresh tmux session (not the old one) to avoid name collision: `tmux new-session -d -s hermes-gateway 'hermes gateway run'`

### 2. Gateway Dies Silently (SIGTERM from Chat Session)

**Symptom**: Gateway starts fine, handles messages, then stops working after a few minutes. Gateway logs show:
```
Received SIGTERM as a planned gateway stop — exiting cleanly
Shutdown context: parent_pid=<chat_pid> parent_name=hermes
parent_cmdline='.../hermes chat'
```

**Root cause**: The gateway was started as a child of this Hermes chat session. When the chat session's terminal/proc group is reaped, its children receive SIGTERM.

**Fix**: 
1. This is NOT fixable with `terminal(background=true)` — that creates a child of the chat session.
2. Must use a detached tmux session so the process tree is: `init → tmux: server → gateway`
3. Add the `~/.bashrc` auto-start snippet (see above) so the gateway survives WSL restarts

### 3. Gateway Dies on `hermes gateway restart` (Even in tmux)

**Symptom**: Gateway is running in tmux. After a restart operation (e.g., during Slack bot setup), it dies and tmux exits. The tmux session is gone and gateway won't respond.

**Root cause**: `hermes gateway restart` sends SIGTERM to the gateway process. If the gateway is running directly in tmux (`tmux ... 'hermes gateway run'`), tmux sees the child exit and the pane/session terminates. No auto-restart mechanism.

The log shows:
```
Received SIGTERM as a planned gateway stop — exiting cleanly
```

**Fix**: Use the **watchdog wrapper** (`~/.local/bin/hermes-gateway-watchdog`) instead of running `hermes gateway run` directly in tmux. The watchdog wraps it in a `while true` loop — every time the gateway exits (for any reason), it sleeps 3 seconds and relaunches.

```bash
# Install the watchdog
cp ~/.hermes/skills/devops/hermes-agent/scripts/hermes-gateway-watchdog.sh ~/.local/bin/hermes-gateway-watchdog
chmod +x ~/.local/bin/hermes-gateway-watchdog

# Start with watchdog
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
```

- **Critical: the watchdog IGNORES SIGTERM AND SIGHUP (\\\\`trap '' SIGTERM SIGHUP\\\\`).** Unlike a typical script, the watchdog explicitly ignores both \\`SIGTERM\\` and \\`SIGHUP\\` — it never terminates on those signals. Why? When \\`hermes gateway restart\\` or \\`kill <gateway_pid>\\` sends SIGTERM, it only kills the gateway child process. The watchdog's \\`while true\\` loop sees the exit, sleeps 3 seconds, and restarts the gateway. Without \\`trap '' SIGTERM\\`, bash's default SIGTERM handler kills the watchdog too — exactly the bug this fix prevents. Similarly, tmux server restarts send SIGHUP to child processes; without ignoring it, the watchdog dies in the same way.

To **permanently stop** the gateway (not restart): send \\`SIGINT\\` to the watchdog PID (e.g. \\`kill -INT <watchdog_pid>\\`), or use \\`tmux kill-session -t hermes-gateway\\`.

### 4. Slow Per-Message Response Latency

**Symptom**: Simple messages ("hi", "hello") take 10-15s to get a response. Total API calls are low (1-2), but the first call itself is slow.

**Diagnose with gateway logs**:
```bash
tail -50 ~/.hermes/logs/gateway.log | grep "response ready"
```
Look for lines like:
```
response ready: platform=slack chat=D0B0LU0HP4L time=15.1s api_calls=1 response=168 chars
```
Key metric: `api_calls=1` + `time=15.1s` means the LLM call itself is the bottleneck.

**Common cause #1: `reasoning_effort: medium` (or high)**

Forces chain-of-thought reasoning on EVERY message. Even "hi" passes through 5-10s of CoT before first response token. Fix: set to empty and restart gateway:
```yaml
agent:
  reasoning_effort: ''
```

**Common cause #2: Bloated memory (>90% utilization)**

Each memory char is system prompt tokens. Condense entries to <70%, keep only high-value durable facts.

**Common cause #3: 94+ skill descriptions in system prompt (~3K tokens)**

No built-in trim, but three techniques help:
1. **Lean memory** (<70%) — fewer total tokens to process
2. **Disabled reasoning_effort** — removes CoT time that compounds overhead
3. **FAST PATH channel prompt** — add a rule to the platform channel prompt that skips skill loading entirely for trivial messages:
   ```yaml
   slack:
     channel_prompts: 'D0B0LU0HP4L:...FAST PATH: greetings, acknowledgments, single-word, or under 50 chars — reply instantly, load zero skills, search nothing.'
   ```
   Without this, even "hi" triggers full skill scanning before the first response token. With it, trivial messages bypass scanning entirely. Expected improvement: ~9s → ~3-4s for simple messages.

### 10. Slack User Sees Command Approval Dialogs

**Symptom**: Non-technical Slack users see "Command Approval Required" dialogs with Allow Once / Deny buttons when the agent tries to run terminal commands.

**Root cause**: `approvals.mode: manual` (default) intercepts `command_allowlist` matches and routes them through platform approval buttons. For Slack, this shows inline buttons. For Telegram, the approval is a simple yes/no inline interaction. Users who don't understand the command get confused.

**Fix options** (choose one):

1. **Change to auto** (recommended for product-agent bots):
   ```yaml
   approvals:
     mode: auto
   ```
   Dangerous commands are auto-approved and run silently. The agent's channel prompt (which says "BLOCKED: terminal") is the first line of defense.

2. **Lock allowed_channels** — Restrict which Slack channels/DMs the bot responds to:
   ```yaml
   slack:
     allowed_channels: 'D0B0LU0HP4L,D0B0AUSRYQK,C0ABY3VT4U8,C0308PA6Y'
   ```
   Users outside the allowed list get an "Unauthorized user" warning in logs (silent to them).

3. **Both** — auto-approve + restrict access. This is the setting deployed for 's product agent.

**Verification**: After restarting the gateway, terminal commands execute without approval prompts. Only "destructive" slash commands (`/gateway restart`, etc.) still require confirmation if `destructive_slash_confirm: true`.

**Symptom**: Messages get "Gateway timeout" after 30 minutes.

**Config** (in `~/.hermes/config.yaml`):
- `agent.gateway_timeout`: max seconds for a response (default 1800 = 30 min)
- `agent.gateway_timeout_warning`: when to warn (default 900 = 15 min)
- `agent.max_turns`: agent loop iterations (default 90)

### 7. Raw Tool Call XML Leaking into Slack Messages

**Symptom**: Slack displays raw Python code, tool call parameters, or XML tags like `</parameter>` as text in the bot's response. Messages contain fragments like:
```
write_file(path="/home/...")
print("...")
</parameter>
```

**Root cause**: `display.interim_assistant_messages: true` streams the model's intermediate reasoning text to Slack while the response is being generated. When the model's chain-of-thought includes planned tool call invocations as text (common with some models), those verbatim fragments are delivered to Slack before being consumed as structured function calls.

**Fix**: Add a Slack-specific platform override to suppress interim messages:

```yaml
display:
  platforms:
    slack:
      tool_progress: off
      interim_assistant_messages: false
```

May need to also add the `interim_assistant_messages` key if it doesn't already exist under `display.platforms.slack`. Restart gateway after change.

**Verification**: Send a command that triggers tool calls (e.g., a file write request) from Slack. Only the final clean response should appear — no raw tool call XML fragments.

**Pitfalls**:
- `interim_assistant_messages: false` means NO streaming text for Slack — users see nothing until the full response is ready. On complex tasks, this may mean a visible delay with no feedback.
- This does NOT affect the final response quality — only suppresses the intermediate/tool-call text fragments that leak.
- The `display.platforms.slack` section may not exist yet — create it if it's missing.

### 8. PGLite Database Corruption (Stale WAL / Checkpoint Files)

**Symptom**: `gbrain doctor` reports:
```
[doctor.pgvector] Could not check pgvector extension
```
Or gbrain commands fail with connection errors. Yet the PGLite directory (`~/.gbrain/brain.pglite/`) exists with files in it. No other error messages.

**Root cause**: On WSL, unclean shutdowns (WSL restart, terminal force-close, machine sleep) leave stale PostgreSQL Write-Ahead Log (WAL) checkpoint files in the PGLite directory — specifically `-wal` and `-shm` files. These are leftovers from a previous connection that didn't clean up. PGLite interprets them as a corrupted database and refuses to start.

**Fix** — delete the stale checkpoint files (these are temp files, not the database itself):
```bash
rm -f ~/.gbrain/brain.pglite/*-wal ~/.gbrain/brain.pglite/*-shm
```
Then verify with `gbrain doctor --json` or `gbrain list -n 3`.

**Verification**:
```
connection: Connected, N pages
pgvector: 100% coverage, 0 missing
```

**Pitfalls**:
- Only delete `-wal` and `-shm` files. **Never delete** the main directory or core database files inside it.
- This is a WSL-specific issue. On native Linux with systemd, PostgreSQL handles WAL cleanup automatically.
- If PGLite persists after checkpoint cleanup, the core database files may be corrupted — restore from backup or run `gbrain import ~/brain/` to rebuild from markdown source.

### 13. Stale Watchdog Accumulation (Multiple Gateway Instances)

**Symptom**: `ps aux` shows 4+ `hermes gateway run` processes running simultaneously, some orphaned (no controlling terminal, high CPU), plus multiple `bash ... hermes-gateway-watchdog` processes from different dates. `hermes gateway status` says running but messages are slow or dropped. Gateway logs may show duplicate connection attempts.

**Root cause**: The watchdog ignores SIGHUP (needed to survive tmux server restarts), but when an old tmux session is killed, the bash watchdog process survives because it traps SIGHUP. On next terminal open, `.bashrc` auto-start creates a NEW tmux + watchdog, and the old one keeps running. Each watchdog spawns its own gateway. Over weeks, you get a pile of stale watchdogs and racing gateway instances fighting for tokens.

**Fix**: The watchdog script now includes PID-file mutual exclusion (v2):
- On startup, checks `/tmp/hermes-gateway.pid` for an existing watchdog
- If found and process is alive → prints "Another watchdog is already running" and exits
- If found but process is dead → cleans up stale file and proceeds
- Only ONE watchdog can ever run

**Verification**:
```bash
# Attempt to start a second watchdog — should refuse
timeout 3 ~/.local/bin/hermes-gateway-watchdog
# Expected: "[watchdog NNN] Another watchdog is already running (PID XXXXX). Exiting."

# Check only one watchdog and one gateway exist
ps aux | grep -E "gateway|watchdog" | grep -v grep
# Expected: 1 tmux + 1 watchdog + 1 gateway process
```

**Cleanup** (if hit by this before the fix):
```bash
# Kill all stale watchdogs and orphan gateways, keeping only the tmux-managed ones
# Identify the REAL gateway first (the one in tmux with a controlling terminal)
ps aux | grep "gateway run" | grep -v grep | grep "pts/"
# Kill everything else
```

**Pitfalls**:
- The watchdog ignores SIGHUP by design — `kill -HUP` won't stop stale instances. Use `kill -9` on the stale bash processes directly.
- The PID file at `/tmp/hermes-gateway.pid` is the single source of truth. If you manually kill the watchdog, also `rm -f /tmp/hermes-gateway.pid` so the next auto-start works.
- This failure mode is cumulative — stale watchdogs accumulate silently over weeks. After WSL restarts, the stale processes are gone, but `.bashrc` creates a fresh one each time a terminal opens.

### 12. Slack "Command Approval Required" Dialog — Non-Technical Users Get Scary Popups

**Symptom**: Slack users (especially non-technical ones like Elaf) see a "Command Approval Required" dialog with shell commands like `curl -s "..." | python3 -c "..."` and buttons: "Allow Once", "Allow Session", "Always Allow", "Deny". They don't understand it and shouldn't have to.

**Root cause — three layers**:

1. **`approvals.mode: manual`** catches pipe-to-shell commands (`curl | python3`, etc.) and gates them behind an approval dialog. This is meant for safety but leaks to every Slack user who DMs the bot.

2. **Channel prompts don't actually disable tools.** Saying `BLOCKED: terminal, execute_code` in a `channel_prompts` entry is just an LLM suggestion — the model may ignore it, and the underlying tool remains available. Real tool restriction requires `platform_toolsets` configuration.

3. **Unrestricted `allowed_channels`** (`allowed_channels: ''`) means ANY Slack user in the workspace can DM the bot. Combined with #1 and #2, this produces the approval dialog for random users.

**Fix (all three)**:

```yaml
# 1. Auto-approve — kill dialogs entirely
approvals:
  mode: auto

# 2. Lock who can reach the bot
slack:
  allowed_channels: 'D0B0LU0HP4L,D0B0AUSRYQK,C0ABY3VT4U8,C0308PA6Y'

# 3. Restricted platform toolsets (already correct if using hermes-slack base)
platform_toolsets:
  slack:
    - hermes-slack    # no terminal, no execute_code, no file write
```

**Verification**:
```bash
hermes config 2>&1 | head -5  # no parse warnings
grep "allowed_channels" ~/.hermes/config.yaml  # not empty
grep "mode: auto" ~/.hermes/config.yaml | grep approvals -A2
```

**Pitfalls**:
- `allowed_channels` is a comma-separated string, not a YAML list. Format: `'D0B0LU0HP4L,D0B0AUSRYQK,C0ABY3VT4U8,C0308PA6Y'`.
- Gateway restart required for changes to take effect.
- `approvals.mode: auto` means dangerous commands run silently — this is acceptable when platform toolsets already restrict what the Slack bot can do.
- The `command_allowlist` entries (pipe remote content to shell, etc.) still apply — `auto` mode just means they run without prompting. Combined with restricted `platform_toolsets`, this is safe.
- Unknown users hitting the bot with `allowed_channels` set will see nothing — the gateway logs `Unauthorized user` and drops the message silently. This is intentional.

### 11. Config YAML Corruption — Concatenated Lines + Missing Quotes

**Symptom**: `hermes config` fails to parse with:
```
while parsing a block mapping in "config.yaml", line 412, column 5
expected <block end>, but found '<scalar>'
```
Gateway silently falls back to default config — model, provider, and all user overrides are **ignored**. The agent works but uses a different model/provider than intended.

**Root cause**: Two `channel_prompts` entries (multi-line string values) got concatenated onto a single line AND the first entry lost its closing `"`. The config had:
```
line 411:  channel_prompts:
line 412:    '-1003773708968': "...KIZUNA prompt...      '-1003958841816': "You are HAIKU...
line 413:      \ are concise, creative, and strategic.\nPERSONALITY: ...
```
The two keys collapsed onto one line. The first key's value was missing its closing quote.

**Fix**: 
1. Inspect the offending line: `awk 'NR==412' config.yaml | wc -c` → 2133 chars (that's two entries)
2. Find the split point where the second key starts: `line.find("    '-1003958841816':")` → char 2048
3. Split into two lines: `lines[411] = line[:2048].rstrip() + '\n'` + `lines.insert(412, line[2048:])`
4. Add missing closing quote: if the first entry ends with `\"\\n` (escaped quote + newline), append a bare `"` before the newline
5. Verify: `hermes config` → no parse warnings, model shows correct provider

**Detection**: `hermes config 2>&1 | head -1` — if you see `⚠️  hermes config: Failed to parse`, the config is broken and the gateway is running on defaults. Model will show as blank or wrong in `hermes config` output.

**Symptom**: `agent.title_generator: Title generation failed: Error code: 404` in logs. Title/vision/compression features return 404 even though main chat works fine.

**Root cause**: `provider: auto` on auxiliary sections resolves to the main provider (`custom:dashscope-anthropic`). The auxiliary feature calls an OpenAI-style endpoint path (e.g., `/v1/chat/completions`) but the Anthropic provider's base_url points to `/apps/anthropic` — the path mismatch causes 404.

**Fix**: Add a second custom provider using DashScope's OpenAI-compatible endpoint, then override the specific auxiliary section. See `references/custom-provider-setup.md` → "DashScope OpenAI-Compatible Endpoint" for full setup.

```bash
hermes config set auxiliary.title_generation.provider custom:dashscope-openai
hermes config set auxiliary.title_generation.model deepseek-v4-flash
```

Restart gateway after changes.

### 9. Platform Not Connecting

Check the log for the platform-specific error:
- **Telegram**: Verify `TELEGRAM_BOT_TOKEN` in `~/.hermes/.env`. Token invalid or revoked → get a new one from @BotFather.
- **Slack**: Verify `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`.

### 14. Slow Platform Initialization (60s+ Startup)

**Symptom**: After gateway restart, Telegram and Slack stay unreachable for 1-2 minutes. The gateway process runs but no `✓ telegram connected` appears in logs. Connecting eventually succeeds after ~65 seconds.

**Root cause**: The gateway's Telegram client initialization (long-poll setup, auth handshake) takes 60+ seconds on this WSL/Azure VM setup. During this window:
- The gateway is alive but invisible to users — no inbound messages reach it
- Any *other* gateway process (including diagnostic probes that spawn temporary gateways during troubleshooting) will claim the Telegram bot token, causing the real gateway to fail immediately with "token already in use" and exit with non-zero
- The watchdog then restarts in 3s — which also fails because the diagnostic gateway still holds the token — creating an **infinite crash loop** that only clears when the diagnostic gateway is killed

**Contributing factor — SQLite session store**: On startup the gateway logs:
```
WARNING hermes_state: state.db: WAL journal_mode unsupported on this filesystem
  (locking protocol) — falling back to journal_mode=DELETE
```
This adds 20-30s of startup overhead. It is cosmetic (the gateway falls back to JSONL), but the delay compounds the slow Telegram init.

**Diagnosis** (do NOT declare failure under 90s — wait for the 60s init window):
```bash
# Give the gateway a full 90 seconds before investigating
sleep 90 && grep -E "connected|running with" ~/.hermes/logs/gateway.log | tail -2
```
Expected output after ~65s:
```
✓ telegram connected
✓ slack connected
Gateway running with 2 platform(s)
```

**Fix**: The slow init is an environment characteristic (WSL network stack, Azure VM latency). There is no direct fix. Mitigations:
1. **If the gateway seems dead after restart, wait 90s before spawning any test/diagnostic gateway** — a second gateway steals the token and causes the crash loop described above
2. **Kill any diagnostic gateways first** if you accidentally spawned one — use `kill -9` on the competing `hermes gateway run` process, then let the watchdog's sleep(3) cycle handle the next restart attempt
3. Check that only ONE gateway process is running:
   ```bash
   ps aux | grep "gateway run" | grep -v grep
   ```

**Signal-source tracing**: The shutdown handler in `gateway/run.py` now reads `.restart_notify.json` (written by `_handle_restart_command` when a `/gateway restart` is issued from Telegram/Slack) and includes it in the shutdown context log. When the next SIGTERM hits, the log will show:
```
restarted_by={"platform": "telegram", "chat_id": "1101916530"}
```
This lets you trace who triggered the restart after the fact. See `references/shutdown-signal-source-tracing.md`.

**Pitfalls**:
- The gateway is NOT dead during the first 60s — it is initializing. Killing and restarting just resets the 60s clock. Be patient.
- `hermes gateway run` in a foreground terminal (for diagnostics) will grab the Telegram token. The watchdog's gateway then cannot connect. Always kill your diagnostic process before expecting the watchdog to recover.
- The SQLite WAL warning is harmless but slows startup. It only fires once per process per database.
- **Config**: Check `~/.hermes/config.yaml` under the `telegram:` / `slack:` sections.

### 11. Config.yaml YAML Corruption — Silent Fallback to Default

**Symptom**: User reports the model or provider switched unexpectedly (e.g., DashScope → OpenRouter). `hermes config` prints a warning header then the table — easy to miss because chat still works:
```
⚠️  hermes config: Failed to parse .../config.yaml: while parsing a block mapping
    ...expected <block end>, but found '<scalar>'...
    Falling back to default config — every user override (auxiliary providers,
    fallback chain, model settings) is being IGNORED. Fix the YAML and restart.
```
Or, silently: `hermes config` looks normal but the **Model:** line shows `(auto)` or an empty value instead of the expected `{'default': '...', 'provider': 'custom:...'}` dict.

**Root cause**: Long `telegram.channel_prompts` / `slack.channel_prompts` string literals get structurally corrupted. Common mutations:
1. **Two map entries concatenated onto one line** — e.g., the end of the KIZUNA prompt and start of the HAIKU prompt share a single YAML line.
2. **Missing closing `"`** on a multi-line value — the escaped `\"\\n` at the end of the string value is present, but the actual closing quote that terminates the YAML scalar is missing.

Triggers: in-place edits that flattened a line break, buggy YAML-emitting code, or edit operations mid-string that broke the key:value boundary.

**Diagnosis** (jump straight to the reported line, don't scan the whole file):
```bash
hermes config 2>&1 | head -10   # spot "Failed to parse" + "Falling back"
# Error reports "line N, column C" — go to that line and check raw bytes:
awk 'NR==<N>' ~/.hermes/config.yaml | wc -c   # suspiciously long?
awk 'NR==<N>' ~/.hermes/config.yaml | od -c | head   # structural defects
```

**Fix via Python** (safe for long strings with `\u`, `\\n`, embedded quotes):
```python
with open('/home//.hermes/config.yaml', 'r') as f:
    lines = f.readlines()

idx = <LINE_INDEX>  # 0-indexed (line N → idx N-1)
line = lines[idx]

# (A) Two map keys on one line → split at the second key boundary
split_at = line.find("    '-")
if 0 < split_at < len(line) - 20:
    lines[idx] = line[:split_at].rstrip() + '\n'
    lines.insert(idx + 1, line[split_at:])
    line = lines[idx]

# (B) Missing closing " — value ends with escaped chars but no terminator
if not line.rstrip().endswith('"'):
    lines[idx] = line.rstrip('\n') + '"\n'

with open('/home//.hermes/config.yaml', 'w') as f:
    f.writelines(lines)
```

**Verification**:
```bash
hermes config 2>&1 | head -5              # banner only, no ⚠️ warning
hermes config 2>&1 | grep -A2 "Model"     # must show custom provider dict
```
Restart gateway (with user permission) for the fix to take effect on live traffic.

**Pitfalls**:
- The YAML error line number is reliable — use it to jump straight to the problem. Do NOT scan the whole 600-line file.
- `read_file` truncates lines over display width, so visual inspection can hide the defect. Use `awk` + `od -c` or `python3 -c` for raw byte inspection.
- Channel prompts with embedded single quotes inside a double-quoted value (e.g., `"You are KIZUNA ... 's HR Manager..."`) are structurally fragile — any edit that splices a `'KEY': "` sequence mid-string produces this corruption.
- If `hermes config` shows `Model: (auto)` or missing provider dict — the config is STILL broken even if there's no visible warning on subsequent reads. Re-run `hermes config 2>&1 | head` to see the hidden warning.
- **Do NOT attempt manual sed/awk edits** on long channel prompt strings — they contain `\u`, `\\n`, embedded quotes. Always use Python for surgical fixes.

## Config & Env Files

- **`~/.hermes/config.yaml`** — Main config: model, providers, toolsets, gateway timeouts, platform settings, delegation, TUI display, etc.
- **`~/.hermes/.env`** — Secrets: bot tokens, API keys, channel IDs. One `KEY=VALUE` per line.
- **`~/.hermes/logs/`** — Log directory:
  - `gateway.log` — Gateway activity and platform connection events
  - `agent.log` — Per-session agent activity
  - `errors.log` — Error aggregations
  - `gateway-shutdown-diag.log` — Shutdown diagnostics (ps tree, load, OOM check)

## YAML Config Corruption: Silent Fallback to Default

**Symptom**: After editing `~/.hermes/config.yaml`, the gateway silently uses default/blank provider instead of the custom one. `hermes config` shows:

```
⚠️  hermes config: Failed to parse /home//.hermes/config.yaml: 
while parsing a block mapping in "...", line 412, column 5
expected <block end>, but found '<scalar>'. 
Falling back to default config — every user override (...) is being IGNORED.
```

**Root cause**: The YAML is syntactically broken. Common causes:

1. **Two YAML keys concatenated on one line** — happens when a channel_prompt value's closing `"` is missing, causing the next key (`'-1003958841816'`) to be parsed as part of the previous value's string, not as a new key.
2. **Missing closing quote** on a double-quoted string — the parser reads past the intended boundary.

**Fix**: Use Python surgically — never hand-edit complex YAML values (channel prompts, long strings with escaped newlines):

```python
python3 << 'EOF'
with open('/home//.hermes/config.yaml', 'r') as f:
    lines = f.readlines()

# Locate the corrupted line (e.g., two channel prompt keys merged)
idx = lines[411].find("    '-1003958841816':")
line1 = lines[411][:idx].rstrip() + '"\n'   # close the first value
line2 = lines[411][idx:]                      # second key
lines[411] = line1
lines.insert(412, line2)

with open('/home//.hermes/config.yaml', 'w') as f:
    f.writelines(lines)
EOF
```

**Verification**: `hermes config 2>&1 | head -3` — should NOT show the parse warning. No gateway restart needed just to verify config parse.

**Pitfall**: The "Falling back to default config" warning means the gateway (if running) or future gateway starts will use the DEFAULT provider with a blank model — not your custom provider. This is why a model change appears to "happen by itself" after config edits.

## Custom Providers (Anthropic-Compatible Backends)

Add third-party Anthropic-compatible API endpoints (DashScope, Groq, Together, etc.) as named custom providers to keep the main model config clean.

### YAML Format (List, Not Dict)

The `custom_providers` block **must** be a YAML list with `- name:` prefix. A dict (`name: {...}`) fails with `custom_providers is a dict — it must be a YAML list`.

**Correct** ✅:
```yaml
custom_providers:
  - name: dashscope-anthropic
    base_url: https://dashscope-intl.aliyuncs.com/apps/anthropic
    api_key: sk-6ea5b78644a940bfa37f266cea896499
    provider_type: anthropic
```

**Wrong** ❌ (causes `Unknown provider` error):
```yaml
custom_providers:
  dashscope-anthropic:
    base_url: ...
```

### Activation

Set `model.provider` to `custom:<name>`:

```bash
hermes config set model.provider custom:dashscope-anthropic
```

### Pitfalls

- **`model.api_key` + `provider: anthropic` does NOT work** — setting `api_key` under `model` and `provider: anthropic` makes Hermes look for the `ANTHROPIC_API_KEY` env var, not the config's `api_key`. Always use a custom provider or set the env var directly.
- **`model.base_url` is ignored when `provider` is not a custom provider** — the base_url only takes effect when paired with a provider that uses it (e.g., openai, anthropic). For third-party endpoints, always use `custom_providers`.
- **YAML list vs dict** — the `custom_providers` key value must be a list (`- name: ...` items). Dict format (`name: {...}`) passes syntax check but Hermes rejects it at runtime with `custom_providers is a dict — it must be a YAML list`.
- **provider_type must match the wire protocol** — for Anthropic-compatible endpoints, use `provider_type: anthropic`. For OpenAI-compatible, use `provider_type: openai`.

### Verification

```bash
hermes config   # check model section shows custom:dashscope-anthropic
hermes chat -q "Hello, are you working?"   # test actual response
```

See `references/custom-provider-setup.md` for a full DashScope (Alibaba) setup walkthrough.

## Cron Jobs (Scheduled Tasks)

`hermes cron` manages recurring jobs. Jobs run in a fresh session with no memory of current chat.

### CLI Reference

| Action | Command |
|---|---|
| List jobs | `hermes cron list` |
| Create job | `hermes cron create '0 3 * * *' --name 'My Job' --script myscript.sh --deliver origin` |
| Edit job | `hermes cron edit <job_id> --schedule '*/30 * * * *'` |
| Pause/resume | `hermes cron pause <job_id>` / `hermes cron resume <job_id>` |
| Remove | `hermes cron remove <job_id>` |
| Run now | `hermes cron run <job_id>` |
| Check scheduler | `hermes cron status` |

### ⚠️ `--script` Expects a File Path, Not a Shell Command

This is the #1 mistake. The `--script` parameter expects a **path to a file under `~/.hermes/scripts/`**, not an inline shell command.

**WRONG** — this fails with "Script not found":
```bash
hermes cron create '0 3 * * *' --name 'Sync' --script 'cd ~/project && python3 sync.py 2>&1'
```

**RIGHT** — create a wrapper script first, then reference it:
```bash
# 1. Create wrapper script
cat > ~/.hermes/scripts/my-sync.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/project"
python3 sync.py
EOF
chmod +x ~/.hermes/scripts/my-sync.sh

# 2. Reference it by filename (no path prefix needed)
hermes cron create '0 3 * * *' --name 'Sync' --script my-sync.sh --deliver origin
```

### Agent Mode vs No-Agent Mode

- **Default (agent mode)**: The script's stdout is injected into the agent's prompt each run. The agent then decides what to report. Use when the job needs reasoning (summarizing feeds, drafting briefings, conditional logic).
- **no-agent mode** (`--no-agent`): The script runs on schedule and its stdout is delivered **verbatim** to the target. Empty stdout = silent delivery (nothing sent). Use for watchdogs (disk/memory/GPU alerts, heartbeat pings, CI notifications) where the script output is the exact message.

```bash
# no-agent: script stdout IS the message
hermes cron create '*/5 * * * *' --name 'Disk Watch' --script disk-check.sh --no-agent --deliver origin

# agent mode: LLM interprets the script output and decides what to say
hermes cron create '0 9 * * *' --name 'Daily Brief' --script collect-data.sh --deliver origin
```

### Script Conventions

- `.sh` / `.bash` files run via bash; everything else runs via Python.
- Scripts should be self-contained — they get no chat context on each tick.
- Use `workdir` to inject project context files (AGENTS.md / CLAUDE.md):
  ```bash
  hermes cron create '0 3 * * *' --name 'Project Sync' --script sync.sh --workdir /home/user/my-project
  ```
- To update an existing job's script: `hermes cron edit <job_id> --script new-script.sh`
- To clear an existing script: `hermes cron edit <job_id> --script ''`
- Per-job model override:
  ```bash
  hermes cron create '0 9 * * *' --name 'Brief' --model 'claude-sonnet-4' --prompt '...'
  ```

## Voice Agent (gbrain integration)
ocessor, etc.) — Auto-start the terminal-background process immediately on boot. The `~/.bashrc` approach (Method A) only starts when a terminal is opened, which means manual intervention after every WSL restart. Use `@reboot` crontab instead:\n\n```bash\n# Next.js (product dashboard)\n@reboot cd /home//projects/-product-dashboard && /path/to/node/npx next start -p 3000 >> server.log 2>&1\n\n# HTTPS proxy (product.example.com)\n@reboot /path/to/node /home//.hermes/ssl/serve-https.js >> proxy.log 2>&1\n\n# Voice agent (cheehow.example.com)\n@reboot cd /home//voice-agent/services/voice-agent && /path/to/node code/server.mjs >> server.log 2>&1\n\n# Cloudflare tunnel\n@reboot /home//.local/bin/cloudflared tunnel --config /home//.cloudflared/cheehow-voice.yml run cheehow-voice >> tunnel.log 2>&1\n```\n\nThen add a `*/2 * * * *` watchdog cron that curl-checks each service and auto-restarts anything that's down. See `scripts/dashboard-watchdog.sh` in the cloudflare-origin-deployment skill.

```
Invalid value: 'Aoede'. Supported values are: 'alloy', 'ash', 'ballad', 'coral',
'echo', 'sage', 'shimmer', 'verse', 'marin', 'cedar'.
```

**Fix** in `server.mjs` line 163:
```javascript
// OLD (broken):
const personaVoice = persona === 'mars' ? 'Orus' : 'Aoede';
// NEW (working):
const personaVoice = persona === 'mars' ? 'ash' : 'sage';
```

**Symptom before fix**: browser shows "sending SDP offer..." then "hung up" with no visible error. The root cause is invisible because the client's `endCall()` overwrites the error message (see next pitfall).

### Client-Side Error Obliteration Bug

The reference `call.html` has `endCall()` always call `setStatus('hung up')` — overwriting any real error before the user can read it. When combined with the voice-name error above, the browser silently shows "hung up" with no clue what failed.

**Fix** — guard the status overwrite:
```javascript
async function endCall() {
  callActive = false;
  callBtn.textContent = 'Connect';
  callBtn.classList.remove('active');
  // Don't overwrite error messages with "hung up"
  if (!statusEl.textContent.startsWith('ERROR:')) {
    setStatus('hung up');
  }
  // ... rest of cleanup
}
```

Also add ICE connection state monitoring so WebRTC failures are visible:
```javascript
pc.oniceconnectionstatechange = () => {
  if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
    setStatus(`ERROR: ICE ${pc.iceConnectionState} — WebRTC cannot establish connection`);
  }
};
```

### Server Error Transparency

The reference `server.mjs` returns raw text from OpenAI on errors, making the browser error display unparseable. Fix: return JSON so the client's `try/catch` on `content-type: application/json` can extract the actual error message.

In `handleSession()`, change the error path from:
```javascript
return send(res, upstream.status, text);
```
To:
```javascript
return sendJson(res, upstream.status, { error: detail });
```
Where `detail` is the parsed `j.error.message` or `j.error.code` from the OpenAI response JSON.

### Duplicate Server Processes Trap

After fixing server code, old server processes still running on port 8765 will respond with the old (broken) behavior. The symptoms persist because the old process serves stale code. `pkill -f "node.*server.mjs"` frequently fails on WSL due to signal handling quirks. The reliable kill pattern:

```bash
# ❌ Unreliable on WSL:
pkill -f "server.mjs"

# ✅ Reliable:
kill $(ps aux | awk '/node.*server.mjs/ && !/grep/ {print $2}')
sleep 2
# Verify nothing left:
ps aux | grep server.mjs | grep -v grep
```

Always verify with `ps aux` that exactly ONE process is running after restart.

### Stale Process Ghosts

After moving or deleting the old voice agent directory (`~/.hermes/voice-agent/`), old Node.js server processes may still hold port 8765. The old process's `import.meta.url` still resolves to the deleted path, so `/call` returns 404 (static file not found even though the new directory has it). The health endpoint works because it's just JSON. **Always kill all node processes on the port** before starting the new one — `pkill -f "node.*server.mjs"` or `kill -9 $(lsof -ti :8765)`.

## Pitfalls

- **`hermes cron --script` expects a file path, not a shell command.** The `--script` parameter is a path relative to `~/.hermes/scripts/`. Passing inline shell commands (`cd X && cmd 2>&1`) causes "Script not found" at runtime. Create a `.sh` wrapper script first, then reference it by filename.
- **Do NOT use nohup/disown/setsid from a foreground terminal() call** — Hermes blocks this and returns an error. Use `background=true` instead.
- **The watchdog MUST explicitly ignore SIGTERM AND SIGHUP (\\\\`trap '' SIGTERM SIGHUP\\\\`).** Without this, a restart-sourced SIGTERM kills the bash shell by default, and the while-loop never gets a chance to restart the gateway. Similarly, a tmux server restart sends SIGHUP to children, killing the watchdog. This is the #1 cause of the gateway staying dead after a Telegram/Slack-initiated restart — the watchdog looks like it's protecting the gateway but actually guarantees permanent death on restart. The fix is a single line: add \\\\`trap '' SIGTERM SIGHUP\\\\` after the other traps. Check the template at \\\\`scripts/hermes-gateway-watchdog.sh\\\\` for the canonical implementation.
- **Always ask the user before restarting the gateway.** Never restart automatically. The user may have active conversations or processes running through the gateway. Get explicit permission first.
- **The old gateway process (even defunct/zombie) blocks the Telegram bot token.** Always check for `<defunct>` processes and kill them with `kill -9` before restarting.
- **`hermes gateway restart` from within the gateway is fragile** — it sends SIGTERM to itself, and the replacement may not start. Prefer `tmux kill-session -t hermesgateway` + fresh tmux start, or manually kill zombies and start fresh.
- **`kill -9` is safe for defunct zombies** — they're already dead, `-9` just reaps them from the process table so their resources (including Telegram bot token) are released.
- **Deploying the watchdog script requires a manual copy into `~/.local/bin/`** — the skill stores the script at `scripts/hermes-gateway-watchdog.sh`, but it must be copied and made executable
- **Gateway log appends, never rewrites** — old session data stays in the log. Check timestamps or grep for fresh connection lines like `✓ telegram connected`.
- **tmux session name collision** — If a tmux session with the target name exists (even a dead one), `tmux new-session -d -s` won't create a new one. Run `tmux ls` first, then `tmux kill-session -t <name>` if you need to reuse the name.
- **Break the old "hermes" tmux session name** — the previous setup used `tmux new -s hermes`. After that session dies, the name becomes available again, but prefer a fresh dedicated name like `hermes-gway` for clarity and to avoid confusion with the `hermes` command itself.

## Multi-Persona / Profile Setup (Channel-Routed)

Hermes can behave as **different personas in different Telegram groups/channels** using the same bot. This is the simplest way to create a dedicated "profile" (e.g., a marketing agent) without running a second gateway.

### How It Works

Each Telegram chat (DM, group, supergroup) has a unique numeric ID. The `telegram.channel_prompts` config in `config.yaml` maps chat IDs to persona-defining system prompts. When a message arrives from that chat, Hermes prepends that prompt — effectively changing its personality, allowed skills, and behavior for that channel only.

Your DM stays unchanged; the marketing group gets the marketing persona.

### Setup Steps

1. **Create a Telegram group** (not a channel) and add the Hermes bot as a member
2. **Send any message** in the group — the gateway logs it:
   ```bash
   tail -20 ~/.hermes/logs/gateway.log | grep "inbound message.*telegram"
   # Look for: inbound message: platform=telegram user=... chat=<-1001234567890>
   ```
3. **Add the channel prompt** in `~/.hermes/config.yaml`:
   ```yaml
   telegram:
     reactions: false
     channel_prompts:
       <CHAT_ID>: |
         You are [PERSONA NAME], the marketing AI for .
         PERSONALITY: [describe tone, style, constraints]
         ALLOWED SKILLS: [skill names comma-separated]
         BLOCKED: [anything to explicitly forbid]
         ACCESS CONTROL — [who can do what]
   ```
4. **Restart the gateway** (with user permission) for changes to take effect

### Persona Prompt Best Practices

- **Name it** — "You are Haiku, the marketing AI for " creates role identity
- **Restrict tools** — explicitly list allowed/blocked skills so the persona doesn't accidentally use tools meant for the main agent
- **Define personality** — tone, verbosity, style preferences
- **Set access control** — which users can do which operations
- **Add a FAST PATH rule** for trivial messages to skip skill scanning (reduces latency)

### Example: Marketing Agent Profile

```yaml
telegram:
  channel_prompts:
    -1234567890: |
      You are Haiku, the creative marketing AI for .
      PERSONALITY: Creative, concise, action-oriented. Present options, execute immediately.
      ALLOWED: brainstorming, baoyu-infographic, baoyu-comic, claude-design, sketch, 
               popular-web-designs, powerpoint, humanizer, xurl, gif-search, youtube-content,
               maps-competitive-intel
      BLOCKED: terminal, execute_code, github-*, kanban-*, cronjob, todo, file
      FAST PATH: greetings, acknowledgments, single-word, or under 50 chars — 
                 reply instantly, load zero skills, search nothing.
```

### Pitfalls

- **Telegram bot privacy mode blocks group messages by default.** When you add a bot to a group, Telegram's default Privacy Mode (set via @BotFather, /setprivacy) only lets the bot read messages starting with /, @mentioning it, or replying to its messages. To let the bot read ALL group messages, either make it an admin or disable privacy mode via @BotFather. Without this, the gateway silently never sees any inbound messages from that group — no error, no log entry. This is the #1 reason a group setup appears to "not work" with no visible failure.
- **Chat ID is a negative number for groups/supergroups** (e.g., `-1001234567890`). Positive IDs are user DMs.
- The bot must be a member of the group — adding it is not enough if Telegram privacy mode is enabled (see above).
- Channel prompts are NOT optional
- **Toolsets are shared** — `telegram.channel_prompts` controls personality and skill loading but does NOT independently restrict underlying platform toolsets from `platform_toolsets.telegram`. Use the BLOCKED list in the prompt to enforce restrictions.
- **Group members see each other's conversations** — the bot responds inline in the group. Everything is visible to all members.
- **Restart required** — channel_prompts changes take effect only after gateway restart.

### Getting the Chat ID

If the gateway log doesn't show the chat ID yet, use:

```bash
curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates" | \
  python3 -c "import sys,json; updates=json.load(sys.stdin)['result']; [print(u['message']['chat']['id'], u['message']['chat'].get('title','DM')) for u in updates if 'message' in u]"
```

## Profile Management (CLI)

`hermes profile` manages independent agent profiles — separate configurations, memories, skills, SOUL personas, and cron jobs under `~/.hermes/profiles/<name>/`. Profiles can share a single gateway (channel prompts route to personas) or run their own.

### CLI Reference

| Action | Command |
|---|---|
| List profiles | `hermes profile list` |
| Create profile | `hermes profile create <name>` |
| Delete profile | `hermes profile delete <name>` (prompts for confirmation by typing the name) |
| Rename profile | `hermes profile rename <old> <new>` |
| Switch active | `hermes profile use <name>` |
| Show profile | `hermes profile show <name>` |
| Create alias | `hermes profile alias <name> --name <alias>` (creates `~/.local/bin/<alias>`) |
| Remove alias | `hermes profile alias <name> --remove` |

### Creating a Profile

```bash
hermes profile create <name>
```

Creates `~/.hermes/profiles/<name>/` with default config, 86 bundled skills, and a wrapper at `~/.local/bin/<name>`. No `--copy` flag — to clone from an existing profile, manually copy files:

```bash
hermes profile create <new-name>
cp ~/.hermes/profiles/<source>/config.yaml ~/.hermes/profiles/<new-name>/config.yaml
cp ~/.hermes/profiles/<source>/.env ~/.hermes/profiles/<new-name>/.env 2>/dev/null
cp ~/.hermes/profiles/<source>/memories/*.md ~/.hermes/profiles/<new-name>/memories/
```

This copies model config, API keys, and shared memories while keeping the new profile's own skill bundle.

### SOUL.md — Persona Definition

Each profile has a `SOUL.md` at `~/.hermes/profiles/<name>/SOUL.md`. This defines the agent's personality, role, responsibilities, and boundaries. A well-structured SOUL.md includes:

- **Identity** — who the agent is, its core principles
- **Responsibilities** — numbered list of specific duties
- **Key Paths** — relevant file system paths
- **Always Load Before Working** — skills the agent should preload
- **Boundaries** — explicit "do NOT do X" rules
- **Communication Style** — tone, format, delivery preferences

SOUL.md is loaded fresh each message — no restart needed after edits.

### Renaming a Profile (Pitfall)

`hermes profile rename <old> <new>` can fail with `PermissionError` if the old profile's gateway lock file is held. The rename is an atomic `os.rename()` operation and locks in the filesystem prevent it.

**Workaround**: manually copy and remove:
```bash
cp -r ~/.hermes/profiles/<old> ~/.hermes/profiles/<new>
rm -rf ~/.hermes/profiles/<old>
```

After renaming, the active profile tracker may become stale (pointing to the deleted name). If `hermes profile use default` fails with "Profile `<old>` does not exist", temporarily recreate the old name to unstuck:
```bash
hermes profile create <old>
hermes profile use default
hermes profile delete <old>   # requires typing the name to confirm
```

### Profile Aliases (CLI Wrappers)

```bash
hermes profile alias <name> --name <alias>
```

Creates `~/.local/bin/<alias>` — a CLI wrapper that runs `hermes --profile <name> <args>`. Useful for your-product universe names:
```bash
hermes profile alias project-manager --name taiko     # `taiko chat` → project-manager
hermes profile alias hr-manager --name kizuna         # `kizuna chat` → hr-manager
```

### Gateway & Profiles

**Only one gateway can hold Slack/Telegram bot tokens at a time.** If the default gateway (PID 28094) is running, starting a second gateway under a different profile fails with:
```
Telegram bot token already in use (PID 28094). Stop the other gateway first.
Slack app token already in use (PID 28094). Stop the other gateway first.
```

**For multi-persona setups, do NOT run separate gateways per profile.** Instead, use **channel prompts** in the default gateway's config (see "Multi-Persona / Profile Setup (Channel-Routed)" above). Channel prompts auto-switch personality based on which Slack channel or Telegram chat a message arrives from. Profiles define the persona; channel prompts route to it.

### Profile Directory Structure

```
~/.hermes/profiles/<name>/
├── SOUL.md              Persona definition
├── config.yaml          Model, toolsets, platform settings
├── .env                 API keys and secrets
├── memories/
│   ├── MEMORY.md        Durable facts across sessions
│   └── USER.md          User profile (preferences, style)
├── skills/              Profile's skill library (bundled on create)
├── sessions/            Chat session history
├── cron/                Profile-specific cron jobs
├── audio_cache/         TTS output cache
├── logs/                Gateway and agent logs
└── plans/               Implementation plans
```

### Pitfalls

- **No `--copy` flag exists** — `hermes profile create` always makes a fresh profile. Clone manually with `cp`.
- **Gateway lock blocks rename** — kill the profile's gateway process or remove its `gateway.lock` before renaming.
- **Active profile tracker breaks on rename** — after manual `cp + rm`, the CLI may point to the deleted name. Recreate a temp profile under the old name, switch to default, then delete the temp.
- **Profile delete requires interactive confirmation** — type the profile name, not just "yes". Non-interactive delete (`--force`) is not supported.
- **Channel prompts are the routing layer, profiles are the definition layer.** Don't start a gateway per profile. One gateway + channel prompts = all personas reachable.
- **New profiles inherit 86 bundled skills, not the source profile's skills** — if you cloned from product-manager, manually copy the skills directory too if custom skills are needed.
- **Cron jobs are gate on the active profile** — `hermes cron list` shows only jobs registered under the currently active profile. Check `~/.hermes/profiles/<name>/cron/jobs.json` for the raw list.

## Web Search Setup (DuckDuckGo)

To enable `web_search` tool (DuckDuckGo, free, no API key):

1. **Enable `web` toolset** in `~/.hermes/config.yaml`:
   ```yaml
   toolsets:
   - hermes-cli
   - web
   ```
   Also add `- web` under the relevant `platform_toolsets.<platform>` entry (e.g. `telegram`, `slack`) so the tool is available on that platform.

2. **Set the search backend** in config:
   ```yaml
   web:
     search_backend: ddgs
     extract_backend: ''
   ```

3. **Install the provider**:
   ```bash
   pip install ddgs
   ```

4. **Restart the gateway** (with user permission!) for changes to take effect.

Supported backends (legacy preference order): firecrawl → parallel → tavily → exa → searxng → brave-free → ddgs. Only `ddgs` (DuckDuckGo) requires no API key.

**For high-quality web search with content extraction, use MCP instead** (Exa + Firecrawl). See `references/mcp-web-search-setup.md` for the full setup guide. MCP search is far superior to the legacy DDG backend for research tasks, competitive intel, and content scraping.
  ```
  Without this step, the tmux watchdog launch command (`~/.local/bin/hermes-gateway-watchdog`) will silently fail.
- **Gateway log appends, never rewrites** — old session data stays in the log. Check timestamps or grep for fresh connection lines like `✓ telegram connected`.
- **tmux session name collision** — If a tmux session with the target name exists (even a dead one), `tmux new-session -d -s` won't create a new one. Run `tmux ls` first, then `tmux kill-session -t <name>` if you need to reuse the name.
- **Break the old "hermes" tmux session name** — the previous setup used `tmux new -s hermes`. After that session dies, the name becomes available again, but prefer a fresh dedicated name like `hermes-gway` for clarity and to avoid confusion with the `hermes` command itself.

## Reference Files

- `references/gateway-zombie-troubleshooting.md` — Full transcript of a real session where a zombie gateway process blocked Telegram reconnection, with step-by-step diagnosis and resolution.
- `references/windows-task-scheduler-watchdog.md` — Register a Windows Task Scheduler task to auto-start the gateway watchdog on boot/logon, surviving WSL VM restarts. Commands, pitfalls, and full session transcript.
- `references/slack-latency-diagnosis.md` — Diagnosis and fix of 15s Slack response latency: reasoning_effort, memory bloat, and skills overhead analysis with concrete gateway log evidence.
- `references/slack-channel-config.md` — Slack platform channel configuration: `channel_prompts` MUST be a YAML dict (not a string), `allowed_channels` restriction, per-channel prompt strategy, and gateway restart requirements.
- `references/dashboard-infrastructure-setup.md` — Full infrastructure guide for hosting web apps on this WSL/Azure VM behind Cloudflare: Google OAuth Web Application client setup (including the IP restriction rule), Cloudflare DNS record creation via API tokens, API token type differences (Account vs Personal), Windows portproxy (netsh) for port forwarding, Windows Firewall rules, SSL termination for Cloudflare Full SSL mode using a self-signed cert + Node.js HTTPS reverse proxy, NextAuth behind-reverse-proxy troubleshooting (Configuration error + Supabase adapter tables).
- `references/watchdog-accumulation-case-study.md` — Real incident (2026-05-29): stale watchdog accumulation from multiple tmux kills over weeks, orphan gateway processes burning CPU, PID-file mutual exclusion fix with before/after process state.
- `references/watchdog-trap-evolution.md` — Three iterations of watchdog signal trap debugging: why SIGTERM alone wasn't enough, how tmux server SIGHUP killed the watchdog, and the final `trap '' SIGTERM SIGHUP` fix with verification steps.
- `references/service-watchdog-pattern.md` — Pattern for auto-restarting dead services (Next.js, proxies, tunnels) via `no_agent` cron watchdog: health checks, silent-success semantics, `pkill` pitfalls, and the `@reboot` + `*/2` combo.
- `references/shutdown-signal-source-tracing.md` — How the gateway traces who triggered a `/gateway restart`: `.restart_notify.json` written by the restart handler, read by `snapshot_shutdown_context()` during SIGTERM, logged as `restarted_by=...` in the shutdown context line.
- `references/gbrain-data-collectors.md` — Bypass gbrain's Clawvisor dependency: direct Gmail + Calendar → markdown → gbrain import pipeline. Collector scripts, PII scrubbing, cron setup.
- `references/-your-product-profiles.md` — 's full profile roster with your-product universe naming (Taiko, Kizuna, Kura, Koku, Haiku), SOUL.md structure pattern, profile creation recipe, and channel prompt routing pattern.
- `references/mcp-web-search-setup.md` — Set up high-quality web search via MCP: Exa (semantic search) + Firecrawl (scraping, content extraction, batch ops). Configuration, tools reference, and pitfalls.

### Verifying after Restart

```
1. tail -20 ~/.hermes/logs/gateway.log  # Check for "✓ telegram connected"
2. ps aux | grep "hermes gateway run"   # Confirm the process is alive
3. Send a test message from Telegram to the bot
```

> **Note**: After restart, the gateway takes ~65s to connect Telegram. Do NOT panic if `✓ telegram connected` is missing for the first 60s. Wait 90s before investigating — spawning a diagnostic gateway during this window steals the bot token and causes a crash loop (see Failure Mode 14).

## WSL-Specific Tips

### ⚠️ Cloudflare Settings — Never Change Globally

**Never suggest changing the Cloudflare zone-wide SSL/TLS setting** (e.g., Full → Flexible) to fix a per-subdomain issue. Users have multiple sites on the same zone and a global change affects everything. Always fix it on the origin side: add an SSL-terminating proxy (self-signed cert + Node.js/nginx) and keep Full/Strict mode intact.

### WSL Networking & Port Forwarding

The Hermes server runs as **WSL inside an Azure VM**. The public IP `52.187.147.28` maps to the Azure VM's Windows host, and WSL has its own internal NAT'd IP (`10.0.2.x` for WSL 1). Traffic reaching the VM must be forwarded through two layers:

```
Internet → Cloudflare → Azure VM (52.187.147.28) → Windows portproxy → WSL (10.0.2.x)
```

Key commands (run as Windows Administrator via a `.bat` script on the Desktop):

| Action | Command |
|--------|---------|
| Forward VM:443 to WSL:8443 | `netsh interface portproxy add v4tov4 listenport=443 listenaddress=0.0.0.0 connectport=8443 connectaddress=10.0.2.4` |
| Remove a forward rule | `netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0` |
| List all proxy rules | `netsh interface portproxy show all` |
| Open firewall port | `netsh advfirewall firewall add rule name="Service" dir=in action=allow protocol=TCP localport=443` |

**Important**: Since WSL has no sudo automation, services that bind to ports <1024 (80, 443) need either: (a) run as root via `sudo -S`, or (b) bind to a port >1024 and use Windows portproxy to bridge from the low port down to the high port.

**Self-signed SSL cert** (for Cloudflare Full/Strict SSL mode — each zone-wide setting can't be changed per-subdomain):
```bash
mkdir -p ~/.hermes/ssl
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout ~/.hermes/ssl/server.key \
  -out ~/.hermes/ssl/server.crt \
  -subj "/C=MY/ST=KL/L=KL/O=/CN=product.example.com" \
  -addext "subjectAltName=DNS:product.example.com,DNS:localhost,IP:52.187.147.28"
```

For persistent background processes (servers, proxies), use **tmux** just like the gateway — `terminal(background=true)` creates child processes that die when the chat session ends.

See `references/dashboard-infrastructure-setup.md` for a full walkthrough with a Node.js HTTPS proxy script and Cloudflare details.

### Other Tips

- **`\\\\wsl$\\` can show empty folders** — Windows Explorer's 9P protocol driver sometimes caches stale directory listings. Press F5 or use `explorer.exe ~/brain` from within WSL to open Explorer directly at the correct path.
- **systemd is optional** — Check `/etc/wsl.conf` for `systemd=true`. If enabled, systemd services work; if not, rely on `~/.bashrc` and Windows Task Scheduler for auto-start (see Auto-Start section above).
- **No sudo automation** — Terminal tool blocks interactive sudo (password prompt). Use rustup/pip/manual downloads instead of apt when possible.
- **Gateway auto-start on VM boot** — For boot-time resilience across WSL VM restarts, use Windows Task Scheduler (see `references/windows-task-scheduler-watchdog.md`). The `~/.bashrc` approach only starts the gateway when a terminal is opened.

## Absorbed Sub-Skills (Reference Files)

The following specialized workflows were merged into this umbrella. Their full content lives in `references/`:

| Former Skill | Reference File | Topic |
|---|---|---|
| `hermes-auxiliary-setup` | `references/hermes-auxiliary-setup.md` | Vision provider config, Google OAuth tokens, `hermes config set` string trap, platform_toolsets |
| `hermes-wsl-operations` | `references/hermes-wsl-operations.md` | Session search locking protocol, vision backend null-client, state.db WAL cleanup, gateway force restart (tmux server death) |
| `hermes-remote-setup` | `references/hermes-remote-setup.md` | Cloning Hermes to remote GPU/cloud servers — brain via git, profiles via rsync, config via scp/paramiko |
| `-profile-routing` | `references/-profile-routing.md` | Routing  your-product profiles to Telegram groups — chat ID discovery, channel_prompts editing |
| `hermes-agent-skill-authoring` | `references/hermes-agent-skill-authoring.md` | Authoring SKILL.md files — frontmatter conventions, validator constraints, directory placement, in-repo vs user-local |
| `hermes-data-migration` | `references/hermes-data-migration.md` | SQLite→Postgres session migration — schema, psycopg2 pitfalls, import path sweeping, verification |
| `hermes-session-debug` | `references/hermes-session-debug.md` | Session DB debugging — background review diagnosis, state.db corruption, three-handle architecture, slow-response triage |
| `hermes-tui` | `references/hermes-tui-keybindings.md` | TUI keybindings — Enter/Shift+Enter, slash commands, navigation, platform-specific terminal quirks |
