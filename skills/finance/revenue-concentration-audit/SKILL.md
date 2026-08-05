---
name: revenue-concentration-audit
description: "Use when auditing revenue breakdown by client and flagging concentration risks (>20% total revenue from a single customer). Produces a client revenue concentration table with risk flags."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, concentration, revenue, risk, client, audit]
    category: finance
    related_skills: [unit-economics-margin-analysis, cfo-executive-reporting, ar-credit-control]
---

# Customer Concentration Risk Audit

## Overview

Audits revenue breakdown by client and flags concentration risks (>20% total revenue from a single customer). The skill produces a client revenue concentration table ranked by revenue share, with a ">20% concentration risk" flag for any single customer exceeding that threshold — using existing `acct_list_contacts` and `acct_list_sales_invoices` contract tools. No new CRM or BI integration is implied.

## When to Use

- Monthly or quarterly finance review requires a customer concentration risk assessment
- Board materials require a concentration risk disclosure for governance purposes
- A new large contract would push a single customer over the 20% threshold
- The `monthly-board-report` skill needs the concentration risk section

Don't use for: margin analysis by client — see [unit-economics-margin-analysis](../unit-economics-margin-analysis/SKILL.md); AR collections — see [ar-credit-control](../ar-credit-control/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_contacts`, `acct_list_sales_invoices` (existing `acct_*` contract tools)
- gbrain `finance` source (concentration audit history at `finance/concentration-audit/`)

## Workflows

### Monthly Concentration Audit

1. Pull all sales invoices for the period via `acct_list_sales_invoices(date_from=period_start, date_to=period_end)` — done when: revenue per invoice is available with the customer reference.
2. Call `acct_list_contacts` to resolve customer names from contact IDs — done when: every invoice is annotated with the customer name.
3. Aggregate revenue by customer and compute total period revenue — done when: each customer has a total revenue and a revenue share percentage (`customer_revenue / total_revenue × 100`).
4. Rank customers by revenue share descending — done when: the table is sorted from highest to lowest concentration.
5. Flag any customer whose revenue share exceeds 20% with a "⚠️ >20% Concentration Risk" marker — done when: the flagged list is non-empty or explicitly empty (no single customer >20%).
6. Save the concentration table to `finance/concentration-audit/<YYYY-MM>.json` in the gbrain finance source — done when: the audit record is written for the period.

## Common Pitfalls

1. **>20% concentration risk threshold** — the spec defines 20% as the single-customer concentration risk threshold; flagging at this level is a standard corporate governance and investor-reporting convention. Do not raise the threshold without board approval.
2. **Consolidated entity grouping** — if a single ultimate parent has multiple subsidiary customers, their revenues must be aggregated before the concentration check; separate entity treatment understates the true concentration.
3. **Period selection bias** — a short reporting period (e.g., a single month with a lumpy payment) can spike one customer above 20%; use a trailing 12-month revenue total for structural risk assessment alongside the MTD figure.
4. **Confidentiality in board materials** — client names in concentration tables may be commercially sensitive; confirm whether customer A/B/C anonymisation is required before distributing board reports.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/revenue-concentration-audit/`
- [ ] `/revenue-concentration-audit` loads on the `finance-manager` profile
- [ ] Happy-path audit produces a ranked concentration table with at least one customer shown
- [ ] Customers exceeding the 20% threshold are correctly flagged with a "⚠️ >20% Concentration Risk" marker
