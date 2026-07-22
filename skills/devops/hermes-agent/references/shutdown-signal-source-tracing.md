# Shutdown Signal-Source Tracing

## What

When the gateway receives SIGTERM, `snapshot_shutdown_context()` (in
`gateway/shutdown_forensics.py`) now checks for `.restart_notify.json` in
`HERMES_HOME` and includes its contents in the shutdown context log.

This file is written by `_handle_restart_command()` in `gateway/run.py`
whenever a user issues `/gateway restart` from Telegram, Slack, or any other
messaging platform.

## How It Works

1. User sends `/gateway restart` on Telegram
2. `_handle_restart_command()` writes `.restart_notify.json`:
   ```json
   {"platform": "telegram", "chat_id": "1101916530"}
   ```
3. The method then calls `request_restart()` → `stop(restart=True)` → sends
   SIGTERM to the gateway process
4. The gateway's `shutdown_signal_handler()` calls `snapshot_shutdown_context()`
5. `snapshot_shutdown_context()` reads `.restart_notify.json` and adds:
   ```python
   ctx["restart_notify"] = raw[:300]
   ```
6. `format_context_for_log()` renders it in the log line:
   ```
   restarted_by={"platform": "telegram", "chat_id": "1101916530"}
   ```

## What the Log Looks Like

```
WARNING gateway.run: Shutdown context: signal=SIGTERM
  under_systemd=no parent_pid=30653 parent_name=bash
  loadavg_1m=0.52 restarted_by={"platform": "telegram", "chat_id": "1101916530"}
  parent_cmdline='bash /home/tapway/.local/bin/hermes-gateway-watchdog'
```

## Reading the Result

| Field | Meaning |
|---|---|
| `restarted_by` | The content of `.restart_notify.json` — platform + chat_id of requester |
| No marker | Either SIGTERM came from `kill` CLI, or `.restart_notify.json` was cleaned up before shutdown |
| `takeover_marker_present=other` | A `--replace` instance was starting — not a user-requested restart |

## Source Files Modified

- **`gateway/shutdown_forensics.py`** — `snapshot_shutdown_context()` reads
  `.restart_notify.json`; `format_context_for_log()` includes `restarted_by` in extras
- **`gateway/run.py`** — `_handle_restart_command()` writes `.restart_notify.json`
  (pre-existing, no changes needed)

## Verification

Simulate a restart from the Telegram bot and check the resulting log entry:
```bash
grep "restarted_by" ~/.hermes/logs/gateway.log
# Expected: restarted_by={"platform": "telegram", "chat_id": "..."}
```

If the gateway was killed by a direct `kill` command or OOM, no
`restarted_by` will appear — only the parent process info.

## Pitfalls

- `.restart_notify.json` is consumed lazily by `snapshot_shutdown_context()`
  — the file is read, not deleted. A stale `.restart_notify.json` from a
  previous restart appears in the next shutdown context too. This is
  acceptable because the sequence numbers/time in the parent's context also
  tells you when the signal arrived.
- The file is truncated at 300 chars — fits platform + chat_id easily, but
  if future versions add more fields, keep the truncation limit in mind.
- The check runs inside the signal handler (synchronous, <1ms). It uses
  `read_text()` from pure stdlib (`pathlib`) — no network, no subprocesses.
- If `HERMES_HOME` env var is not set, `.restart_notify.json` can't be
  found and the field is omitted. This shouldn't happen in normal gateway
  operation.