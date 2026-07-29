---
name: financial-statement-prep
description: "Use when preparing statutory Profit & Loss, Balance Sheet, Statement of Cash Flows, and Statement of Changes in Equity compliant with MFRS / MPERS."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, close, mfrs, mpers, financial-statements, malaysia]
    category: finance
    related_skills: []
---

# MFRS / MPERS Financial Statement Preparation

## Overview

Prepares statutory Profit & Loss (P&L), Balance Sheet, Statement of Cash Flows, and Statement of Changes in Equity compliant with MFRS / MPERS. The skill produces the four primary statements formatted from the existing `acct_*` P&L and balance-sheet surfaces — no new consolidation engine is introduced; presentation compliance with MFRS / MPERS is the skill's deliverable.

## When to Use

- Statutory period-end requires the primary financial statements
- Cash flow statement must be derived from P&L and balance-sheet movements
- Statements must be presented per MFRS / MPERS disclosure requirements

Don't use for: trial balance verification / period lock — see [period-end-close-checklist](../period-end-close-checklist/SKILL.md); revenue recognition assurance — see [mfrs15-revenue-recognition](../mfrs15-revenue-recognition/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_profit_loss`, `acct_get_balance_sheet` (existing `acct_*` contract tools)
- gbrain `finance` source (for statement archive, e.g. `finance/statements/`)

## Workflows

### Prepare Primary Statements

1. Pull P&L via `acct_get_profit_loss(date_from=period_start, date_to=period_end)` — done when: revenue, COGS, gross profit, OPEX, and net profit are enumerated.
2. Pull balance sheet via `acct_get_balance_sheet(as_of_date=period_end)` — done when: assets, liabilities, and equity accounts are enumerated.
3. Derive the Statement of Cash Flows from the movement in balance-sheet accounts plus P&L non-cash items — done when: operating, investing, and financing cash flows reconcile to the net cash movement.
4. Derive the Statement of Changes in Equity from equity account movements and comprehensive income — done when: opening + total comprehensive income − distributions = closing equity.
5. Archive the statements to `finance/statements/` in the gbrain finance source — done when: the four statements are saved.

## Common Pitfalls

1. **MFRS / MPERS presentation drift** — presenting statements in a non-compliant layout (e.g. wrong line ordering, missing disclosures) fails compliance; align line items to the MFRS / MPERS model.
2. **Cash-flow reconciliation gap** — a cash flow statement that does not tie to the net cash movement signals an error in working-capital movements; reconcile before sign-off.
3. **Equity movement omission** — skipping comprehensive income or distributions in the changes statement leaves the closing equity unexplained.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/financial-statement-prep/`
- [ ] `/financial-statement-prep` loads on that profile
- [ ] Happy-path statement preparation completed once
- [ ] All four statements reconcile internally and to the source GL
