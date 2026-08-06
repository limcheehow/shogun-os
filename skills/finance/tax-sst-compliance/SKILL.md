---
name: tax-sst-compliance
description: "Use when monitoring SST-02 return filing, CP204 corporate tax estimate filings, Form C annual tax compliance, or tax penalty prevention. Produces a compliance calendar and filing checklist."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, tax, malaysia, sst, sst02, cp204, form-c, compliance, lhdn]
    category: finance
    related_skills: [mfrs15-revenue-recognition, internal-control-governance, expense-claim-audit]
---

# Corporate Income Tax & SST Compliance

## Overview

Monitors SST-02 return filing, CP204 corporate tax estimate filings, Form C annual tax compliance, and tax penalty prevention. The skill produces a tax compliance calendar with filing due dates and a filing checklist per obligation, using existing `acct_*` contract tools for revenue and expense data — no new tax-agency integration is implied.

## When to Use

- A bimonthly SST-02 return is due and the output tax liability must be computed
- CP204 instalment filing (monthly or bimonthly) requires an updated estimate of current-year tax
- Year-end Form C corporate income tax return requires P&L reconciliation
- A new tax filing due date needs adding to the compliance calendar
- The company is approaching a penalty risk from a missed or underpaid instalment

Don't use for: MFRS 15 revenue recognition — see [mfrs15-revenue-recognition](../mfrs15-revenue-recognition/SKILL.md); SST treatment on reimbursed expenses — see [expense-claim-audit](../expense-claim-audit/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_profit_loss`, `acct_list_sales_invoices`, `acct_list_purchase_bills` (existing `acct_*` contract tools)
- gbrain `finance` source (tax compliance calendar at `finance/tax/compliance-calendar.json`, CP204 estimates at `finance/tax/cp204/`)

## Workflows

### SST-02 Return Preparation

1. Determine the taxable period (bimonthly: Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec) and the SST-02 due date (last day of the month following the taxable period) — done when: period and due date are confirmed.
2. Pull taxable supplies for the period via `acct_list_sales_invoices(date_from=period_start, date_to=period_end)` and identify SST-applicable revenue lines — done when: output tax (service tax at 6%, or applicable rate) is computed on taxable supplies.
3. Pull claimable input tax (if any — for manufacturers registered for Sales Tax) from `acct_list_purchase_bills` — done when: eligible input tax is confirmed (note: Service Tax has no input tax mechanism).
4. Compute net SST payable and flag the remittance due date — done when: the SST-02 return summary is produced and recorded in `finance/tax/compliance-calendar.json`.

### CP204 Corporate Tax Estimate Filing

1. Pull current-year YTD P&L via `acct_get_profit_loss(date_from=year_start, date_to=today)` — done when: estimated taxable income for the year is computed.
2. Apply the corporate tax rate (current statutory rate per LHDN — 24% for Sdn Bhd above the SME threshold; 17% for the first RM 600,000 of chargeable income for qualifying SMEs) to estimate annual tax — done when: the CP204 estimate is computed.
3. Check whether the estimate exceeds the prior-year actual tax by more than 30%; if so, flag the risk of a CP204C revision being required — done when: variance from prior year is computed and flagged if >30%.
4. Record the CP204 instalment amount and due date in `finance/tax/cp204/` — done when: the instalment schedule is updated.

### Form C Annual Tax Compliance

1. Pull the full-year P&L and adjust for non-deductible items (entertainment disallowance, motor vehicle disallowance, etc.) per the LHDN tax adjustment schedule — done when: adjusted chargeable income is computed.
2. Compute Form C tax payable and reconcile against CP204 instalments paid — done when: tax balance payable or refund is determined.
3. Flag the Form C submission deadline (7 months after financial year end for e-Filing) — done when: the deadline is recorded in the compliance calendar.

## Common Pitfalls

1. **SST-02 return filing deadline** — SST-02 is due by the last day of the month following the taxable period. Late filing attracts a fine under the Sales Tax Act 2018 / Service Tax Act 2018.
2. **CP204 estimate accuracy** — if actual tax exceeds the CP204 estimate by more than 30%, LHDN imposes a 10% penalty on the shortfall under the Income Tax Act 1967. File a CP204C revision (by the 9th month of the financial year) if the estimate is likely to be materially wrong.
3. **Form C annual submission** — Form C must be e-Filed within 7 months of the financial year end. Failure to submit on time attracts a penalty under the Income Tax Act 1967.
4. **SST rate changes** — SST rates may be amended by Finance Act or ministerial order; verify the current rate from RMCD (Royal Malaysian Customs Department) before filing.
5. **Tax penalty prevention** — proactive CP204C revision and timely SST-02 filing are the primary penalty-prevention levers; monitor the compliance calendar at least 30 days before each filing due date.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/tax-sst-compliance/`
- [ ] `/tax-sst-compliance` loads on the `finance-manager` profile
- [ ] Happy-path SST-02 preparation produces a net SST payable figure with the correct due date
- [ ] CP204 instalment check correctly flags cases where the estimate exceeds prior-year tax by >30%
