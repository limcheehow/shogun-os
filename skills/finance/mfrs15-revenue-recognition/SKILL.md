---
name: mfrs15-revenue-recognition
description: "Use when validating compliance with MFRS 15 5-Step model, Standalone Selling Price (SSP) allocation in MYR, deferred revenue amortization, or SST exclusion from transaction price. Produces a revenue recognition schedule and compliance flag per contract."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, tax, malaysia, mfrs15, revenue-recognition, ssp, deferred-revenue, sst, ifrs15]
    category: finance
    related_skills: [financial-statement-prep, tax-sst-compliance, general-ledger-journal-prep]
---

# MFRS 15 / IFRS 15 Revenue Recognition Assurance

## Overview

Validates compliance with MFRS 15 5-Step model, Standalone Selling Price (SSP) allocation in MYR, deferred revenue amortization, and SST exclusion from the transaction price. The skill produces a revenue recognition schedule per contract and a compliance flag for each obligation, using existing `acct_*` contract tools for invoice and contact data — no new contract-management integration is implied.

## When to Use

- A new multi-element customer contract requires revenue allocation across performance obligations
- Deferred revenue on the balance sheet needs amortization scheduling and periodic release
- Audit or internal review queries whether SST has been excluded from the MFRS 15 transaction price
- Year-end statutory financial statements require an MFRS 15 disclosure note

Don't use for: SST return filing — see [tax-sst-compliance](../tax-sst-compliance/SKILL.md); P&L and balance sheet preparation — see [financial-statement-prep](../financial-statement-prep/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_sales_invoices`, `acct_list_contacts`, `acct_get_profit_loss` (existing `acct_*` contract tools)
- gbrain `finance` source (contract register at `finance/contracts/`, SSP schedule at `finance/ssp-schedule.json`)

## Workflows

### MFRS 15 5-Step Assessment per Contract

The 5-Step model per MFRS 15 (equivalent to IFRS 15):

1. **Step 1 — Identify the contract**: Confirm a written or substantive agreement exists with a customer with enforceable rights and obligations — done when: the contract reference is confirmed in `finance/contracts/`.
2. **Step 2 — Identify performance obligations**: List all distinct goods or services promised in the contract (e.g., SaaS subscription, implementation services, training) — done when: each obligation is named and assessed for distinctness.
3. **Step 3 — Determine transaction price**: Pull the invoice total via `acct_list_sales_invoices` and exclude SST from the transaction price (SST is a pass-through tax, not revenue under MFRS 15) — done when: transaction price (ex-SST) is confirmed in MYR.
4. **Step 4 — Allocate to performance obligations at SSP**: Load the SSP schedule from `finance/ssp-schedule.json` and allocate the transaction price to each obligation proportionally at its SSP in MYR — done when: each obligation has an allocated transaction price.
5. **Step 5 — Recognise revenue when/as obligation is satisfied**: Determine whether the obligation is satisfied at a point in time (e.g., delivery) or over time (e.g., SaaS subscription) and compute the recognition schedule — done when: a monthly revenue recognition schedule is produced for over-time obligations.

### Deferred Revenue Amortization

1. Load the deferred revenue balance from the balance sheet via `acct_get_profit_loss` or `acct_get_balance_sheet` — done when: the opening deferred revenue balance is known.
2. Apply the recognition schedule from Step 5 above to release deferred revenue to income in the period — done when: the journal entries (Dr Deferred Revenue, Cr Revenue) are computed for the period.
3. Record the release via the `general-ledger-journal-prep` skill's journal entry workflow — done when: the GL is updated and deferred revenue closing balance is confirmed.

## Common Pitfalls

1. **SST exclusion from transaction price** — under MFRS 15, the transaction price is the amount to which the entity expects to be entitled in exchange for goods/services. SST collected on behalf of the government is excluded. Failure to exclude SST overstates recognised revenue.
2. **SSP in MYR** — for multi-element arrangements, SSP must be in the functional currency (MYR for Malaysian entities); using USD-denominated SSP without translation introduces an accounting error.
3. **MFRS 15 5-Step model compliance** — MFRS 15 is converged with IFRS 15 and effective for annual periods beginning on or after 1 January 2018 for Malaysian companies adopting MFRS. MPERS entities follow a simplified revenue standard.
4. **Bundled discounts** — if the contract is sold at a discount, the discount must be allocated proportionally to all performance obligations at their SSP, not assigned entirely to the lowest-priced obligation.
5. **Variable consideration constraint** — if any element of the transaction price is variable (milestone payments, usage-based fees), apply the MFRS 15 constraint test before including variable amounts in the recognised revenue.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/mfrs15-revenue-recognition/`
- [ ] `/mfrs15-revenue-recognition` loads on the `finance-manager` profile
- [ ] Happy-path 5-Step assessment completed for a test multi-element contract with SSP allocation in MYR
- [ ] Deferred revenue amortization schedule produces correct monthly release amounts with SST excluded from the transaction price
