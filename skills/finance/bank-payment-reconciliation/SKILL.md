---
name: bank-payment-reconciliation
description: "Use when reconciling daily bank feeds and payment gateway settlements (Stripe, FPX, Credit Cards) against QuickBooks general ledger records."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, close, reconciliation, bank, stripe, fpx, payments]
    category: finance
    related_skills: []
---

# Bank & Payment Gateway Settlement Reconciliation

## Overview

Reconciles daily bank feeds and payment gateway settlements (Stripe, FPX, Credit Cards) against QuickBooks general ledger records. The skill produces a reconciled differences list (matched, unmatched, exceptions) that closes the gap between gateway/bank inflows and the posted GL cash accounts using existing `acct_*` tools — no new payment gateway integration is implied.

## When to Use

- End-of-day gateway settlement (Stripe / FPX / card) must match posted GL cash
- Bank feed transactions need matching to AR receipts or AP disbursements
- Reconciling items need surfacing before period close

Don't use for: AR collections dunning — see [ar-credit-control](../ar-credit-control/SKILL.md); AP batching — see [ap-vendor-management](../ap-vendor-management/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_get_balance_sheet`, `acct_list_sales_invoices`, `acct_list_purchase_bills` (existing `acct_*` contract tools)
- gbrain `finance` source (for settlement truth, e.g. `finance/settlements/`)

## Workflows

### Reconcile Daily Settlements

1. Pull GL cash accounts via `acct_get_balance_sheet(as_of_date=today)` — done when: cash and bank account balances are listed.
2. Load the gateway settlement file (Stripe / FPX / card) from the `finance` gbrain source — done when: every settlement line is loaded with a net amount.
3. Match settlement lines to posted AR receipts / AP disbursements via `acct_list_sales_invoices` / `acct_list_purchase_bills` — done when: each line is matched or flagged as an exception.
4. Produce the differences list (matched, unmatched, exceptions) — done when: matched + unmatched + exceptions equals total settlement lines.

### Surface Reconciling Items

1. List unmatched items with a reason (timing difference, missing invoice, FX rounding) — done when: every unmatched item has a reason code.

## Common Pitfalls

1. **FX rounding gaps** — gateway FX and GL functional-currency rounding leaves small residuals; allocate a rounding account rather than forcing false matches.
2. **Refund netting** — netting refunds against gross inflows hides refund volume; reconcile gross inflows and gross refunds separately.
3. **Settlement delay mismatch** — T+2 gateway settlement vs same-day GL posting creates timing exceptions; clear them at period close.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/bank-payment-reconciliation/`
- [ ] `/bank-payment-reconciliation` loads on that profile
- [ ] Happy-path daily reconciliation completed once
- [ ] Differences list partitions cleanly into matched / unmatched / exceptions
