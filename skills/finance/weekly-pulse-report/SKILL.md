---
name: weekly-pulse-report
description: "Use when generating the Weekly Financial Pulse report — cash & runway status, AR aging collections focus, AP commitments, and MTD revenue & spend pacing. Produces a formatted report delivered to Slack/Telegram and saved to gbrain."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, reporting, weekly, pulse, ar, ap, cash, mtd, executive]
    category: finance
    related_skills: [cfo-executive-reporting, monthly-board-report, cash-runway-forecasting, ar-credit-control]
---

# Weekly Financial Pulse Report Generator

## Overview

Compiles on-demand Weekly Financial Pulse reports that summarise cash & runway status, AR aging collections focus, AP commitments due this week, and MTD revenue & spend pacing. The skill executes the four-step `acct_*` data-gathering sequence defined in the spec, formats the output into the standard "Weekly Financial Pulse" template, saves a copy to the `finance` gbrain source, and delivers it via the `department-scrum` comm layer. Script: `scripts/weekly_pulse.py`.

## When to Use

- User sends: `"Koku, generate the weekly financial report for this week"`, `"Give me the weekly financial pulse"`, or `/weekly-report`
- The weekly scheduled cron triggers the pulse report
- An ad-hoc cash-position check is requested by the CFO

Don't use for: full monthly board report — see [monthly-board-report](../monthly-board-report/SKILL.md); deep cash runway modelling — see [cash-runway-forecasting](../cash-runway-forecasting/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_balance_sheet`, `acct_get_aging_report`, `acct_list_purchase_bills`, `acct_get_profit_loss` (existing `acct_*` contract tools)
- gbrain `finance` source (report archive at `finance/reports/weekly/`)
- Comm layer: `skills/department-scrum/scripts/comm/` for Slack / Telegram delivery
- Script: `skills/finance/weekly-pulse-report/scripts/weekly_pulse.py`

## Data-Gathering Sequence

Executed in order by `weekly_pulse.py`:

1. `acct_get_balance_sheet(as_of_date=today)` → Cash & Bank balances, Total Assets, Total Liabilities for the Cash & Runway section.
2. `acct_get_aging_report(type="receivable")` → Total AR, overdue amounts (>30, 60, 90 days), and top unpaid invoices for the AR Collections section.
3. `acct_get_aging_report(type="payable")` + `acct_list_purchase_bills(date_from=7_days_ago, date_to=today)` → AP due this week and total outstanding supplier bills for the AP Commitments section.
4. `acct_get_profit_loss(date_from=month_start, date_to=today)` → MTD Revenue and Expenses for the Revenue & Spend Pacing section.

## Output Format

```
📊 WEEKLY FINANCIAL PULSE (Week Ending: <date>)
Prepared by: Koku (Finance Manager) | Source: QuickBooks Online

1. 💵 Cash & Runway Status
   - Available Bank Balance: $<amount>
   - Avg Monthly Burn Rate: $<amount>
   - Estimated Cash Runway: <N> Months (<status>)

2. 📥 Accounts Receivable (Collections Focus)
   - Total Outstanding AR: $<amount>
   - Current (0-30 Days): $<amount>
   - Overdue (>30 Days): $<amount> (<N> invoices)
   - ⚠️ Priority Collections Action Required:
     - <client>: $<amount> (<days> days overdue — Invoice #<ref>)

3. 📤 Accounts Payable & Upcoming Commitments
   - Payments Due This Week: $<amount>
   - Total Outstanding AP: $<amount>

4. 📈 Month-To-Date (MTD) Revenue & Spend Pacing
   - MTD Revenue (<days> Days): $<amount> (Target Pace: $<amount> | <pct>% of Target)
   - MTD Expenses: $<amount>
   - Net MTD Operating Surplus/Deficit: <+/->$<amount>
```

## Workflows

### Generate Weekly Pulse Report

1. Run `weekly_pulse.py` (or invoke steps manually) to execute the 4-step data-gathering sequence — done when: all four sections have data from the `acct_*` tools.
2. Format the output per the template above — done when: the report renders cleanly with no `NOT_IMPLEMENTED` errors from any `acct_*` call.
3. Save the report to `finance/reports/weekly/<YYYY-MM-DD>.md` in the gbrain finance source — done when: the archive file is written.
4. Deliver via the `department-scrum` comm layer — done when: the message is confirmed sent to the target channel.

## Common Pitfalls

1. **Month-start boundary** — `month_start` should be the first calendar day of the current month, not 30 days ago; using 30 days ago shifts the pacing window incorrectly.
2. **Burn rate from P&L vs. cash flow** — the burn rate in Step 1 is estimated from MTD OPEX in the P&L; for a cash-basis burn rate, use the `cash-runway-forecasting` skill's dedicated workflow.
3. **AR priority list length** — cap the priority collections list at the top 5 overdue invoices (by amount) to keep the report actionable; a list of 30 invoices is not executive-readable.
4. **Comm layer message size** — Slack message limits apply; if the report exceeds ~4,000 characters, split or post as a file attachment.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/weekly-pulse-report/`
- [ ] `/weekly-pulse-report` loads on the `finance-manager` profile
- [ ] `python skills/finance/weekly-pulse-report/scripts/weekly_pulse.py` returns all four sections without `NOT_IMPLEMENTED` errors
- [ ] Report saved to `finance/reports/weekly/<date>.md` in the gbrain finance source
