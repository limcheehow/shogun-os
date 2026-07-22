# Gateway Zombie Process — Troubleshooting Reference

## Context

This document captures the debugging sessions from 2026-05-18 where the user's Telegram gateway was down. Three rounds of debugging occurred:

1. **Round 1** — Zombie process blocking bot token (resolved with `kill -9`)
2. **Round 2** — Gateway died because it was a child of the chat session (resolved with tmux isolation)
3. **Round 3** — Even tmux gateway dies on `hermes gateway restart` because tmux exits when the command exits (resolved with watchdog script)

## Round 1 — Zombie Gateway Blocking Bot Token

### Symptom

User said: "it seems like my telegram gateway is down"

### Investigation

#### Step 1 — Check running processes

```bash
ps aux | grep -i hermes | grep -v grep
```

**Found**:
- `tmux new -s hermes hermes gateway run` — parent (sleeping, PID 2633)
- `[hermes] <defunct>` — zombie gateway process (PID 2634, marked `Zs`)
- `hermes dashboard` — still running
- `hermes chat` — current session

The gateway process was `Zs` (zombie/defunct) — it had exited but its parent hadn't reaped it.

#### Step 2 — Check gateway logs

```bash
tail -50 ~/.hermes/logs/gateway.log
```

**Found** at end of log:
```
2026-05-18 10:27:38,713 INFO gateway.run: Received SIGTERM as a planned gateway stop — exiting cleanly
2026-05-18 10:27:38,714 WARNING gateway.run: Shutdown context: signal=SIGTERM under_systemd=no parent_pid=2633 parent_name=tmux: server
```

A `hermes gateway restart` command had been executed, which sent SIGTERM to the old gateway. The shutdown was clean, but no replacement started.

#### Step 3 — Check tmux sessions

```bash
tmux ls
```

The "hermes" session had ended. Only session "1" (the dashboard) remained.

#### Step 4 — Attempt restart → secondary error

Starting a new gateway revealed:
```
ERROR gateway.platforms.base: [Telegram] Telegram bot token already in use (PID 2634). Stop the other gateway first.
```

The zombie process (PID 2634) was still registered as the owner of the Telegram bot token, even though it was `<defunct>`.

### Resolution

```bash
# 1. Kill the zombie gateway
kill -9 2634

# 2. Verify zombie is gone
ps aux | grep defunct | grep -v grep

# 3. Also clean up the tmux parent
kill -9 2633

# 4. Start fresh gateway
tmux new-session -d -s hermes-gateway 'hermes gateway run'

# 5. Verify in logs
tail -15 ~/.hermes/logs/gateway.log
# Expected output:
#   ✓ telegram connected
#   ✓ slack connected
#   Gateway running with 2 platform(s)
```

---

## Round 2 — Gateway Dies from SIGTERM (Child of Chat Session)

### Symptom

After the Round 1 fix, Telegram stopped working again minutes later.

### Diagnosis

The new gateway was started with `terminal(background=true, command="hermes gateway run")` — this makes it a child of the current chat session. When the chat session's process tree is reaped, the gateway receives SIGTERM and dies.

Evidence from the gateway shutdown diagnostic:
```
Shutdown context: signal=SIGTERM under_systemd=no
parent_pid=16416 parent_name=hermes
parent_cmdline='.../hermes chat'
```

Every attempt via `terminal(background=true)` produced the same pattern: when the parent chat session's terminal tool cleaned up, the gateway got killed.

### Key Insight

`terminal(background=true)` creates processes that are children of the chat session — they share the parent's process group and die when it does. This is fine for short-lived tasks but NOT for persistent services like a gateway.

### Fix: tmux Process Isolation

Use a **detached tmux session** directly (NOT via `terminal(background=true)`):

```bash
tmux new-session -d -s hermes-gateway 'hermes gateway run'
```

The tmux server is parented by init (PID 1), not by the chat session.

Verify process isolation:
```bash
pstree -p -s <gateway_pid>
# Expected: init → tmux: server → hermes
# NOT: init → ... → hermes chat → hermes gateway run
```

---

## Round 3 — Even tmux Gateway Dies on `hermes gateway restart`

### Symptom

After Round 2 was fixed (gateway running in tmux), the gateway was working fine — Telegram and Slack connected, messages flowing. Then:

```
2026-05-18 11:59:35,688 INFO gateway.run: Received SIGTERM as a planned gateway stop — exiting cleanly
Shutdown context: parent_pid=17781 parent_name=tmux: server
```

The tmux session was gone. Gateway would not respond.

### Root Cause

`hermes gateway restart` (triggered during Slack bot setup operations) sends SIGTERM to the gateway. When the gateway is running directly inside tmux (`tmux ... 'hermes gateway run'`), tmux sees the child process exit and the window/session terminates with it. No auto-restart mechanism exists.

This happens because tmux runs the command as a single pane — when that command exits, the pane is closed, and if it's the only pane, the session closes too.

### Fix: Watchdog Script

Wrap `hermes gateway run` in a `while true` loop that re-launches the gateway after any exit:

```bash
#!/usr/bin/env bash
# ~/.local/bin/hermes-gateway-watchdog

while true; do
  hermes gateway run
  sleep 3
done
```

Then use the watchdog in tmux instead of the bare command:
```bash
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
```

The full watchdog script lives at `scripts/hermes-gateway-watchdog.sh` in the `hermes-agent` skill. To install it:
```bash
cp ~/.hermes/skills/devops/hermes-agent/scripts/hermes-gateway-watchdog.sh ~/.local/bin/hermes-gateway-watchdog
chmod +x ~/.local/bin/hermes-gateway-watchdog
```

### Verification

```bash
# 1. Process tree: init → tmux: server → bash (watchdog) → hermes
pstree -p -s $(pgrep -f "hermes gateway run" | head -1)

# 2. Logs show clean startup after auto-restart
tail -10 ~/.hermes/logs/gateway.log
# Should show fresh connection lines with timestamps after restart

# 3. Telegram responds to messages
```

---

## Complete Restart Sequence (with verification)

```bash
# 1. Kill any zombie/defunct gateway processes
ps aux | grep -i hermes | grep defunct
kill -9 <PID>

# 2. Clean up stale tmux sessions
tmux ls
tmux kill-session -t <name>  # if stale

# 3. Ensure watchdog script is installed
ls -la ~/.local/bin/hermes-gateway-watchdog

# 4. Start gateway with watchdog in tmux
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'

# 5. Wait and verify in logs
sleep 15
tail -10 ~/.hermes/logs/gateway.log
# Expected:
#   ✓ telegram connected
#   ✓ slack connected
#   Gateway running with 2 platform(s)

# 6. Verify process isolation
ps aux | grep "gateway run" | grep -v grep
# Should be child of tmux server (PID near 1)

# 7. Test from Telegram — send a message to the bot
```

---

## Console Commands Quick Reference

| Situation | Commands |
|-----------|----------|
| Check gateway is alive | `ps aux \| grep "gateway run" \| grep -v grep` |
| Check tmux sessions | `tmux ls` |
| Check logs | `tail -20 ~/.hermes/logs/gateway.log` |
| Check if zombie/defunct | `ps aux \| grep defunct \| grep -v grep` |
| Kill zombie | `kill -9 <PID>` |
| Start gateway (watchdog) | `tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'` |
| Start gateway (bare, simple) | `tmux new-session -d -s hermes-gateway 'hermes gateway run'` |
| Attach to tmux | `tmux attach -t hermes-gateway` |
| View tmux output | `tmux capture-pane -t hermes-gateway -p \| tail -10` |
| Stop gateway | `tmux kill-session -t hermes-gateway` |
| Restart gateway | `tmux kill-session -t hermes-gateway && tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'` |
