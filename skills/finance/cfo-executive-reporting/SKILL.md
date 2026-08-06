---
name: cfo-executive-reporting
description: "Use when compiling on-demand Weekly Pulse and Monthly Board reports delivered directly to Slack or Telegram. Produces a formatted executive report and triggers delivery via the department-scrum comm layer."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, reporting, cfo, slack, telegram, executive, pulse, board]
    category: finance
    related_skills: [weekly-pulse-report, monthly-board-report, revenue-concentration-audit, bva-variance-analysis]
---

# CFO Briefing & Executive Pulse Reports

## Overview

Compiles on-demand Weekly Pulse and Monthly Board reports delivered directly to Slack or Telegram. The skill orchestrates the `weekly-pulse-report` and `monthly-board-report` skills on demand and delivers the formatted output via the existing `department-scrum` comm layer (`skills/department-scrum/scripts/comm/`) — no new messaging or API integration is implied.

## When to Use

- An executive or board member asks for the weekly or monthly financial summary via Slack or Telegram
- The regular scheduled report delivery (weekly / monthly) is triggered by the cron job
- An ad-hoc CFO briefing is requested outside the normal schedule

Triggers (any of):
- `"Koku, generate the weekly financial report for this week"`
- `"Give me the weekly financial pulse"`
- `/weekly-report`
- `"Koku, prepare the monthly financial performance report for <month> <year>"`
- `"Generate monthly board financial report"`
- `/monthly-report`

Don't use for: direct data gathering — see [weekly-pulse-report](../weekly-pulse-report/SKILL.md) and [monthly-board-report](../monthly-board-report/SKILL.md); customer concentration analysis — see [revenue-concentration-audit](../revenue-concentration-audit/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: all `acct_*` tools used by the underlying report skills (delegated)
- gbrain `finance` source (report archives at `finance/reports/`)
- Comm layer: `skills/department-scrum/scripts/comm/` for Slack / Telegram delivery

## Workflows

### Weekly Pulse Report (On-Demand)

1. Detect the trigger intent (weekly pulse / `/weekly-report`) — done when: report type and target date are confirmed.
2. Delegate to the `weekly-pulse-report` skill's data-gathering sequence — done when: the formatted pulse report is returned.
3. Deliver the report via the `department-scrum` comm layer to the requesting Slack channel or Telegram chat — done when: the message is confirmed sent.
4. Save a copy to `finance/reports/weekly/<YYYY-MM-DD>.md` in the gbrain finance source — done when: the archive file is written.

### Monthly Board Report (On-Demand)

1. Detect the trigger intent (monthly board / `/monthly-report`) and extract the target month/year — done when: period is confirmed (defaults to last completed calendar month).
2. Delegate to the `monthly-board-report` skill's data-gathering sequence including BvA — done when: the full formatted board report is returned.
3. Deliver the report via the `department-scrum` comm layer to the requesting channel — done when: the message is confirmed sent.
4. Save a copy to `finance/reports/monthly/<YYYY-MM>.md` in the gbrain finance source — done when: the archive file is written.

## Common Pitfalls

1. **Comm layer dependency** — delivery relies on `skills/department-scrum/scripts/comm/`; if the comm layer is not configured for the `finance-manager` profile, the report will be generated but not delivered. Verify the comm config before declaring this skill live.
2. **Report archive vs. delivery** — always save the archive first, then deliver; if delivery fails, the report is not lost.
3. **On-demand vs. scheduled** — this skill handles on-demand triggering; scheduled delivery is wired via `scripts/wire-crons.py`. Do not duplicate the schedule inside this skill.
4. **Large report truncation** — Slack message limits (~4,000 characters) may truncate long board reports; split into multiple messages or post as a file attachment if the report exceeds the limit.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/cfo-executive-reporting/`
- [ ] `/cfo-executive-reporting` loads on the `finance-manager` profile
- [ ] `/weekly-report` trigger produces the weekly pulse report and delivers it to the test Slack channel
- [ ] `/monthly-report` trigger produces the monthly board report (with BvA section) and saves it to `finance/reports/monthly/`
