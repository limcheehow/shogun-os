---
name: department-scrum
description: "Universal cross-department scrum workflow — 3-tier cadence (9am/11am/5pm). Any profile loads this for their daily standup, quality tracking, and brain cross-reference. Replaces per-dept hardcoded scripts with profile-parameterized config."
version: 3.0.0
tags: [shared, scrum, standup, cron, cross-department, compliance, production-hardened]
triggers:
  - "morning scrum"
  - "midday scrum"
  - "evening scrum"
  - "standup"
  - "blockers"
  - "compliance report"
  - "daily check-in"
  - "scrum config"
  - "scrum setup"
  - "init scrum"
---

# Cross-Department Scrum Workflow

Unified daily scrum system for **any Hermes Agent profile** — Project, Product, HR, Finance, CRM, Marketing, Procurement, Compliance, Support. One workflow, per-profile config.

## Architecture

```
9:00 AM ── send-scrum-dms.py (no_agent script)
               → Reads scrum.yaml for team roster
               → Opens Slack DM with each member
               → Sends 4 standard questions
               → Saves state to scrum-states/{profile}/{date}.json
               → Stdout summary → cron delivery to home channel

REALTIME ── Gateway agent (no daemon, no socket mode)
               → Slack Events API delivers DMs directly to gateway
               → SOUL.md routes: scrum reply → save + post to channel
                              non-scrum → answer with domain knowledge

11:00 AM ── check-scrum-replies.py warn (LLM agent)
               → Reads state file + scrum.yaml (brain cross-ref rules)
               → Cross-references replies against gbrain
               → Warns non-responders via Slack DM
               → Holiday gate: KL holidays skip scrum

5:00 PM  ── check-scrum-replies.py report (LLM agent)
               → Full compliance report
               → Quality gates (SMART-adapted per domain)
               → Brain cross-reference
               → Logs to gbrain _scrum/{profile}/{date}
               → Holiday gate: KL holidays skip scrum
```

## The 4 Standard Questions

Every department asks the same structure — domain context adapts the cross-ref:

1. **Yesterday** — What tasks did you complete?
2. **Today** — What are you working on?
3. **Blockers** — Any obstacles?
4. **Help needed** — Anything you need from someone?

## Cross-Department Config

**Every profile** that wants scrum creates a `scrum.yaml` in their profile directory:

```yaml
# ~/.hermes/profiles/<profile>/scrum.yaml
profile: project-manager
app_name: Gorobei                    # Used in DM greetings
channel_updates: "C0XXXXXXXX"      # Where scrum summaries post
channel_leadership: "C0XXXXXXXX"   # Where enriched 5pm reports post
state_dir: "~/.hermes/scrum-states/<profile>"

brain:
  source: "projects"                 # gbrain source for cross-ref
  task_id_patterns:                  # How to find task IDs in replies
    - pattern: 'TS-20\\d{2}-\\d{3}'  # MUST use single quotes for regex in YAML!
      label: "Support Ticket"
  project_keywords:                  # Domain term list for matching
    - "Alam Flora"
    - "IOI"
    - "Kossan"
  custom_ref:                        # Optional: extra brain paths
    project_dir: "~/brain/projects/active_projects/"
    ticket_index: "~/brain/projects/support_tickets/INDEX.md"
```

See `references/scrum-config-schema.md` for the full spec.

## Cron Jobs

Each profile instantiates 3 (or 4 including holiday gate) cron jobs.

### 9am — Send DMs (no_agent)

```yaml
name: "<profile>-scrum-9am"
schedule: "0 9 * * 1-5"
script: "send-scrum-dms.py --profile <profile>"
no_agent: true
deliver: "slack:<channel_updates>"
```

### 11am — Warn Non-Responders (LLM agent)

```yaml
name: "<profile>-scrum-11am"
schedule: "0 11 * * 1-5"
prompt: |
  Loaded skills: department-scrum, task-management, staff-lookup
  
  STEP 1 — Run check script in warn mode:
    python3 ~/.hermes/scripts/scrum/check-scrum-replies.py warn --profile <profile>
  
  STEP 2 — Read state from scrum-states/<profile>/{date}.json
  
  STEP 3 — Cross-ref replies against gbrain source: <source>
    - Extract task IDs using the profile's task_id_patterns
    - Match domain terms against brain pages
    - Flag unmatched items as brain_missing
  
  STEP 4 — Post summary to slack:<channel_updates> with:
    - How many new replies
    - Cross-ref results (matched / missing)
    - Non-responder count
skills: ["department-scrum", "task-management", "staff-lookup"]
deliver: "slack:<channel_updates>"
```

### 5pm — Compliance Report (LLM agent)

```yaml
name: "<profile>-scrum-5pm"
schedule: "0 17 * * 1-5"
prompt: |
  Loaded skills: department-scrum, task-management, staff-lookup
  
  STEP 1 — Run check script in report mode:
    python3 ~/.hermes/scripts/scrum/check-scrum-replies.py report --profile <profile>
  
  STEP 2 — Read state from scrum-states/<profile>/{date}.json
  
  STEP 3 — Full brain cross-ref on ALL replies (use domain rules from scrum.yaml)
  
  STEP 4 — Quality scan using SMART gates
  
  STEP 5 — Post enriched summary to slack:<channel_leadership>
skills: ["department-scrum", "task-management", "staff-lookup"]
deliver: "slack:<channel_updates>"
```

### Midnight — Holiday Gate (LLM agent, optional)

```yaml
name: "<profile>-scrum-holiday-gate"
schedule: "0 0 * * *"
# Checks KL holidays, pauses/resumes 9am/11am/5pm jobs
# Uses offline Hijri calendar algorithm
```

## Option B: Gateway DM Handling

**Every profile's SOUL.md** must include a "Scrum DM Handling" section. Copy from `references/soul-snippet.md`:

```markdown
## Scrum DM Handling

When someone DMs you, check if they are in today's scrum team. State file: 
`~/.hermes/scrum-states/{profile}/{today}.json`. Team list is under `team` key.

**If they are a team member and haven't submitted yet:**
1. Read their message — is it a scrum reply (answers the 4 questions)?
2. If complete → run `python3 ~/.hermes/scripts/scrum/check-scrum-replies.py report --profile {profile}` to save state, then post formatted submission to Scrum DM channel using Slack API
3. If incomplete → ask for missing parts
4. If already submitted → acknowledge, don't re-post

**If NOT a team member:** Help them with domain knowledge.
```

## SMART Quality Gates (Domain-Adapted)

| Gate | What we check | ❌ Fail |
|---|---|---|
| **Specific** | Names a concrete project/ticket/task/initiative | "working on stuff", "same as before" |
| **Measurable** | Has an outcome or deliverable | "no updates" |
| **Achievable** | Single-day scope | "finish the entire project" |
| **Relevant** | Cross-ref: does it exist in brain? | Unrecognized project/ticket ID |

Each profile's `scrum.yaml` defines what "Specific" means for that domain (project names, ticket patterns, initiative names, etc.).

## Domain-Specific Adaptations

Each profile's scrum.yaml customizes the cross-ref rules:

| Profile | Task IDs | Project Terms | Brain Source |
|---|---|---|---|
| **Projects (Gorobei)** | `TS-20\d{2}-\d{3}` | Company/project names | `projects/` |
| **Product (Shi)** | `SAM-\d{2}-\d{2}-\d{3,4}`, `INT-\d+`, `EP-\d+` | Feature names | `products/` |
| **HR (Jinzai)** | `HR-\d+` | Leave types, hiring phases | `hr/` |
| **Finance (Koku)** | `PO-\d+`, `INV-\d+` | Budget codes, vendor names | `finance/` |
| **CRM (Kizuna)** | Deal pipeline IDs | Client names | `crm/` |
| **Marketing (Haiku)** | Campaign IDs | Campaign names | `marketing/` |
| **Support (Bōei)** | `TS-20\d{2}-\d{3}` | Client names, severities | `support/` |

## Holiday Gate

KL public holidays skip all scrum activity. Uses offline Hijri calendar algorithm (see `references/holiday-gate.md`).

On holiday:
- 9am cron fires → checks holiday → reports "scrum paused for <holiday>" → exits (no DMs)
- 11am/5pm crons skip their checks
- Midnight gate job auto-pauses/resumes

## State File Schema

`~/.hermes/scrum-states/{profile}/{date}.json`

| Field | Type | Description |
|---|---|---|
| `date` | str | ISO date |
| `profile` | str | Profile name |
| `questions_sent_at` | str | ISO timestamp |
| `team[].name` | str | Member name |
| `team[].slack_id` | str | Slack user ID |
| `team[].role` | str | Department role |
| `team[].replied` | bool | Has replied |
| `team[].reply_text` | str | Raw reply |
| `team[].replied_at` | str | Slack timestamp |
| `team[].compliance` | str | `on_time`, `late`, `missed` |
| `team[].confidence` | str | `high`, `medium`, `low` |
| `team[].issues` | list | Issue codes |
| `team[].tasks_matched` | list | Task IDs found in brain |
| `team[].brain_missing` | list | Ref not in brain |
| `errors` | list | Slack API errors |

## Scripts

| Script | Type | Purpose |
|---|---|---|
| `~/.hermes/scripts/scrum/send-scrum-dms.py` | `no_agent` | Reads scrum.yaml, sends DMs, saves state |
| `~/.hermes/scripts/scrum/check-scrum-replies.py` | Agent-run | Two modes: `warn` (11am), `report` (5pm) |

Both scripts accept `--profile <name>` and read config from `~/.hermes/profiles/<name>/scrum.yaml`.

## Related Skills

- `task-management` — Unified task schema for creating/querying tasks (MUST load before cron prompts)
- `staff-lookup` — Resolve names to Slack IDs, check leave status
- `project-scrum-workflow` — Legacy, will be deprecated
- `product-scrum-workflow` — Legacy, will be deprecated

## Pitfalls

### YAML Regex Patterns Must Use Single Quotes

This is the #1 gotcha when creating `scrum.yaml`. YAML double-quoted strings parse escape sequences, and `\d` is **not** valid YAML:

```yaml
# ❌ ScannerError: unknown escape character 'd'
task_id_patterns:
  - pattern: "TS-20\d{2}-\d{3}"

# ✅ Single quotes pass the regex literally
task_id_patterns:
  - pattern: 'TS-20\d{2}-\d{3}'
```

All regex `task_id_patterns` in `scrum.yaml` must use **single quotes**. Non-regex fields (names, channel IDs) can stay double-quoted.

### False Positive: "Blockers: none" Flagged as Non-Update

The quality assessment's `question_not_update` check used substring matching. `"none"` in a reply like "Blockers: none" would match and flag a legitimate scrum answer as non-compliant.

**Fix (applied to check-scrum-replies.py and test):** Check for standalone empty answers only:
- Substring match: `"no update"`, `"same as before"`, `"nothing new"` (these are reliably bad)
- Exact match: `text_lower.strip() in ("none", "n/a", "na", "no", "nothing", "same")` (entire answer is just this word)

Do NOT substring-match on `"none"`, `"no"`, `"same"`, or `"nothing"` — they appear in legitimate context ("no blockers", "none on my side", "same project, different task").

### Cross-Department Isolation

Task ID patterns MUST NOT overlap between departments:
- Project patterns (`TS-20\d{2}-\d{3}`, `PRJ-\d{3}`) should NOT match product task IDs
- Product patterns (`SAM-\d{2}-\d{2}-\d{3,4}`, `INT-\d+`, `EP-\d+`) should NOT match project tickets
- Verified by test suite: cross-dept pattern isolation is enforced

If patterns do accidentally overlap, replies from one department get enriched against the wrong brain source. Keep pattern regexes specific to each department's ID format.

### Script Token Resolution

Both `send-scrum-dms.py` and `check-scrum-replies.py` resolve `SLACK_BOT_TOKEN` in this order:
1. Environment variable `SLACK_BOT_TOKEN` (highest priority — for cron jobs that inject via grep)
2. `~/.hermes/profiles/<profile>/.env`
3. `~/.hermes/.env` (global fallback)

In cron jobs, token quoting can break if injected inline via shell. Always use `os.environ` pattern (export to env var first, read in Python as `os.environ['TOKEN']`) rather than inline string interpolation in a `python3 -c "..."` command.

## Test Suite

A comprehensive cross-department test suite is at:

```
~/.hermes/scripts/scrum/test-scrum-cross-dept.py
```

Run: `python3 ~/.hermes/scripts/scrum/test-scrum-cross-dept.py`

Tests (48 total):
- Config parsing for 4 departments (Projects, Products, HR, Finance)
- Task ID extraction across all 4 department patterns
- Domain term matching
- SMART quality gates (with "no blockers" false-positive guard)
- State file schema compliance (14 member fields, 7 top-level fields)
- Script runnability and --profile requirement
- Cross-department isolation (no pattern leaks)
- Edge cases (empty replies, minimal replies, empty patterns)

Add new tests before deploying scrum.yaml for a new department.

## Production Pitfalls

**15 hard-won lessons from running this workflow in production.** Each was discovered during live operation and is documented in `references/production-pitfalls.md`. Read them before deploying scrum for the first time.

Key ones to know upfront:

| # | Pitfall | One-liner |
|---|---|---|
| 1 | Gateway healthy but WebSocket dead | `systemctl is-active` ≠ gateway actually receiving messages |
| 3 | Cron batch-fire race condition | Save state BEFORE sending DMs, not after |
| 4 | HERMES_HOME points to profile dir | Use `~/.hermes` expanded, not `$HERMES_HOME` |
| 8 | Save state AFTER posting to channel | Otherwise crash leaves `posted_to_channel: null` |
| 10 | Non-standard compliance_state values | Only use `ok` / `pending_clarification` |
| 14 | Duplicate systemd services | Check for both user and system level units |

**See `references/production-pitfalls.md` for full details, detection commands, and fixes.**

## Migration Path

| Phase | What changes | Status |
|---|---|---|
| 1 | Create `department-scrum` shared skill + templates | ✅ Complete |
| 2 | Write generic `send-scrum-dms.py` | ✅ Complete |
| 3 | Write generic `check-scrum-replies.py` | ✅ Complete |
| 4 | Create `scrum.yaml` for project-manager profile | ✅ Complete |
| 5 | Convert project scrum crons to new pattern | ✅ Deployed |
| 6 | Create `scrum.yaml` for product-manager profile | ✅ Deployed |
| 7 | Convert product scrum crons to new pattern | ✅ Deployed |
| 8 | Add scrum to HR, Finance, CRM, etc. | ⏳ Per-profile create scrum.yaml + crons |
| 9 | Deprecate old per-dept scrum skills | ⏳ After all profiles migrated |
| 10 | Merge production pitfalls (v3.0.0) | ✅ Complete — 15 pitfalls documented |