# Silent Gateway Death — Tmux Server SIGKILL

## Symptom

Gateway process vanishes with NO shutdown log entry. The gateway log just... stops. No "Received SIGTERM", no "shutdown", no error. The tmux server itself is gone (`tmux ls` → "no server running"). The watchdog PID file at `/tmp/hermes-gateway.pid` is missing. Everything is dead with zero trace.

## Root Cause

The **tmux server process** itself was killed. This can happen from:
- `kill -9` on the tmux server PID (SIGKILL is untrappable)
- System resource pressure killing the tmux process
- tmux server crash
- Manual `pkill -9 tmux` or similar

When the tmux server dies, it sends SIGHUP to its children. The watchdog traps SIGHUP (`trap '' SIGHUP`), so it SHOULD survive. But if the tmux server is killed with SIGKILL, the kernel terminates the entire process group — the watchdog can't trap SIGKILL (no process can).

## Diagnosis

```bash
# Check if gateway exists
ps aux | grep "gateway run" | grep -v grep     # empty → dead

# Check if tmux server exists
tmux ls                                          # "no server running" → tmux dead

# Check last log entry
tail -5 ~/.hermes/logs/gateway.log              # abrupt stop, no shutdown line

# Check shutdown diag
tail -5 ~/.hermes/logs/gateway-shutdown-diag.log # last entry is from a prior restart
```

Key indicators:
- Log stops abruptly (no "Received SIGTERM")
- No `gateway-shutdown-diag.log` entry for the event
- Tmux server is completely gone
- Watchdog PID file doesn't exist

## Fix

Restart from scratch — there's nothing to recover:

```bash
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
```

Wait 90s for Telegram to connect, then verify:

```bash
tail -10 ~/.hermes/logs/gateway.log | grep -E "connected|running with"
# Expected: ✓ telegram connected, ✓ slack connected, Gateway running with 2 platform(s)
```

## Prevention

Nothing can prevent SIGKILL — it's the kernel-level termination that bypasses all signal handlers. The watchdog protects against SIGTERM and SIGHUP, but not SIGKILL. Mitigations:
- Don't manually `kill -9` the tmux server
- Ensure adequate system memory so the OOM killer doesn't target tmux
- The `.bashrc` auto-start snippet will restart the gateway on next terminal open
- Windows Task Scheduler (Method B in the Auto-Start section) provides boot-time resilience
