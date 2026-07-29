---
name: monthly-board-report
description: "Use when generating the Monthly Financial Performance & Board Report — P&L breakdown, balance sheet ratios, BvA variance analysis, and customer concentration risk. Produces a formatted board report delivered to Slack/Telegram and saved to gbrain."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, reporting, monthly, board, bva, concentration, executive, kpi]
    category: finance
    related_skills: [cfo-executive-reporting, weekly-pulse-report, bva-variance-analysis, revenue-concentration-audit]
---

# Monthly Financial Performance & Board Report Generator

## Overview

Compiles on-demand Monthly Financial Performance and Board Reports that include an Executive KPI Scorecard, P&L breakdown, Balance Sheet health ratios, Budget vs. Actual (BvA) variance analysis, and customer concentration risk. The skill executes the five-step `acct_*` data-gathering sequence defined in the spec (including a call to the local `variance.py` script for the BvA section), formats the output into the standard "Monthly Financial Performance Report" template, saves a copy to the `finance` gbrain source, and delivers it via the `department-scrum` comm layer. Script: `scripts/monthly_board.py`.

## When to Use

- User sends: `"Koku, prepare the monthly financial performance report for <month> <year>"`, `"Generate monthly board financial report"`, or `/monthly-report`
- The monthly scheduled cron triggers the board report
- The board or investors require a formal monthly financial pack

Don't use for: the weekly pulse report — see [weekly-pulse-report](../weekly-pulse-report/SKILL.md); standalone BvA — see [bva-variance-analysis](../bva-variance-analysis/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_profit_loss`, `acct_get_balance_sheet`, `acct_list_contacts`, `acct_list_sales_invoices` (existing `acct_*` contract tools)
- gbrain `finance` source: `finance/budget.json` (for BvA, optional — degrades gracefully if absent), report archive at `finance/reports/monthly/`
- Comm layer: `skills/department-scrum/scripts/comm/` for Slack / Telegram delivery
- Script: `skills/finance/monthly-board-report/scripts/monthly_board.py` (calls `skills/finance/bva-variance-analysis/scripts/variance.py` for the BvA section)

## Data-Gathering Sequence

Executed in order by `monthly_board.py`:

1. `acct_get_profit_loss(date_from=last_month_start, date_to=last_month_end)` → Full Revenue, COGS, Gross Profit, OPEX, and Net Profit for the reported month.
2. `acct_get_balance_sheet(as_of_date=last_month_end)` → End-of-month Assets, Liabilities, Working Capital, and Equity for balance sheet ratios.
3. `acct_get_profit_loss(date_from=prior_month_start, date_to=prior_month_end)` → Prior month P&L for Month-over-Month (MoM) growth comparison.
4. **Local BvA computation** — call `variance.py --budget finance/budget.json --actuals <Step 1 P&L JSON>` → BvA section with per-line variances and >10% flags. If `budget.json` is absent, insert "BvA section unavailable — finance/budget.json not found" and continue.
5. `acct_list_contacts` + `acct_list_sales_invoices(date_from=last_month_start, date_to=last_month_end)` → Customer revenue concentration % for the concentration risk section.

## Output Format

```
🏛️ MONTHLY FINANCIAL PERFORMANCE REPORT — <Month Year>
Prepared by: Koku (Finance Manager) | Source: QuickBooks Online & gbrain

1. 🎯 Executive Summary & KPI Scorecard
   - Total Revenue: $<amount> (MoM: <+/-><%> | YoY: <+/-><%>)
   - Gross Profit: $<amount> (Gross Margin: <%>)
   - Operating Expenses (OPEX): $<amount>
   - Net Profit: $<amount> (Net Margin: <%>)
   - EBITDA: $<amount>

2. 📑 Profit & Loss (P&L) Account Breakdown
   - Revenue Breakdown: [by line item]
   - OPEX Breakdown: [by line item]

3. ⚖️ Balance Sheet & Financial Health Ratios
   - Cash Balance: $<amount>
   - Accounts Receivable (AR): $<amount>
   - Accounts Payable (AP): $<amount>
   - Current Ratio: <N>x (Healthy >1.5x)
   - Quick Ratio: <N>x (Healthy >1.0x)

4. 📉 Budget vs. Actual (BvA) Variance Analysis
   [BvA table from variance.py, or "BvA section unavailable" if budget.json absent]

5. 🔍 Concentration Risk & Efficiency
   - Top Client Concentration: <client> accounts for <%> of <month> Revenue
     (<⚠️ above 20% risk threshold> or <within threshold>)
   - Days Sales Outstanding (DSO): <N> Days
   - Days Payable Outstanding (DPO): <N> Days
```

## Workflows

### Generate Monthly Board Report

1. Run `monthly_board.py` (or invoke steps manually) to execute the 5-step data-gathering sequence — done when: all five sections have data and the BvA section is either populated or gracefully omitted.
2. Format the output per the template above — done when: the report renders cleanly with no `NOT_IMPLEMENTED` errors from any `acct_*` call.
3. Save the report to `finance/reports/monthly/<YYYY-MM>.md` in the gbrain finance source — done when: the archive file is written.
4. Deliver via the `department-scrum` comm layer — done when: the message is confirmed sent to the target channel.

## Common Pitfalls

1. **BvA graceful degradation** — if `finance/budget.json` is missing, the script must continue and insert a "BvA section unavailable" message rather than crash or raise an unhandled exception.
2. **MoM comparison period alignment** — "prior month" must be the immediately preceding calendar month, not 30 days ago; check month-boundary arithmetic carefully for months of different lengths.
3. **YoY growth requires prior-year data** — if the system is newly deployed, prior-year actuals may not be in QuickBooks; produce YoY as "N/A — prior year data unavailable" rather than fabricating a comparison.
4. **DSO and DPO calculation** — DSO = `(AR / monthly_revenue) × days_in_month`; DPO = `(AP / monthly_cogs) × days_in_month`; confirm the denominator used is consistent with industry convention.
5. **Comm layer message splitting** — the board report is longer than the weekly pulse; proactively split into multiple Slack messages or attach as a file if the content exceeds the character limit.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/monthly-board-report/`
- [ ] `/monthly-board-report` loads on the `finance-manager` profile
- [ ] `python skills/finance/monthly-board-report/scripts/monthly_board.py` returns all five sections without `NOT_IMPLEMENTED` errors from any `acct_*` call
- [ ] BvA section renders when `finance/budget.json` is present and is gracefully omitted when absent
- [ ] Report saved to `finance/reports/monthly/<YYYY-MM>.md` in the gbrain finance source
