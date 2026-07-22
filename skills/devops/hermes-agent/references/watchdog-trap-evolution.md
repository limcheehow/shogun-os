# Watchdog Trap Evolution — Why the Gateway Kept Dying on Restart

Three iterations of debugging the gateway watchdog, each uncovering a new signal path that killed the watchdog alongside the gateway.

## Iteration 1: SIGTERM

**Symptom**: Gateway dies after `hermes gateway restart` and never comes back. Watchdog (bash running `while true; do hermes gateway run; done`) also gone.

**Root cause**: The watchdog script had `trap cleanup SIGTERM SIGINT SIGHUP`. When `hermes gateway restart` sent SIGTERM to the gateway PID, the bash watchdog also caught it via process-group propagation and ran `cleanup() → exit 0`.

**Fix**: `trap cleanup SIGINT SIGHUP` + `trap '' SIGTERM`. Bash now ignores SIGTERM; only the gateway child receives and handles it cleanly. Watchdog's while-loop sees exit → sleep 3 → restart.

**Verification**: `kill -TERM <gateway_pid>` → watchdog survives → new gateway starts in ~8s.

## Iteration 2: SIGHUP from tmux server

**Symptom**: Same as above — gateway dead, watchdog gone. But the logs show a clean shutdown, and the tmux session `hermes-gateway` is missing from `tmux ls` (orphan tmux client PID still in `ps`).

**Root cause**: After a restart from Telegram, the tmux server had crashed/restarted. On exit, it sent SIGHUP to all child processes. The watchdog's trap caught SIGHUP and ran `cleanup() → exit 0`.

**Diagnostic evidence**:
```
$ tmux ls
hermes-gateway: 1 windows    # old session still registered
$ ps aux | grep tmux
... tmux new-session -d -s hermes-gateway ~/.local/bin/hermes-gateway-watchdog   # orphan PID from May 19
                         ^--- PID 10326
```
The orphan PID 10326 was a tmux client disconnected from a dead tmux server. The watchdog and gateway were orphaned under init (PID 1), but the watchdog's trap still caught SIGHUP from the tmux server dying.

**Fix**: `trap cleanup SIGINT` + `trap '' SIGTERM SIGHUP`. Both SIGTERM and SIGHUP are now ignored. Only SIGINT (Ctrl+C) stops the watchdog.

**Verification**:
- `kill -TERM <gateway_pid>` → watchdog survives → gateway restarts ✓
- `kill -HUP <watchdog_pid>` → watchdog survives (ignored) ✓

## Iteration 3: SIGHUP from process group

(Not needed — Iteration 2's fix covers all cases found so far.)

## Final Watchdog Signal Design

```
trap cleanup SIGINT          # Ctrl+C → clean shutdown
trap '' SIGTERM SIGHUP       # ignored — gateway child handles restart, tmux restarts survive
```

## How to Test

```bash
# 1. Find PIDs
WATCHDOG_PID=$(ps aux | grep "hermes-gateway-watchdog" | grep -v grep | awk '{print $2}')
GATEWAY_PID=$(ps aux | grep "gateway run" | grep -v grep | awk '{print $2}')

# 2. Test SIGTERM (simulates gateway restart)
kill -TERM $GATEWAY_PID
sleep 8
ps aux | grep "gateway run" | grep -v grep   # should show new PID

# 3. Test SIGHUP (simulates tmux server restart)
kill -HUP $WATCHDOG_PID
sleep 3
ps aux | grep "watchdog" | grep -v grep   # should still be running
```

## Key Lessons

- Bash's `trap` handler applies to the bash process itself. When bash is running a child process (`hermes gateway run`), signals sent to the child's PID go to the child only. BUT signals from process-group operations (`pkill`, tmux server shutdown) may also reach the parent.
- `trap '' SIGNAL` is bash's way to ignore a signal completely — bash doesn't forward it or handle it.
- `trap 'cleanup' SIGNAL` catches the signal so you CAN handle it (log, clean up, exit).
- tmux server restarts (e.g. after `killall tmux` or a crash) send SIGHUP to all child processes. This is the least-obvious kill path for a watchdog.
- An orphan tmux client in `ps aux` (without a corresponding `tmux ls` entry) is a dead giveaway that the tmux server restarted while the watchdog was running.