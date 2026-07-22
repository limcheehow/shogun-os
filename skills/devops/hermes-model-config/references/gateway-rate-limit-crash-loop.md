# Gateway Crash Loop Due to Provider Rate Limiting (HTTP 429)

Real incident from 2026-06-09.

## Timeline

- Gateway was processing Telegram messages normally (last success at 23:25)
- A session hit DeepSeek API rate limit (`HTTP 429: Allocated quota exceeded`) via DashScope MaaS
- Gateway crashed on first retry, watchdog auto-restarted it
- New gateway process started but also hit the same rate limit immediately on first API call
- Result: silent crash loop — watchdog kept restarting, gateway kept dying

## Diagnosis

```
# Gateway logs showed:
WARNING agent.conversation_loop: API call failed (attempt 1/1) error_type=RateLimitError
... HTTP 429: ... "Allocated quota exceeded" ...

# Process state showed watchdog alive, PIDs cycling:
pgrep -P <watchdog_pid>   # PID changed between checks
ps aux | grep "hermes gateway run" | grep -v grep  # gateway kept appearing/disappearing
```

## Fix Applied

1. Killed the old watchdog: `kill -9 803 && rm -f /tmp/hermes-gateway.pid`
2. Switched provider from `custom:dashscope-anthropic` (DashScope MaaS) to OpenRouter:
   ```
   hermes config set model.provider openrouter
   hermes config set model.default deepseek/deepseek-v4-flash
   ```
3. Started fresh in tmux: `tmux new-session -d -s hermes-gateway '~/.local/bin/hermes-gateway-watchdog'`
4. Waited ~65s for Telegram init
5. Verified: `tail ~/.hermes/logs/gateway.log | grep "running with"` → Gateway running with 2 platform(s)

## Key Insight

The fallback_providers chain works for runtime API failures but does NOT engage at gateway initialization time. A rate-limited provider kills the gateway during boot, before any fallback logic runs. Manual provider switch is required.

## Provider Config After Fix

```yaml
model:
  default: deepseek/deepseek-v4-flash
  provider: openrouter
```

Original DashScope config preserved in file (can switch back when quota resets).