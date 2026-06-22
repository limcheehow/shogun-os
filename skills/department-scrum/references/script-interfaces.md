# Generic Scrum Script Interfaces

## `send-scrum-dms.py`

One script for ALL departments. Reads config from profile's `scrum.yaml`.

```bash
python3 ~/.hermes/scripts/scrum/send-scrum-dms.py --profile project-manager
```

### How it works

1. Reads `~/.hermes/profiles/<profile>/scrum.yaml`
2. For each team member:
   - Opens Slack DM via `conversations_open`
   - Sends the 4 standard questions
   - Records `dm_channel` and `question_ts`
3. Writes state file to `~/.hermes/scrum-states/<profile>/{date}.json`
4. Logs to gbrain at `_scrum/<profile>/{date}`
5. Prints summary to stdout (captured by cron delivery)

### Stdout format

```
=== Scrum Send: <profile> — 2026-06-22
 Team size: 9

  [OK] Sheikh Syazwan         (Head of Project)     -> DM sent
  [OK] Mohd Fitri Abdullah    (Technical PM)         -> DM sent
  [ERR] ...                   (...)                  -> error message

State saved to ~/.hermes/scrum-states/<profile>/2026-06-22.json
Logged to gbrain _scrum/<profile>/2026-06-22
```

### Error handling

- Individual member Slack errors don't crash the script
- Errors are recorded in the state file under `errors` array
- Script exits with code 0 even with partial errors (the agent decides severity)

### Dependencies

- `slack_sdk` (pip install)
- `PyYAML` (pip install)
- Slack bot token in profile's `.env`

---

## `check-scrum-replies.py`

One script for ALL departments. Does both warn (11am) and report (5pm) modes.

```bash
# Warn mode — 11am: check replies, warn non-responders
python3 ~/.hermes/scripts/scrum/check-scrum-replies.py warn --profile project-manager

# Report mode — 5pm: full compliance, quality gates, brain cross-ref
python3 ~/.hermes/scripts/scrum/check-scrum-replies.py report --profile project-manager
```

### How it works

1. Reads `~/.hermes/profiles/<profile>/scrum.yaml`
2. Loads today's state file from `~/.hermes/scrum-states/<profile>/{date}.json`
3. For each member without `replied=true`:
   - Checks for thread replies via `conversations_replies`
   - Updates state with reply_text, replied_at, replied=true
4. **Quality assessment** (built-in, not LLM-dependent):
   - Checks for 4-question format compliance
   - Assigns confidence: high/medium/low
   - Flags issues: `no_project_match`, `question_not_update`, `too_short`, etc.
5. **Brain cross-ref** (uses scrum.yaml patterns):
   - Extracts task IDs using `brain.task_id_patterns` regex
   - Matches `brain.domain_terms` keywords in reply text
   - Checks against gbrain source or local files
6. **Warn mode** (11am):
   - Sends Slack DMs to non-responders (only if not warned yet)
   - Posts summary to channel_updates
7. **Report mode** (5pm):
   - Full compliance stats (on_time / late / missed)
   - Per-member table with matched/missing items
   - Posts enriched report to channel_leadership
   - Logs final state to gbrain

### Stdout format (warn)

```
=== Scrum Warn: <profile> — 2026-06-22
 Members: 9 total
 Replied: 5 | Non-responders: 4
 Warnings sent: 4
 Brain cross-ref: 12 tasks matched, 2 missing
```

### Stdout format (report)

```
=== Scrum Report: <profile> — 2026-06-22
 Members: 9 total, 8 replied, 1 missed
 Compliance: 6 on_time, 2 late, 1 missed (77.8%)
 Quality flags: 2 vague, 1 no_project_match
 Brain cross-ref: 15 tasks matched, 3 missing
 Overdue projects: 1 flagged
 Posted to #project-leadership
 Logged to gbrain _scrum/<profile>/2026-06-22
```

### Dependencies

- `slack_sdk` (pip install)
- `PyYAML` (pip install)
- Slack bot token in profile's `.env`