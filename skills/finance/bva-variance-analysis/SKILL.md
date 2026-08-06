---
name: bva-variance-analysis
description: "Use when tracking line-item spending against budget baselines and flagging department cost overruns exceeding 10%. Produces a Budget vs. Actual variance report with flagged lines and a BvA section for the monthly board report."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, bva, variance, budget, opex, overrun, analysis]
    category: finance
    related_skills: [budget-financial-modeling, monthly-board-report, cfo-executive-reporting]
---

# Budget vs. Actual Variance Analysis

## Overview

Tracks line-item spending against budget baselines and flags department cost overruns exceeding 10%. The skill produces a Budget vs. Actual variance report with per-line variance amounts, variance percentages, and a ">10% overrun" flag for each line — implemented via the local `variance.py` script that reads `finance/budget.json` from the gbrain finance source and calls existing `acct_get_profit_loss` / `acct_get_balance_sheet` contract tools for actuals. No contract edit or plugin change is involved.

## When to Use

- Month-end close requires a BvA section in the board report
- A department manager asks why their cost centre shows an overrun
- Finance review needs a full-period variance breakdown by account line
- The `monthly-board-report` skill calls this skill's `variance.py` script internally

Don't use for: authoring the budget file — see [budget-financial-modeling](../budget-financial-modeling/SKILL.md); producing the full board report — see [monthly-board-report](../monthly-board-report/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_profit_loss`, `acct_get_balance_sheet` (existing `acct_*` contract tools)
- gbrain `finance` source — `finance/budget.json` must exist (authored by `budget-financial-modeling`)
- Script: `skills/finance/bva-variance-analysis/scripts/variance.py`

## Workflows

### BvA Variance Report

1. Load `finance/budget.json` from the gbrain finance source — done when: budget lines (account_code, account_name, budget_amount) are available. If absent, degrade gracefully: return a "BvA section unavailable — budget.json not found" message and exit without error.
2. Pull actuals via `acct_get_profit_loss(date_from=period_start, date_to=period_end)` — done when: actual spend per account line is returned for the same period as the budget.
3. Compute per-line variance: `variance = actual − budget`; `variance_pct = (actual − budget) / budget × 100` — done when: every budget line has a computed variance amount and percentage.
4. Flag lines where `abs(variance_pct) > 10` with a "⚠️ >10% Variance" marker — done when: the flagged list is non-empty or explicitly empty (no overruns).
5. Return the BvA section formatted as a markdown table with columns: Account | Budget | Actual | Variance | Variance % | Flag — done when: the table renders cleanly in the board report.

## Script: `scripts/variance.py`

Standalone script invoked by `monthly-board-report` and directly for ad-hoc BvA checks:

```
python skills/finance/bva-variance-analysis/scripts/variance.py \
  --budget <path-to-budget.json> \
  --actuals <path-to-acct-pl-json>
```

- Reads `budget.json` and the actuals P&L JSON.
- Computes variance per line and prints a markdown table.
- Flags lines with >10% variance.
- Gracefully handles missing `budget.json` (prints a warning, exits 0).
- No import of `recipes.accounting.*` — pure local computation using the tool output files.

## Common Pitfalls

1. **>10% variance threshold** — the spec defines 10% as the flag threshold for department cost overruns; do not change this threshold without updating the budget model and board report template.
2. **Budget period alignment** — `budget.json` is annual; when reporting a partial period (e.g., MTD), pro-rate the budget to the same number of days to avoid structural variance.
3. **Missing budget.json — graceful degradation** — if `budget.json` is absent (e.g., new fiscal year not yet budgeted), the skill must return a clean "BvA section unavailable" message rather than an error or crash.
4. **Account code mapping drift** — if QuickBooks account codes are renumbered, budget lines will fail to match actuals; maintain a code-mapping table in `finance/budget.json`.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/bva-variance-analysis/`
- [ ] `/bva-variance-analysis` loads on the `finance-manager` profile
- [ ] `python skills/finance/bva-variance-analysis/scripts/variance.py --budget <path> --actuals <acct P&L JSON>` prints variance lines and >10% flags
- [ ] Script exits cleanly with a "BvA section unavailable" message when `budget.json` is absent
