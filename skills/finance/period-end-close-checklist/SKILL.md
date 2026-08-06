---
name: period-end-close-checklist
description: "Use when executing trial balance verification, sub-ledger to GL balancing, period locking, and month-end close checklists."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, close, trial-balance, period-lock, checklist]
    category: finance
    related_skills: []
---

# Month-End & Year-End Close Orchestration

## Overview

Executes trial balance verification, sub-ledger to GL balancing, period locking, and month-end close checklists. The skill produces a signed-off close checklist that attests each control (TB balances, sub-ledgers tie, period locked) using existing `acct_*` tools — it orchestrates the close, it does not itself post journals.

## When to Use

- Month-end or year-end close requires a controlled checklist run
- Sub-ledgers (AR/AP) must tie to GL control accounts before lock
- Period must be locked against late postings

Don't use for: journal authoring — see [general-ledger-journal-prep](../general-ledger-journal-prep/SKILL.md); statutory statements — see [financial-statement-prep](../financial-statement-prep/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_balance_sheet`, `acct_get_profit_loss`, `acct_get_aging_report` (existing `acct_*` contract tools)
- gbrain `finance` source (for the signed close checklist, e.g. `finance/close/`)

## Workflows

### Run Close Checklist

1. Pull the trial balance via `acct_get_balance_sheet(as_of_date=period_end)` and `acct_get_profit_loss(date_from, date_to)` — done when: total debits == total credits and total assets == liabilities + equity.
2. Reconcile sub-ledger to GL: compare `acct_get_aging_report(type="receivable")` and `acct_get_aging_report(type="payable")` totals to the GL AR/AP control accounts — done when: each sub-ledger total equals its control account.
3. Run the period-end close checklist (accruals posted, bank rec done, depreciation booked) — done when: every checklist control is signed off.
4. Lock the period against late postings — done when: the period lock is recorded in `finance/close/`.

## Common Pitfalls

1. **Late postings after lock** — postings that slip into a locked period reopen the close; enforce a hard lock and route corrections to the next period.
2. **Sub-ledger drift** — AR/AP sub-ledger totals that diverge from control accounts mean the close is not clean; resolve before lock.
3. **Checklist sign-off without evidence** — a signed checklist with no attached evidence is un-auditable; save the TB and aging snapshots alongside the sign-off.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/period-end-close-checklist/`
- [ ] `/period-end-close-checklist` loads on that profile
- [ ] Happy-path close checklist completed once
- [ ] Trial balance balances and sub-ledgers tie to control accounts
