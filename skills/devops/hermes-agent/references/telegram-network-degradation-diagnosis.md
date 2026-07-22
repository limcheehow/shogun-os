# Telegram Network Degradation → Extreme Latency Diagnosis

When the user reports "massive slowness" or "memory issues" but the system has plenty of free RAM and no OOM kills, the real culprit is often **Telegram API network degradation** causing message delivery backpressure.

## The Signature Pattern

Three telltale signs in `gateway.log`:

1. **High count of network errors** — `Timed out`, `RemoteProtocolError`, `ConnectTimeout`, `send_path_degraded`
2. **Response times in hundreds/thousands of seconds with low `api_calls`** — e.g., `time=3015.8s api_calls=1` means the model responded quickly but the message sat in a delivery queue behind failed Telegram sends
3. **Telegram reconnect storms** — multiple `Connected to Telegram` / `Telegram polling resumed` lines clustered within minutes to hours

## Diagnostic Commands

```bash
# 1. Quantify network errors
grep -c "Timed out\|RemoteProtocolError\|send_path_degraded\|ConnectTimeout" ~/.hermes/logs/gateway.log

# 2. Check response times — spot the outliers
grep "response ready" ~/.hermes/logs/gateway.log | \
  grep -oP 'time=\K[\d.]+' | sort -n | tail -20

# 3. Check for reconnect storms (multiple reconnects = network instability)
grep -E "Connected to Telegram|polling resumed" ~/.hermes/logs/gateway.log | tail -20

# 4. Rule out OOM (absence = network, not memory)
dmesg -T 2>/dev/null | grep -i "oom\|killed"
free -h

# 5. Check memory monitor (if enabled) — stable RSS + no OOM = not a memory leak
grep "MEMORY" ~/.hermes/logs/gateway.log | tail -10
```

## Distinguishing Network Delays from Model/Overhead Delays

| Metric | Network degradation | Model/overhead issue |
|---|---|---|
| `api_calls` in `response ready` | Low (1-3) even for long times | High (10+) |
| `Timed out` / `ConnectTimeout` in log | Frequent (10+) | Rare or none |
| Telegram reconnect events | Multiple per hour | Normal (once per start) |
| Free RAM / OOM | Normal / no OOM | May show OOM or high RSS |
| Memory monitor RSS trend | Flat | Rising |

**Key heuristic**: `time=3015s api_calls=1` → the 1 API call completed quickly, then the response sat in a queue for 50 minutes behind failed Telegram sends. This is 100% network, 0% model slowness.

## Root Cause

This WSL-on-Azure-VM environment has an intermittent network path to Telegram's API servers (`api.telegram.org`). The failures manifest as:
- `httpcore.ConnectTimeout` — can't establish TCP connection
- `httpx.RemoteProtocolError: Server disconnected without sending a response` — connection dropped mid-request
- `telegram.error.TimedOut` — request sent but no response within timeout

The gateway handles these gracefully (retries, catches exceptions, reconnects) but each failure blocks the message delivery pipeline. When multiple messages are pending, the queue backs up and even fast model responses get delayed by minutes or tens of minutes.

## What Doesn't Help

- **Restarting the gateway** — clears the backlog but the underlying network path is unchanged
- **Increasing timeouts** — the connection is failing at the TCP level, not timing out
- **Killing zombie processes** — the gateway process is healthy; network is the problem

## Mitigations (None Proven)

- The watchdog auto-restarts when the gateway dies, but network degradation isn't fatal — the gateway stays alive, just slow
- Telegram fallback IPs are already enabled (`149.154.166.110`)
- No known fix for the Azure VM → Telegram API path instability

## Real Incident: 2026-06-12

- **63** network errors in gateway.log
- Response times: 597s, 2,232s, **3,015s** (50 min), 827s, 777s
- Telegram reconnect storm 13:32–14:25, plus 6 reconnects on June 11 evening
- No OOM kill, 13GB free RAM, gateway RSS 227MB
- Gateway restarted at 14:33, both platforms connected in 7s
- Conclusion: pure network degradation, zero memory involvement