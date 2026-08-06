---
name: ap-vendor-management
description: "Use when handling supplier invoices, 3-way matching (PO + GRN + Invoice), payment batching, or vendor account reconciliation. Produces a payment batch and vendor reconciliation statement."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, ops, ap, vendor, matching, payments, reconciliation]
    category: finance
    related_skills: [ar-credit-control, bank-payment-reconciliation]
---

# Accounts Payable & Supplier Disbursements

## Overview

Handles supplier invoices, 3-way matching (PO + GRN + Invoice), payment batching, and vendor account reconciliation. The skill produces a matched payment batch ready for approval and a vendor reconciliation statement per period, using existing `acct_*` contract tools — no new procurement integration is implied.

## When to Use

- Supplier invoice received and needs matching to a purchase order and goods-receipt note
- Weekly or fortnightly AP payment run requires batching and approval routing
- Month-end vendor statement reconciliation to confirm balances match supplier records
- New vendor onboarding requires credit terms and bank detail setup in QuickBooks

Don't use for: customer invoice collections — see [ar-credit-control](../ar-credit-control/SKILL.md); bank/gateway settlement — see [bank-payment-reconciliation](../bank-payment-reconciliation/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_purchase_bills`, `acct_create_purchase_bill`, `acct_list_contacts`, `acct_get_aging_report` (existing `acct_*` contract tools)
- gbrain `finance` source (for PO register and GRN records at `finance/po-register/`)

## Workflows

### 3-Way Invoice Match

1. Load the supplier invoice and retrieve the matching PO from `finance/po-register/` in the gbrain finance source — done when: PO number, ordered quantity, and unit price are confirmed.
2. Confirm the goods-receipt note (GRN) in the gbrain finance source matches the invoice quantity — done when: received quantity equals or is explicitly short-received against invoiced quantity.
3. Compare invoice unit price and total against the PO — done when: price variance is zero or within the approved tolerance; flag exceptions for manual approval.
4. Call `acct_create_purchase_bill` to post the matched invoice in QuickBooks — done when: the bill is posted with correct GL code, cost centre, and payment terms.

### Payment Batch Run

1. Call `acct_get_aging_report(type="payable")` — done when: AP aging by supplier is populated with due dates.
2. Filter invoices due within the payment run window (configurable: 7 or 14 days) — done when: a payment batch list is produced with supplier name, bank details, and net amount.
3. Submit the payment batch for two-person approval — done when: an approver acknowledgement is logged in the gbrain finance source before funds are released.

### Vendor Account Reconciliation

1. Pull all bills for the period via `acct_list_purchase_bills(date_from=period_start, date_to=period_end)` — done when: all posted bills and credit notes are listed.
2. Compare against the supplier's statement — done when: matched, unmatched, and disputed items are identified and a reconciliation statement is produced.

## Common Pitfalls

1. **3-way match tolerance abuse** — price tolerance should be narrow (e.g., ≤1%); wide tolerances allow overbilling to pass silently.
2. **Duplicate invoice risk** — same invoice number from same supplier on same date must trigger a duplicate check before posting.
3. **Payment terms date calculation** — Net-30 from invoice date vs. receipt date differs; confirm which governs in the supplier contract.
4. **Segregation of duties** — the same person must not approve a bill and approve the payment; enforce 2-person sign-off in the payment batch step.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/ap-vendor-management/`
- [ ] `/ap-vendor-management` loads on the `finance-manager` profile
- [ ] Happy-path 3-way match completed once with a test invoice, PO, and GRN
- [ ] Payment batch produces an approval-ready list before any disbursement
