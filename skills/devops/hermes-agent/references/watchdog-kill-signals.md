# Killing the Watchdog: Signal Reality

The watchdog script traps `SIGTERM` and `SIGHUP` (ignores them) but leaves `SIGINT` unblocked for clean shutdown.

## What Works

| Signal | Effect | Notes |
|---|---|---|
| `kill -9 <pid>` (SIGKILL) | Always kills | Untrappable. Works regardless of terminal state. **Use this.** |
| `Ctrl+C` in attached tmux | Sends SIGINT | Works because the terminal is the delivery channel |

## What Does NOT Work

| Attempt | Why It Fails |
|---|---|
| `kill <pid>` (SIGTERM) | Trapped by `trap '' SIGTERM` — watchdog ignores it |
| `kill -HUP <pid>` (SIGHUP) | Trapped by `trap '' SIGHUP` — watchdog ignores it |
| `kill -INT <pid>` (SIGINT) | **Fails silently when watchdog has no controlling terminal.** SIGINT requires a tty to deliver — a daemonized/orphaned process won't receive it. |
| `tmux kill-session -t hermes-gateway` | Sends SIGHUP to pane's process group, which the watchdog traps. Watchdog survives, gateway becomes orphan but keeps running. |

## The Reliable Kill Sequence

```bash
# 1. Kill the watchdog (and gateway as collateral)
kill -9 $(ps aux | grep "hermes-gateway-watchdog" | grep -v grep | awk '{print $2}')

# 2. Clean stale PID file
rm -f /tmp/hermes-gateway.pid

# 3. Verify nothing left
ps aux | grep -E "gateway|watchdog" | grep -v grep
```

## Why This Happened

Real incident (2026-06-08): gateway died silently, tmux server vanished. Watchdog became orphaned with no controlling terminal. `kill -INT <watchdog_pid>` had zero effect — SIGINT undeliverable without tty. Required SIGKILL.
