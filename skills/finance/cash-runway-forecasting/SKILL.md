---
name: cash-runway-forecasting
description: "Use when computing net monthly burn rate, cash runway (months), or 13-week rolling liquidity forecasts. Produces a runway summary and 13-week cash forecast table."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, cash, runway, burn-rate, liquidity, forecasting, treasury]
    category: finance
    related_skills: [budget-financial-modeling, bva-variance-analysis, treasury-fx-facility-mgmt]
---

# 13-Week Cash Flow & Runway Modeling

## Overview

Computes net monthly burn rate, cash runway (months), and 13-week rolling liquidity forecasts. The skill produces a runway summary (current cash / monthly burn = runway months) and a week-by-week 13-week cash forecast table, using existing `acct_*` contract tools for balances and actuals — no new treasury or banking integration is implied.

## When to Use

- Board or investor meeting requires a cash runway statement
- Monthly finance review needs a 13-week liquidity forecast
- Cash balance has changed significantly and a revised runway estimate is needed
- The `cfo-executive-reporting` / `weekly-pulse-report` skill needs the cash-runway section

Don't use for: FX and credit facility monitoring — see [treasury-fx-facility-mgmt](../treasury-fx-facility-mgmt/SKILL.md); budget modelling — see [budget-financial-modeling](../budget-financial-modeling/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_balance_sheet`, `acct_get_profit_loss` (existing `acct_*` contract tools)
- gbrain `finance` source (forecast assumptions at `finance/cash-forecast/`)

## Workflows

### Monthly Burn Rate & Runway Calculation

1. Pull current cash and bank balances via `acct_get_balance_sheet(as_of_date=today)` — done when: total liquid cash (checking + savings, net of overdraft) is known.
2. Pull last-3-months OPEX actuals via `acct_get_profit_loss(date_from=3_months_ago, date_to=today)` — done when: average monthly net cash outflow (burn rate) is computed as `(total_expenses − non_cash_items) / 3`.
3. Compute runway: `runway_months = current_cash / avg_monthly_burn` — done when: runway months are calculated and a status label is assigned (Critical <2 months / Caution 2-4 months / Healthy >4 months).

### 13-Week Rolling Liquidity Forecast

1. Load the 13-week forecast assumptions (expected receipts and disbursements per week) from `finance/cash-forecast/` in the gbrain finance source — done when: weekly inflow and outflow assumptions are available for each of the 13 weeks.
2. Apply AR collection schedule from `acct_get_aging_report(type="receivable")` to refine expected receipts — done when: expected collections by week are updated from the live aging data.
3. Apply AP payment schedule from `acct_get_aging_report(type="payable")` to refine expected disbursements — done when: expected payments by week are updated from live AP data.
4. Produce the 13-week cash forecast table: Week | Opening Cash | Receipts | Disbursements | Closing Cash — done when: all 13 rows are populated and closing cash is non-negative (or a liquidity warning is raised if it turns negative in any week).

## Common Pitfalls

1. **13-week liquidity horizon** — the 13-week window is the standard short-term liquidity management horizon; shorter windows miss payment timing risks and longer windows lose precision.
2. **Non-cash burn exclusion** — depreciation and amortisation are non-cash items; exclude them from the cash burn computation to avoid overstating the burn rate.
3. **Committed but unbooked outflows** — large vendor contracts or payroll commitments not yet in AP must be manually added to the forecast; the `acct_*` tools only reflect booked transactions.
4. **Runway status thresholds** — "Healthy >4 months" and "Critical <2 months" are finance-manager conventions aligned with the weekly pulse report; do not change without updating the report template.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/cash-runway-forecasting/`
- [ ] `/cash-runway-forecasting` loads on the `finance-manager` profile
- [ ] Happy-path runway calculation produces a runway-months figure and a status label
- [ ] 13-week forecast table produces 13 rows with non-negative closing cash (or an explicit liquidity warning)
