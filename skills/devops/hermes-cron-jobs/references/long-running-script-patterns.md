# Long-Running Scripts in Cron Jobs: Execution Patterns

## The Problem

When a cron job agent needs to run a script that takes **300–600+ seconds** (e.g., Gmail collection hitting 9 users via Google API), the obvious patterns fail:

### ❌ Pattern 1: `delegate_task` subagents

```
delegate_task runs subagents with a ~600s timeout (config.yaml: delegation.timeout_seconds).
Scripts taking 400-500s often run right up to the limit and time out.
Three parallel subagents all timing out = triple the wasted time with no results.
```

**Symptom**: `Subagent timed out after 600.0s with N API call(s) completed`

### ❌ Pattern 2: `process(action='wait')` with long timeout

```
terminal(background=true) → process(action='wait', timeout=300)
             ↑
    Clamped to 60s by the system. Returns timeout with empty output.
```

**Symptom**: `"Requested wait of 300s was clamped to configured limit of 60s"`

## The Working Pattern

### ✅ Direct background + polling

```python
# 1. Launch in background with notification
terminal(command="python3 script.py", background=True, notify_on_complete=True)
# Returns session_id immediately

# 2. Poll until done (loop as needed)
process(action='poll', session_id=sess_id)
# Check status: "running" → poll again later; "exited" → read output_preview

# 3. On exit, output_preview contains the full stdout
```

**Why this works**:
- No subagent timeout ceiling — the background process runs until the script exits
- `notify_on_complete=true` means the agent gets notified on exit (even if you forget to poll)
- Polling lets you collect multiple parallel processes incrementally
- `output_preview` on exit gives you the script's stdout

## Real Session Evidence

From the 2026-06-12 Gmail collection cron job:

| Approach | Result |
|---|---|
| 3× `delegate_task` subagents | All 3 timed out at ~603s with 5-7 API calls each |
| 3× `terminal(background=true)` | All 3 completed (409s, 406s, 519s) with full output |

The scripts took ~400-520s — right in the danger zone for subagent timeouts.

## When to Use Which Pattern

| Script duration | Pattern |
|---|---|
| < 60s | `terminal()` foreground — simplest |
| 60–300s | `terminal(background=true)` + single `process(action='wait')` — the clamp is fine |
| 300–600s | `terminal(background=true)` + poll loop — avoid subagent timeout |
| > 600s | `terminal(background=true, notify_on_complete=true)` + poll loop — subagents WILL time out |
| Parallel 3+ long scripts | Same as above, just poll all 3 session IDs in one batch each iteration |

## Output Buffering Note

Scripts using `print(..., flush=True)` produce output that's visible in `output_preview` on exit. Without flush, output may stay buffered and appear only in the final log. The `process(action='log')` action can retrieve the full output after exit if `output_preview` is empty.