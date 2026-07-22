---
name: hermes-cron-jobs
description: Manage Hermes Agent scheduled cron jobs — create, edit, pause, resume, and troubleshoot recurring tasks. Covers the CLI quirks that differ from the general hermes-agent docs.
category: devops
tags: [hermes, cron, scheduled-tasks, CLI]
---

# Hermes Cron Jobs

Use when creating, debugging, restoring, or managing Hermes Agent's scheduled cron jobs via `hermes cron`.

## `hermes cron create` — Critical Argument Ordering

The prompt is a **positional argument**, NOT a `--prompt` flag. It MUST come **immediately after the schedule**, before any named flags (`--name`, `--script`, `--skill`, `--deliver`, `--workdir`). Placing it after flags silently fails with "unrecognized arguments."

**WRONG** — prompt after named flags:
```bash
hermes cron create '0 9 * * 1-5' --name 'Scrum' --skill 'product-scrum-workflow' --deliver local "Do the scrum thing."
# ERROR: unrecognized arguments: Do the scrum thing.
```

**RIGHT** — prompt right after schedule, before all flags:
```bash
hermes cron create '0 9 * * 1-5' "Do the scrum thing. Post to #channel." --name 'Scrum' --skill 'product-scrum-workflow' --deliver local
```

This ordering applies whether or not `--script` is used. With `--script`, the prompt still goes right after the schedule:
```bash
hermes cron create '0 3 * * *' "Run the sync — report how many files changed." --name 'Sync' --script 'sync.sh' --deliver origin
```

Without a prompt, flags can be in any order — the error only fires when a positional string appears after named flags.

## `--model` and `--prompt` Named Flags Do NOT Exist

The current `hermes cron create` CLI does NOT support `--model` or `--prompt` as named flags. Attempting either produces a parse error.

There is **no per-job model override via the create command**. If a user specifies `--model` in their cron job specs, the CLI cannot enforce it directly. Set the default model for the profile instead.

## `--script` Expects a File Path, Not a Shell Command

The `--script` parameter is a path relative to `~/.hermes/scripts/`. Passing inline shell commands fails with "Script not found."

**WRONG**:
```bash
hermes cron create '0 3 * * *' --name 'Sync' --script 'cd ~/project && python3 sync.py'
```

**RIGHT** — create a wrapper script first, then reference it:
```bash
# 1. Create wrapper in ~/.hermes/scripts/
cat > ~/.hermes/scripts/my-sync.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/project" && python3 sync.py
EOF
chmod +x ~/.hermes/scripts/my-sync.sh

# 2. Reference by filename (no path prefix)
hermes cron create '0 3 * * *' --name 'Sync' --script my-sync.sh --deliver origin
```

**Note**: `.sh`/`.bash` files run via bash. Everything else runs via Python.

## `--deliver` Target

- `origin`: results sent back to the **chat where the job was originally created** (the `origin` field in jobs.json). NOT the current user's DM — it routes to whichever chat/group the job was born in.
- `local`: results kept in the local output log (`~/.hermes/cron/output/<job_id>/`), not delivered to any platform

### How `origin` Resolution Works

Each cron job stores an `origin` object in `~/.hermes/cron/jobs.json`:

```json
"origin": {
  "platform": "telegram",
  "chat_id": "-1003773708968",
  "chat_name": " HR",
  "thread_id": null
}
```

When `deliver` is set to `"origin"`, the scheduler reads this `origin` field and routes output to that specific chat. This means:
- A job created from the HR Telegram group with `deliver: origin` sends its output back to the HR group, NOT to your DM.
- A job created from your DM with `deliver: origin` sends output back to your DM.
- The **origin is set at creation time** and is immutable without editing jobs.json directly.
- jobs.json is the **authoritative source** for seeing which chat owns which job — `cronjob list` shows `deliver` as "origin" or "local" but does NOT expose the underlying `origin.chat_name`.

## Agent Mode vs No-Agent Mode

- **Default (agent mode)**: The script's stdout is injected into the agent's prompt each run. The agent decides what to report. Use for jobs needing reasoning (summaries, conditional logic, formatting).
- **`--no-agent`**: The script runs on schedule and its stdout is delivered **verbatim**. Empty stdout = silent (nothing sent). Use for watchdogs (disk/memory alerts, heartbeat pings).

```bash
# no-agent: script stdout IS the message
hermes cron create '*/5 * * * *' --name 'Disk Watch' --script disk-check.sh --no-agent --deliver origin

# agent mode: LLM interprets the script output
hermes cron create '0 9 * * *' --name 'Daily Brief' --script collect-data.sh --deliver origin
```

## `--skill` vs `--script`

- `--skill`: attach a skill for the agent to load when the job runs. Repeat for multiple skills.
- `--script`: attach a data-collection script whose output feeds the prompt (or is the job verbatim in no-agent mode).

They can be used together. When both are present, the prompt (positional) + script output + skill context all feed into the agent.

## Auditing Cronjob Delivery Targets

Use this when the user asks "what cronjobs are being sent to [group X]?" or "what jobs are currently deployed to profile Y?"

### Step 1: List All Jobs via Tool

```python
# Use cronjob tool with action='list'
```

The tool returns `deliver` (string) and `last_status` per job but NOT the underlying `origin` chat identity.

### Step 2: Read jobs.json for Full Origin Detail

The authoritative source is `~/.hermes/cron/jobs.json`. Each job entry contains:

```json
{
  "id": "...",
  "name": "gmail-morning-summary",
  "deliver": "origin",        // "origin" (delivers) or "local" (silent)
  "origin": {
    "platform": "telegram",
    "chat_id": "-1003773708968",
    "chat_name": " HR", // ← THIS tells you which chat owns it
    "thread_id": null
  }
}
```

To audit what's going to a specific group:

1. Search jobs.json for `"chat_name": " HR"` or the target chat name
2. For each matching job, check `deliver`:
   - `"origin"` → output IS delivered to that chat
   - `"local"` → output stays local, NOT delivered
3. Also check `last_status` and `last_error` to see if jobs are healthy

### Step 3: Check All Profiles

Cronjobs live in each profile independently. The `cronjob list` tool shows only the current profile's jobs. To discover jobs in other profiles:

```bash
# Find state.db files in other profiles
find ~/.hermes/profiles/<name>/ -name "state.db"

# Check for separate cron job storage
ls ~/.hermes/profiles/<name>/cron/
```

Most profiles use the SAME scheduler (default profile), so their jobs appear in `~/.hermes/cron/jobs.json` — the `origin.chat_name` field tells you which profile/group they were created for.

### Step 4: Classify Jobs

Group the results by delivery type:

- **deliver: origin** → actively outputting to the chat. These are the ones the group actually sees.
- **deliver: local** → running but silent. These may still matter (data collection, internal syncs).

Report to the user with a clean table or bullet groups, showing schedule, last_status, and whether it's agent or script-based. Include the job_id for any follow-up actions (pausing, changing deliver, etc.).

See `references/delivery-audit.md` for a full walkthrough from a real session.

See `references/slack-posting-from-cron.md` for the pattern of posting to Slack from a cron job — token extraction from profile .env, channel ID resolution, and Python-based `chat.postMessage` calls.

## Moving Cron Jobs Between Profiles

`hermes cron` is profile-scoped — jobs created under one profile don't appear under another. To move a job to a different profile:

1. **Read the existing job's config** (model, skill, script, schedule, prompt via `cronjob list`)
2. **Create a new job** in the target profile using the `cronjob` action=create tool, passing the `profile` parameter to land it there. Include the original model/skill/script/schedule.
3. **Remove the old job** from the current profile using `cronjob action=remove` with the old job's ID.

**DO NOT** automate bulk re-creation — use the `cronjob` tool directly for each job, passing all original parameters explicitly.

## Diagnosing Job Failures

When cron jobs show `last_status: error`, follow this pipeline:

### Step 1: List and Filter

```python
# Use cronjob tool with action='list' — scan for last_status: error
```

Group failures by the ERROR MESSAGE, not the job name. Four jobs failing with the same root cause beats four separate fixes.

### Step 2: Read the Output (Critical: It's .md Files, Not Logs)

Cron job output is stored as timestamped `.md` files at `~/.hermes/cron/output/<job_id>/<YYYY-MM-DD_HH-MM-SS>.md`. There are NO `stdout.log` or `stderr.log` files — trying `tail stdout.log` returns nothing.

Read the **most recent** output file for each failing job:
```bash
ls -lt ~/.hermes/cron/output/<job_id>/ | head -3  # find latest
cat ~/.hermes/cron/output/<job_id>/<latest>.md       # read it
```

The `.md` file contains: job name, run time, mode (agent/no_agent), status, and the actual script stdout/stderr or agent error.

For **no_agent** jobs: the markdown shows `stderr:` and `stdout:` sections with the raw script output — this is where you find the actual traceback or error message.

For **agent** jobs: the markdown shows the agent's final response AND a `## Error` section if the agent crashed — check BOTH.

### Step 3: Trace to Root Cause

Read the **script** that the failing job invokes (from `cronjob list` output — the `script` field). Follow the trail:
1. Read the script → it may call another script or binary
2. Test the failing command manually in terminal to reproduce the error
3. Check external dependencies (API keys, token files, network endpoints)

### Step 4: Group by Root Cause

Common failure classes to check for:
- **Auth/token expiry** — Google OAuth tokens, API keys in `/tmp` (volatile!), expired credentials
- **Lock contention** — two cron jobs hitting the same resource lock (e.g., both calling `gbrain sync`)
- **Timeout** — scripts that run longer than the cron timeout (agent jobs have a 300s foreground cap; no_agent scripts can also time out)
- **Daemon-in-cron** — `while true` scripts that never exit; these can't work as cron jobs, they always time out
- **Missing files** — scripts relying on files in `/tmp/` that disappear on reboot

### Step 5: Fix the Root Cause, Not Each Job

When 3 jobs fail with the same Google auth error, fix the auth once — don't patch 3 scripts. Report findings grouped by root cause with impact counts.

### Output Format for User Reports

```markdown
### 🔴 Root cause: Brief label — N jobs affected

**Job names** — what's failing + the shared symptom

**Fix needed:** One-sentence action.
```

Use emoji severity: 🔴 for blocking (auth, missing files), 🟠 for degraded (lock contention), 🟡 for nuisance (timeouts).

For gbrain-specific cron failure patterns (Google OAuth expiry, lock contention with `gbrain sync`, `/tmp` file volatility, daemon-in-cron scripts), see `references/gbrain-job-failures.md`.

## cronjob Tool vs hermes cron CLI

The `cronjob` **tool** (programmatic interface) has capabilities the CLI lacks:

| Feature | cronjob tool | `hermes cron create` CLI |
|---|---|---|
| Per-job model override | ✅ via `model` parameter | ❌ not supported |
| Profile assignment | ✅ via `profile` parameter | ❌ only current profile |
| Model pinning on existing jobs | ✅ via `update` action | ❌ |
| Skills array on create | ✅ | ✅ via `--skill` flag |
| No-agent mode | ✅ via `no_agent` param | ✅ via `--no-agent` flag |

Use the `cronjob` tool when you need model pinning, profile targeting, or cross-profile operations. Use the CLI for quick one-off jobs within the current profile.

## Common Patterns

### Agent-based scrum job with skill:
```bash
hermes cron create '0 9 * * 1-5' "You are the daily scrum agent. Run the workflow and post to #sprint-management." --name 'scrum-agent-9am' --skill 'product-scrum-workflow' --deliver local
```

### Agent mode with parallel subagent delegation

For cron jobs that process N independent work items (users, repos, files), split them across parallel subagents to stay under the 120s no_agent timeout AND keep any single subagent under 60s:

```python
# Cron job: agent mode (no_agent=false), no script
# Prompt tells the agent to delegate_task with a tasks array:

# STEP 1 — Delegate 3 subagents in parallel (batch mode):
#   Task A: processes items 1-3
#   Task B: processes items 4-6
#   Task C: processes items 7-9
#
# Each subagent runs a self-contained command with its own subset:
#   python3 script.py --subset "item1,item2,item3"
#
# STEP 2 — Sum totals from all 3 subagents
# STEP 3 — Report; if total==0 respond "[SILENT]"
```

Key design rules for this pattern:
- Each subagent must be **self-contained** — it does its own work AND its own import/upload. Don't have subagents collect data then the parent import it — the parent would face the same bottleneck.
- Use `--self-import` or equivalent flags so each subagent processes only its own output files, not an accumulated directory.
- Subagents use `toolsets: terminal, file` — no browser, no delegation.
- The parent agent only sums and reports — no heavy lifting.
- `[SILENT]` rule: if ALL subagents return 0, the agent responds with exactly `[SILENT]`.

### No-agent script timeouts

No-agent scripts have a **120s hard timeout** from the cron scheduler. If a script runs longer, it's killed and the job shows `last_status: error` with "Script timed out after 120s".

Common timeout causes and fixes:
- **`gbrain import` on accumulated directories**: Over time, collectors dump thousands of files into `~/brain/data/email/`. `gbrain import --no-embed` scans ALL of them even though most are already imported. At ~2 files/second, 2,870 files = 24+ minutes. **Fix**: Import only specific new files (`gbrain import --no-embed <file1> <file2> ...`) rather than the entire directory.
- **Daemon loops as cron jobs**: `while true` scripts always time out. Convert to one-shot checks.
- **External API calls hanging**: Broken OAuth tokens cause API calls to hang until timeout. Fix the auth, not the timeout.
- **Too many work items in sequence**: 9 users × 10 emails each = 90 API calls sequentially. Split across parallel subagents (agent mode) instead.
```bash
hermes cron create '*/2 * * * *' --name 'Dashboard Watchdog' --script 'dashboard-watchdog.sh' --no-agent --deliver local
```

### Agent job with prompt and script:
```bash
hermes cron create '0 3 * * *' "Run the sync and report how many files changed." --name 'git-sync' --script 'sync.sh' --deliver origin
```

## Pitfalls

- **The positional prompt must come IMMEDIATELY after the schedule**, before any named flags. This is the #1 cause of failed cron job creation.
- **`--model` does not exist** on `hermes cron create`. Don't attempt it.
- **`--script` path is relative to `~/.hermes/scripts/`**, not an absolute path or inline command.
- **Always quote the prompt** in double quotes when it contains special characters like `#`, `$`, or parentheses.
- **Cron jobs are profile-scoped** — `hermes cron list` shows only jobs for the active profile.
- **Scope precision — do only what was explicitly asked.** If the user says "move gmail-triage and gmail-morning-summary to profile X", move exactly those two. Do not add other gmail jobs, scrum jobs, or anything else unless asked. Expanding scope without instruction is a correction magnet.
- **To stop a no-agent job from delivering output**, ensure the script produces empty stdout on success. Non-empty stdout = delivery.
- **`delegate_task` subagents time out at ~600s** — do NOT use them for scripts that run 300s+. Instead, use `terminal(background=true, notify_on_complete=true)` + poll loop. See `references/long-running-script-patterns.md` for the working pattern and real failure evidence.
- **`process(action='wait', timeout=N)` is clamped to 60s** regardless of what you pass. If your script takes longer, you MUST use `process(action='poll')` in a loop instead.
