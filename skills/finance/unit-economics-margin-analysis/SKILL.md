---
name: unit-economics-margin-analysis
description: "Use when calculating Gross Margin %, Net Margin %, EBITDA, Customer Acquisition Cost (CAC), or Client Profitability. Produces a unit-economics summary and margin breakdown by revenue line."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, fpna, margin, ebitda, cac, unit-economics, profitability, gross-margin]
    category: finance
    related_skills: [revenue-concentration-audit, bva-variance-analysis, cfo-executive-reporting]
---

# Margin & Unit Economics Optimization

## Overview

Calculates Gross Margin %, Net Margin %, EBITDA, Customer Acquisition Cost (CAC), and Client Profitability. The skill produces a unit-economics summary and a margin breakdown by revenue line (e.g., SaaS subscriptions vs. professional services), using existing `acct_*` contract tools for income and expense data — no new BI or data-warehouse integration is implied.

## When to Use

- Monthly or quarterly finance review requires a full margin breakdown by revenue stream
- A new product line or client segment needs a profitability assessment
- Board materials require EBITDA and net margin KPIs
- CAC has changed and its relationship to LTV needs evaluating

Don't use for: customer concentration risk — see [revenue-concentration-audit](../revenue-concentration-audit/SKILL.md); BvA tracking — see [bva-variance-analysis](../bva-variance-analysis/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_profit_loss`, `acct_list_sales_invoices`, `acct_list_contacts` (existing `acct_*` contract tools)
- gbrain `finance` source (marketing spend and CAC assumptions at `finance/unit-economics/`)

## Workflows

### Gross & Net Margin Calculation

1. Pull the P&L for the period via `acct_get_profit_loss(date_from=period_start, date_to=period_end)` — done when: Revenue, COGS, Gross Profit, OPEX, and Net Profit are available.
2. Compute Gross Margin %: `gross_margin_pct = (revenue − cogs) / revenue × 100` — done when: the gross margin percentage is calculated for each revenue line.
3. Compute Net Margin %: `net_margin_pct = net_profit / revenue × 100` — done when: the overall net margin is computed.
4. Compute EBITDA: `EBITDA = net_profit + interest + tax + depreciation + amortisation` (depreciation and amortisation sourced from the `general-ledger-journal-prep` depreciation schedule in the gbrain finance source) — done when: EBITDA is computed.

### CAC Calculation

1. Load total sales and marketing spend for the period from the P&L OPEX lines — done when: the combined S&M spend figure is known.
2. Load the number of new customers acquired in the period via `acct_list_contacts` (filtered by creation date) — done when: new customer count is known.
3. Compute CAC: `cac = total_sm_spend / new_customers_acquired` — done when: a per-customer acquisition cost is returned.

### Client Profitability Analysis

1. Pull all sales invoices for the period via `acct_list_sales_invoices(date_from=period_start, date_to=period_end)` — done when: revenue per client is known.
2. Allocate COGS and attributable OPEX to each client from the gbrain finance source at `finance/unit-economics/` — done when: each client has a revenue, cost, and gross profit figure.
3. Rank clients by gross profit descending and flag clients with a negative or <10% gross margin — done when: the ranked profitability table is produced.

## Common Pitfalls

1. **COGS vs. OPEX boundary** — direct delivery costs (hosting per-customer, dedicated support) belong in COGS, not OPEX; misclassification inflates gross margin and understates cost of delivery.
2. **Depreciation sourcing for EBITDA** — EBITDA requires adding back depreciation; confirm the depreciation schedule with the `general-ledger-journal-prep` skill to avoid double-counting.
3. **CAC period lag** — marketing spend in Month 1 may generate customers in Month 2-3; use a trailing 3-month blended CAC rather than a single-month ratio for a more accurate figure.
4. **LTV/CAC ratio** — the skill computes CAC but not LTV; the LTV assumption (average contract value × average retention months) must be provided by the stakeholder, not inferred from the `acct_*` tools.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/unit-economics-margin-analysis/`
- [ ] `/unit-economics-margin-analysis` loads on the `finance-manager` profile
- [ ] Happy-path margin calculation produces Gross Margin %, Net Margin %, and EBITDA for a test period
- [ ] CAC calculation produces a per-customer acquisition cost with the S&M spend and new customer count shown
