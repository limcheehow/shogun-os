# Orphaned Watchdog After Tmux Server Death

## When This Happens

The gateway is dead. `tmux ls` shows "no server running on /tmp/tmux-1000/default". But `ps aux` reveals a surviving watchdog process (TTY=`?`, no controlling terminal) with the gateway still parented to it. The tmux server was killed (crash, `kill -9`, memory pressure).

## Why SIGINT Fails

The watchdog script traps all signals EXCEPT SIGINT (designed for Ctrl+C clean shutdown):
```bash
trap '' SIGTERM SIGHUP   # ignored — watchdog survives these
```

But when the tmux server dies, the watchdog loses its controlling terminal. The kernel CANNOT deliver SIGINT to a process with no controlling terminal — `kill -INT <pid>` returns success but the signal is silently dropped. SIGKILL is the only signal that works.

## Fix

```bash
# Kill watchdog AND gateway (both must die)
ps aux | awk '/hermes gateway run|hermes-gateway-watchdog/ && !/awk/ {print $2}' | xargs -r kill -9
sleep 2

# Clean PID file so new watchdog doesn't refuse to start
rm -f /tmp/hermes-gateway.pid

# Start fresh
tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'
```

## Key Pitfalls

- `tmux kill-session` sends SIGHUP which the watchdog IGNORES — wrong tool for this scenario
- If you only kill the gateway child, watchdog restarts it in 3s with OLD config
- No shutdown log, no trace — the tmux server just vanishes
