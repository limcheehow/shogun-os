# Production Pitfalls — Scrum Workflow

Hard-won lessons from running department-scrum in production. Each pitfall below was discovered during live operation and is generalized for any deployment.

---

## 1. Gateway Healthy but WebSocket Dead

**Symptom:** `systemctl is-active` returns `active (running)` but the gateway's Slack/Telegram WebSocket is in a crash loop. DM replies are silently dropped — the gateway process is alive but **deaf**.

**Detection:**
```bash
journalctl --user -u hermes-gateway@<profile> --since "1 min ago" --no-pager | grep -c "Session is closed"
```
If count > 0, the WebSocket is crash-looping.

**Impact on scrum:** The listener/gateway receives scrum replies but never processes them. State file shows all members as `replied: false` even though they replied.

**Recovery:** Restart the gateway via `systemctl --user restart hermes-gateway@<profile>`. The agent cannot do this from inside the gateway process — escalate to an operator.

---

## 2. LLM Timeout Cascade

**Symptom:** When using dual LLM passes (e.g., structured analysis + legacy fallback), both can time out on verbose submissions. The listener sends a false "gaps" DM flagging valid answers as missing, then crashes with SIGKILL.

**Root cause:** Default LLM timeout (60s) is too short for complex scrum replies with many task IDs and cross-references.

**Fix:** Increase LLM timeouts to 120s+ for scrum analysis passes. If both passes fail, do NOT send a gaps DM — save the raw reply and flag for manual review instead.

---

## 3. Cron Batch-Fire Race Condition

**Symptom:** At startup or after a downtime gap, the cron scheduler fires all overdue jobs simultaneously (~09:12 for midnight+9am jobs). If the send script writes state AFTER sending all DMs, a concurrent cron trigger can start a second send before the first completes.

**Fix:** Write the state file BEFORE sending DMs. Update each member's status as DMs are sent. This way, a concurrent trigger sees the state file exists and skips.

```python
# ✅ Correct: save state first, then send
state = {"date": DATE_STR, "team": [...], "questions_sent_at": None}
state_file.write_text(json.dumps(state, indent=2))

for member in team:
    result = provider.send_dm(member["user_id"], QUESTIONS)
    member["thread_id"] = result["thread_id"]
    # Save after each DM
    state_file.write_text(json.dumps(state, indent=2))
```

---

## 4. HERMES_HOME Points to Profile Dir

**Symptom:** Scripts using `HERMES_HOME / "scrum"` resolve to `~/.hermes/profiles/<profile>/scrum/` instead of `~/.hermes/scrum/`. State file not found → "No state file for today" skip.

**Root cause:** When running inside a profile gateway, `HERMES_HOME` is set to the profile directory, not the base Hermes directory.

**Fix:** Always use `os.path.expanduser("~/.hermes")` for base paths, NOT `$HERMES_HOME`:

```python
# ❌ Breaks when HERMES_HOME is the profile dir
SCRUM_DIR = HERMES_HOME / "scrum"

# ✅ Always resolves correctly
SCRUM_DIR = Path(os.path.expanduser("~/.hermes/scrum"))
```

---

## 5. JSON Extraction from CLI Output

**Symptom:** When calling `hermes chat -Q` (or similar CLI tools that return JSON), the output includes warning lines on stdout before the JSON payload. `json.loads()` fails.

**Root cause:** CLI tools may print `Warning: ...` or `session_id: ...` lines before the JSON.

**Fix:** Scan all stdout lines for the first one starting with `{`, `[`, or a markdown code fence, and parse from there:

```python
def extract_json(stdout):
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith(("{", "[", "```")):
            # Strip code fences if present
            if line.startswith("```"):
                line = line[3:]
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise ValueError("No JSON found in output")
```

---

## 6. Brain Tool Selection — Keyword vs Semantic

**Symptom:** Task ID validation hit rate is low (e.g., 72%) when using semantic search (`gbrain query`). IDs like `TASK-001` appear inside file content but not in filenames.

**Fix:** Use the right tool for the right pattern:

| Pattern | Tool | Why |
|---|---|---|
| Task ID validation | Keyword search (ripgrep) | IDs are exact strings, not semantic concepts |
| Task ID → slug resolution | Keyword search | Filenames/paths contain the ID |
| Conceptual description matching | Semantic search (`gbrain query`) | Natural language → brain page matching needs semantic ranking |

If using `gbrain search` for keyword matching, sanitize the query first — special characters (`+`, `→`, `/`, `()`, `&`) break ripgrep.

---

## 7. Listener Crash vs LLM Outage

**Symptom:** Both produce the same initial sign — team members stuck in `pending_clarification`. But the recovery is different.

| | Listener Crash | LLM Outage |
|---|---|---|
| Process | PID not found | Process alive |
| Logs | No "Listening" line | `LLM_ANALYZE_ERROR` or `LLM_LEGACY_PARSE_ERROR` |
| Fix | Restart listener | Wait for provider to recover, or switch provider |

**Do NOT restart the listener during an LLM outage** — it will just crash again on the next submission.

---

## 8. Save State AFTER Posting to Channel

**Symptom:** Member shows `submission_state: complete` but `posted_to_channel: null`. The listener processed the reply (parsed via LLM) but never posted to the updates channel.

**Root cause:** If state is saved BEFORE the channel post, a crash between save and post leaves a null `posted_to_channel`.

**Fix:** Post to channel first, get the `ts`, THEN save state with the `ts`:

```python
# ✅ Correct: post first, then save
post_result = client.chat_postMessage(channel=CHANNEL, blocks=blocks)
member["posted_to_channel"] = post_result["ts"]
state_file.write_text(json.dumps(state, indent=2))
```

---

## 9. Recovery Sweep Date Filtering

**Symptom:** On startup, a listener recovery sweep scans ALL DM history without a date filter. It finds stale replies from previous days and processes them into today's state file.

**Fix:** Filter by date — accept only messages from today:

```python
# ✅ Date guard on recovery sweep
for msg in dm_history:
    msg_date = parse_slack_ts(msg["ts"]).date()
    if msg_date != TODAY:
        continue  # Skip stale replies
```

---

## 10. Non-Standard compliance_state Values

**Symptom:** When manually resolving a clarification (e.g., missing task ID), using ad-hoc values like `"clarified"` or `"resolved"` causes the member to still appear in the non-responder list at 11am/5pm.

**Fix:** Only use these values for `compliance_state`:
- `"ok"` — submission is complete and compliant
- `"pending_clarification"` — awaiting more info

For `submission_state`:
- `"complete"` — all 4 questions answered
- `"pending"` — not yet submitted
- `"partial"` — some questions answered

Document any manual resolution in a `clarification_issues` text array.

---

## 11. Pass-Through Post Failure

**Symptom:** `submission_state: complete` with parsed tasks/projects/hours but `posted_to_channel: null`. The listener parsed the data but the post call failed silently.

**Recovery:** Cross-reference actual channel posts via `conversations.history` on the updates channel. If posts exist but `posted_to_channel` is null in state, update it from the channel history timestamps.

---

## 12. CLI Syntax Verification

**Symptom:** Using `gbrain add timeline <slug> --date <date> --summary <text>` produces `Unknown command: add`. Timeline entries were silently never injected.

**Root cause:** The CLI syntax changed between versions. The correct command was `gbrain timeline-add <slug> <date> <text>` (positional args, no flags).

**Fix:** Always verify CLI syntax with `--help` before using a command in a script. CLIs may change between versions.

```python
# ✅ Verify before using
proc = subprocess.run([GBRAIN, "--help"], capture_output=True, text=True)
if "timeline-add" in proc.stdout:
    cmd = [GBRAIN, "timeline-add", slug, date_str, text]
elif "add timeline" in proc.stdout:
    cmd = [GBRAIN, "add", "timeline", slug, "--date", date_str, "--summary", text]
```

---

## 13. Block Kit Format — No Plain Text

**Symptom:** Scrum submissions posted to the updates channel appear as unformatted `rich_text` blocks instead of structured Block Kit.

**Fix:** All submission posts must use the `blocks=` parameter with `mrkdwn` type, never plain-text strings:

```python
# ❌ Produces rich_text, no formatting
client.chat_postMessage(channel=CHANNEL, text=submission_text)

# ✅ Proper Block Kit with mrkdwn
client.chat_postMessage(channel=CHANNEL, blocks=[
    {"type": "header", "text": {"type": "plain_text", "text": f"Scrum: {name}"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": formatted_body}},
    {"type": "divider"},
    {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Posted at {timestamp}"}]}
])
```

---

## 14. Gateway systemd Restart Loop (Duplicate Services)

**Symptom:** systemd shows `activating (auto-restart)` for a profile gateway. The gateway PID is alive and holding the lock file, but systemd keeps trying to start a duplicate. Each attempt logs "Gateway already running (PID XXXX)" and exits with status=1.

**Root cause:** Two systemd unit files managing the same profile — typically a system-level unit (`/etc/systemd/system/hermes-gateway-<profile>.service`) fighting a user-level template unit (`hermes-gateway@<profile>.service`).

**Detection:**
```bash
# Check for both user and system level units
systemctl --user list-units 'hermes-gateway@*' | grep <profile>
systemctl list-units --all | grep "hermes-gateway-<profile>"
```

**Fix:** Remove the duplicate system-level unit:
```bash
sudo systemctl stop hermes-gateway-<profile>
sudo systemctl disable hermes-gateway-<profile>
sudo rm /etc/systemd/system/hermes-gateway-<profile>.service
sudo systemctl daemon-reload
```

Keep only the user-level template unit (`~/.config/systemd/user/hermes-gateway@.service`).

---

## 15. Cron Job Silent Skip

**Symptom:** A cron job appears healthy (`enabled: true`, `last_status: ok`) but doesn't fire on a given day. `next_run` advanced to tomorrow but `last_run` is still yesterday.

**Detection:** Compare `last_run` date against today's date. If `last_run` is yesterday or earlier but `next_run` is tomorrow, the job was silently skipped.

**Workaround:** Manually trigger the job when this is detected. This is a scheduler-level issue, not a script bug.
