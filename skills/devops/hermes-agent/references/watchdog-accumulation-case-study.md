# Watchdog Accumulation — Case Study (2026-05-29)

## The Incident

User reported "Slack and Telegram gateways are down." Gateway was actually running but
4 orphan `hermes gateway run` processes were consuming ~50% CPU each, competing with the
real gateway for resources.

## Process State Before Cleanup

```
# 4 stale watchdogs from May 21/28 — parented by init, surviving tmux kills
Company    9797   bash /home/tapway/.local/bin/hermes-gateway-watchdog  (May 21)
Company    4578   bash /home/tapway/.local/bin/hermes-gateway-watchdog  (May 28)
Company   31243   bash /home/tapway/.local/bin/hermes-gateway-watchdog  (May 28)
Company   32278   bash /home/tapway/.local/bin/hermes-gateway-watchdog  (May 28)

# 4 orphan gateway processes spawned at 10:19 — no controlling terminal, high CPU
Company   32560   hermes gateway run  (46% CPU, ?)
Company   32563   hermes gateway run  (47% CPU, ?)
Company   32564   hermes gateway run  (49% CPU, ?)
Company   32565   hermes gateway run  (51% CPU, ?)

# Real gateway in tmux (healthy)
Company   30655   hermes gateway run  (pts/6, 10:17 start)

# tmux state
hermes-gateway: 1 windows (created Fri May 29 10:17:13 2026)
```

## Timeline of Events

1. **May 21**: Original tmux session killed, watchdog survives (SIGHUP ignored)
2. **May 28**: Multiple terminal opens → `.bashrc` creates new tmux + watchdog each time
3. **May 28-29**: Stale watchdogs accumulate silently — no errors, just process bloat
4. **May 29 10:07**: Gateway receives SIGINT from user, shuts down cleanly. Watchdog restarts it.
5. **May 29 10:17**: `.bashrc` auto-starts yet another tmux + watchdog. Watchdog spawns gateway (PID 30655).
6. **May 29 10:19**: Orphan gateways spontaneously spawned (likely one of the stale watchdogs saw its gateway die and launched a replacement, but multiple stale watchdogs raced). Real gateway held the tokens — orphans burned CPU futilely.

## Log Evidence

Gateway was always connected — the problem was invisible process bloat:

```
10:07:16  Telegram button resolved (normal operation)
10:07:58  SIGINT — planned gateway stop
10:17:36  Memory monitor started (new gateway)
10:17:45  ✓ telegram connected
10:17:49  ✓ slack connected
10:17:49  Gateway running with 2 platform(s)
10:18:37  inbound message: platform=slack user=Elaf  (gateway processing normally)
10:19:21  response ready: platform=slack time=44.5s api_calls=4 response=810 chars
```

The 44.5s response time for 4 API calls is suspicious — likely from CPU contention with the 4 orphan processes.

## Fix Applied

Mutual exclusion via PID file in the watchdog script (`/tmp/hermes-gateway.pid`):

```bash
# On startup: check for existing watchdog
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE")
  if kill -0 "$OLD_PID" 2>/dev/null && ps -p "$OLD_PID" -o comm= | grep -qE "bash"; then
    echo "Another watchdog is already running (PID $OLD_PID). Exiting."
    exit 0
  fi
  rm -f "$PIDFILE"  # stale
fi
echo "$$" > "$PIDFILE"
```

Smoke test confirmed:
```
$ timeout 3 ~/.local/bin/hermes-gateway-watchdog
[watchdog 1733] Another watchdog is already running (PID 30653). Exiting.
```

## Cleanup Commands Used

```bash
# Kill stale watchdogs (PID 9796 is the tmux server — don't touch)
kill -9 9797 4578 31243 32278

# Orphan gateways were already dead by the time we tried to kill them
kill -9 32560 32563 32564 32565  # → "No such process"
```

## State After Cleanup

```
Company    9796   tmux new-session hermes-gateway  (May 21 — harmless, just the server)
Company   30653   bash watchdog                      (current)
Company   30655   hermes gateway run                 (pts/6, healthy)
```

## Lessons

1. **PID-file mutual exclusion is essential for SIGTERM/SIGHUP-ignoring watchdogs.** Without it, they multiply silently.
2. **Stale watchdogs are invisible** — `hermes gateway status` shows healthy, logs show connected, but CPU is pegged.
3. **`.bashrc` auto-start is a multiplier** — every terminal open creates a watchdog. Without mutex, you get 1 per terminal per WSL session.
4. **The PID file at `/tmp/hermes-gateway.pid` is the canary** — if it gets stale, the next watchdog start will clean it. But the OLD stale watchdogs don't read it.