---
name: treasury-fx-facility-mgmt
description: "Use when monitoring foreign exchange (FX) exposure, Bank Negara Malaysia (BNM) FEA regulations, Debt Service Coverage Ratio (DSCR), or bank credit line terms. Produces an FX exposure report, DSCR computation, and credit facility utilisation summary."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, treasury, fx, bnm, fea, dscr, credit-facility, malaysia, hedging]
    category: finance
    related_skills: [cash-runway-forecasting, financial-statement-prep, internal-control-governance]
---

# Treasury, FX & Credit Facility Management

## Overview

Monitors foreign exchange (FX) exposure, Bank Negara Malaysia (BNM) FEA regulations, Debt Service Coverage Ratio (DSCR), and bank credit line terms. The skill produces an FX exposure report, a DSCR computation, and a credit facility utilisation summary — using existing `acct_*` contract tools for balance sheet and P&L data and the gbrain finance source for facility agreements and FX position records.

## When to Use

- Monthly treasury review requires an FX exposure report and DSCR calculation
- A new bank credit facility or loan drawdown needs to be recorded and tracked
- The company has foreign-currency receivables or payables that need FX hedging assessment
- BNM FEA approval is required before making a large offshore payment or investment
- A loan covenant (e.g., minimum DSCR) must be checked before a quarterly compliance report to the bank

Don't use for: cash runway forecasting — see [cash-runway-forecasting](../cash-runway-forecasting/SKILL.md); statutory financial statements — see [financial-statement-prep](../financial-statement-prep/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_balance_sheet`, `acct_get_profit_loss`, `acct_list_sales_invoices`, `acct_list_purchase_bills` (existing `acct_*` contract tools)
- gbrain `finance` source (FX position register at `finance/treasury/fx-positions.json`, facility agreements at `finance/treasury/facilities/`)

## Workflows

### FX Exposure Report

1. Pull all foreign-currency denominated AR via `acct_list_sales_invoices` and AP via `acct_list_purchase_bills` — done when: every open foreign-currency invoice is listed with currency, amount, and MYR equivalent at the invoice date rate.
2. Load bank balances by currency from `acct_get_balance_sheet(as_of_date=today)` — done when: foreign-currency cash balances are known.
3. Net the FX exposure: `net_exposure_per_currency = FCY_AR + FCY_cash − FCY_AP` — done when: net long (+) or short (−) exposure per currency is computed in MYR equivalent.
4. Flag exposures exceeding the company's approved hedging threshold (loaded from `finance/treasury/fx-positions.json`) — done when: exposures above threshold are marked for hedging review.
5. Assess BNM FEA compliance: transactions involving offshore investments, large foreign currency payments, or capital account transactions may require BNM approval under the Financial Services Act 2013 and FEA (Foreign Exchange Administration) rules — done when: flagged transactions are identified for BNM approval verification.

### DSCR Calculation

1. Pull EBITDA for the trailing 12 months via `acct_get_profit_loss` — done when: EBITDA (net profit + interest + tax + D&A) is computed.
2. Load total debt service (principal + interest payments due in the period) from `finance/treasury/facilities/` in the gbrain finance source — done when: the debt service figure is confirmed.
3. Compute DSCR: `DSCR = EBITDA / total_debt_service` — done when: the DSCR is computed and compared against the loan covenant minimum (typically ≥1.25x or as specified in the facility agreement).
4. Flag breach risk if DSCR is below or approaching the covenant minimum — done when: the covenant status (compliant / at-risk / breached) is returned with the headroom percentage.

### Credit Facility Utilisation

1. Load all bank facility agreements from `finance/treasury/facilities/` — done when: each facility is listed with limit, drawn amount, and expiry date.
2. Compute utilisation: `utilisation_pct = drawn_amount / facility_limit × 100` — done when: every facility has a utilisation percentage and remaining headroom.
3. Flag facilities expiring within 90 days for renewal action — done when: expiry alerts are recorded in the gbrain finance source.

## Common Pitfalls

1. **BNM FEA regulations** — Bank Negara Malaysia's Foreign Exchange Administration rules govern cross-border capital flows. Large offshore investments, loans to non-residents, and certain foreign currency payments require prior BNM approval under the Financial Services Act 2013. Failure to obtain approval constitutes a regulatory breach.
2. **DSCR covenant breach** — if DSCR falls below the covenant minimum specified in the facility agreement, the bank may call the loan or restrict further drawdowns. Monitor DSCR monthly and proactively engage the bank if headroom is below 15%.
3. **FX translation vs. transaction exposure** — translation exposure (balance sheet revaluation of foreign-currency assets/liabilities) is an accounting matter; transaction exposure (open FX commitments) requires cash hedging or forward cover. Distinguish between the two when reporting.
4. **Facility expiry oversight** — a lapsed credit facility that is inadvertently drawn against creates an uncommitted borrowing; flag facilities expiring within 90 days for renewal action.
5. **Hedging instrument eligibility** — BNM FEA rules restrict certain FX hedging instruments for non-bank entities; confirm the instrument type is eligible before advising on an FX hedge.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/treasury-fx-facility-mgmt/`
- [ ] `/treasury-fx-facility-mgmt` loads on the `finance-manager` profile
- [ ] Happy-path FX exposure report produces a net exposure per currency with flagged items above the hedging threshold
- [ ] DSCR calculation produces a DSCR figure and correctly flags breach risk against the covenant minimum
