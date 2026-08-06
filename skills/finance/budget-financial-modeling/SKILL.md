---
name: budget-financial-modeling
description: "Use when authoring annual operating budgets (OPEX/CAPEX), driver-based financial models, or rolling 12-month projections. Produces a structured budget model and projection file saved to the finance gbrain source."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, budget, opex, capex, model, projection, planning]
    category: finance
    related_skills: [bva-variance-analysis, cash-runway-forecasting, unit-economics-margin-analysis]
---

# Financial Modeling & Budgeting

## Overview

Authors annual operating budgets (OPEX/CAPEX), driver-based financial models, and rolling 12-month projections. The skill produces a structured budget model (stored as `finance/budget.json` in the gbrain finance source) and a 12-month projection summary, using existing `acct_*` contract tools for actuals as the baseline — no new spreadsheet or planning-tool integration is implied.

## When to Use

- Annual planning cycle requires a bottom-up OPEX and CAPEX budget for the coming year
- A rolling 12-month projection needs updating with the latest actuals
- A driver-based model (headcount, revenue-per-seat, cost-per-unit) needs building or updating
- Stakeholders request a budget file for variance tracking via the `bva-variance-analysis` skill

Don't use for: tracking actuals against budget — see [bva-variance-analysis](../bva-variance-analysis/SKILL.md); computing cash runway — see [cash-runway-forecasting](../cash-runway-forecasting/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_profit_loss`, `acct_get_balance_sheet` (existing `acct_*` contract tools, used as actuals baseline)
- gbrain `finance` source (budget stored at `finance/budget.json`, projections at `finance/projections/`)

## Workflows

### Annual Budget Build

1. Pull last-year actuals via `acct_get_profit_loss(date_from=last_year_start, date_to=last_year_end)` — done when: every OPEX and CAPEX line from the prior year is available as the budget baseline.
2. Apply driver-based growth assumptions (headcount, revenue per seat, cost per unit) provided by the stakeholder — done when: each budget line is calculated from a driver assumption, not an arbitrary percentage.
3. Structure the budget as a JSON object with keys: `period`, `year`, `lines[]` (each with `account_code`, `account_name`, `budget_amount`, `driver`, `notes`) — done when: the JSON validates against the schema expected by `variance.py`.
4. Save the budget to `finance/budget.json` in the gbrain finance source — done when: the file is written and readable by the `bva-variance-analysis` skill.

### Rolling 12-Month Projection Update

1. Pull MTD actuals via `acct_get_profit_loss(date_from=year_start, date_to=today)` — done when: YTD actuals per line are known.
2. Re-forecast remaining months using the driver assumptions and YTD run rate — done when: each future month has a revised projection amount.
3. Save to `finance/projections/rolling-<YYYY-MM>.json` in the gbrain finance source — done when: the projection file is written with the current month's timestamp.

## Common Pitfalls

1. **Top-down vs. driver-based** — percentage-of-revenue budgets mask structural cost changes; always anchor each line to a business driver (headcount, transaction volume, seat count).
2. **Budget file schema drift** — if `budget.json` structure changes, `variance.py` will fail silently; version the schema and document breaking changes.
3. **CAPEX vs. OPEX misclassification** — capitalised assets must not appear in OPEX lines; ensure depreciation is modelled separately via the `general-ledger-journal-prep` skill.
4. **Overly optimistic revenue assumptions** — anchor revenue projections to signed contracts and pipeline conversion rates, not aspirational targets, to keep the model credible.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/budget-financial-modeling/`
- [ ] `/budget-financial-modeling` loads on the `finance-manager` profile
- [ ] Happy-path annual budget build produces a valid `finance/budget.json` readable by `bva-variance-analysis`
- [ ] Rolling projection update produces a timestamped file in `finance/projections/`
