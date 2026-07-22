# Cronjob Delivery Audit — Session Walkthrough

Real scenario: User asked "what cronjobs are currently sent to the HR group?"

## Step 1: Cronjob List (Tool API)

```
cronjob action=list
```

Returns 34 jobs with `deliver`, `last_status`, `schedule` — but no `origin.chat_name`.
The `deliver` field shows only "origin" or "local", not *which* chat origin routes to.

## Step 2: Read jobs.json Directly

```bash
cat ~/.hermes/cron/jobs.json
```

Each job entry has a full `origin` object:

```json
{
  "id": "bcf83b72acad",
  "name": "gmail-morning-summary",
  "deliver": "origin",
  "origin": {
    "platform": "telegram",
    "chat_id": "-1003773708968",
    "chat_name": "Company HR",
    "thread_id": null
  }
}
```

Search for `"chat_name": "Company HR"` (or target group) to find all jobs originating from that group.

## Step 3: Check for Cross-Profile Jobs

Check if target profile has its own state.db:

```bash
find ~/.hermes/profiles/hr-manager/ -name "state.db"
# → /home/tapway/.hermes/profiles/hr-manager/state.db
```

Check its SQLite tables:

```bash
sqlite3 ~/.hermes/profiles/hr-manager/state.db ".tables"
# → messages, sessions, etc. but NO cron_jobs table
```

Check cron directory:

```bash
ls ~/.hermes/profiles/hr-manager/cron/
# → only .tick.lock and output/ — no separate job storage
```

Conclusion: the HR profile shares the default scheduler's jobs from `~/.hermes/cron/jobs.json`.

## Step 4: Classify and Report

For the HR group, 28 jobs had origin `"Company HR"`:

**Deliver: origin (8 jobs — actively sent to HR group):**

| Job | Schedule | Type | Status |
|-----|----------|------|--------|
| gmail-triage | Every 15min weekdays | Agent | ✅ OK |
| gmail-morning-summary | 8am weekdays | Agent | ✅ OK |
| gmail-urgent-alert | 9/11/13/15/17 weekdays | Agent | ✅ OK |
| github-task-backfill | Daily 6am | Agent | ✅ OK |
| product-brain-github-sync | Daily 3am | Agent | ⏳ Pending |
| gbrain-dream-cycle | Daily 2am | Script | ⏳ Pending |
| Brain Validator Watchdog | Daily 9am | Script | ⏳ Pending |
| Supabase Watcher Watchdog | Every 2min | Script | ✅ OK |

**Deliver: local (20 jobs — not sent to HR):**
BrioHR syncs, scrum agents, brain collectors, dashboards, org chart, etc.
These run but don't message the group.

## Key Insight: "Origin" ≠ "Deliver"
- `origin` = where the job was created (who owns it)
- `deliver` = whether output goes back there ("origin") or stays local ("local")
- A job with origin:HR but deliver:local runs silently in HR's context without spamming the group
- Only the cronjob tool's output shows both fields separated — the CLI `hermes cron list` does not