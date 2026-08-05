---
name: general-ledger-journal-prep
description: "Use when maintaining the double-entry general ledger, accruals, prepayments, fixed asset depreciation schedules, and intercompany transactions."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, close, gl, accruals, prepayments, depreciation, intercompany]
    category: finance
    related_skills: []
---

# General Ledger & Double-Entry Bookkeeping

## Overview

Maintains double-entry general ledger, accruals, prepayments, fixed asset depreciation schedules, and intercompany transactions. The skill produces journal entries and reconciling schedules that keep the GL complete and balanced across an accounting period — no new contract tools are introduced; it relies on the existing `acct_*` ledger surface and the `finance` gbrain source for schedule truth.

## When to Use

- Period-end requires accruals, prepayments, or depreciation journals booked to the GL
- Intercompany transactions need offsetting entries across entities
- New fixed assets are capitalized and require a depreciation schedule

Don't use for: bank statement reconciliation — see [bank-payment-reconciliation](../bank-payment-reconciliation/SKILL.md); trial balance verification / period locking — see [period-end-close-checklist](../period-end-close-checklist/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_balance_sheet`, `acct_get_profit_loss` (existing `acct_*` contract tools)
- gbrain `finance` source (for depreciation / accrual schedule truth, e.g. `finance/assets.json`)

## Workflows

### Book Accruals and Prepayments

1. Pull period P&L via `acct_get_profit_loss(date_from, date_to)` to identify accounts with unposted accruals or deferred income — done when: the relevant expense/revenue accounts are listed.
2. Compose offsetting double-entry journals (debit expense / credit accrued liability, or debit prepayment asset / credit cash) — done when: debits equal credits per journal.
3. Persist the journal set to the `finance` gbrain source for audit traceability — done when: the journals are saved under `finance/journals/`.

### Maintain Fixed Asset Depreciation Schedule

1. Load `finance/assets.json` from the gbrain finance source for cost, salvage, useful life, and method (straight-line) — done when: each asset's parameters are loaded.
2. Compute period depreciation = (cost − salvage) / useful life in periods — done when: every asset has a depreciation amount for the period.
3. Post the depreciation journal (debit depreciation expense / credit accumulated depreciation) — done when: the journal balances.

### Record Intercompany Transactions

1. Identify the offsetting entity and currency for each intercompany movement — done when: both legs of the entry are enumerated.
2. Book matching debit/credit journals in each entity's GL — done when: net intercompany balances eliminate to zero on consolidation.

## Common Pitfalls

1. **Unbalanced journals** — a debit/credit mismatch breaks the trial balance. Enforce debits == credits before persisting.
2. **Depreciation method drift** — switching methods without disclosure distorts period-on-period comparability. Cite the method in the schedule.
3. **Intercompany elimination gaps** — an unbalanced intercompany pair leaves consolidation residuals. Reconcile both legs each period.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/general-ledger-journal-prep/`
- [ ] `/general-ledger-journal-prep` loads on that profile
- [ ] Happy-path accrual + depreciation workflow completed once
- [ ] Journals balance (debits == credits) and are saved to `finance/journals/`
