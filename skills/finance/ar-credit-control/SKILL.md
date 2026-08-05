---
name: ar-credit-control
description: "Use when managing customer billing, payment collections, aging buckets, credit limits, or automated dunning follow-ups. Produces an AR aging summary, dunning queue, and collections action list."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, ops, ar, collections, dunning, aging, credit]
    category: finance
    related_skills: [ap-vendor-management, bank-payment-reconciliation]
---

# Accounts Receivable & Credit Management

## Overview

Manages customer billing, payment collections, aging buckets (0-30, 31-60, 61-90, 90+ days), credit limits, and automated dunning follow-ups. The skill produces an AR aging summary with a prioritised dunning queue and a collections action list, derived from existing `acct_*` contract tools against the QuickBooks data source — no new integration is implied.

## When to Use

- Customer invoice is unpaid and falls into an aging bucket (>30 days overdue)
- Week-end AR sweep to identify overdue invoices requiring follow-up
- Credit limit review before approving a new or expanded customer order
- Monthly dunning batch to auto-generate follow-up messages per aging tier

Don't use for: supplier invoice processing — see [ap-vendor-management](../ap-vendor-management/SKILL.md); bank/gateway settlement — see [bank-payment-reconciliation](../bank-payment-reconciliation/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_sales_invoices`, `acct_get_aging_report`, `acct_list_contacts` (existing `acct_*` contract tools)
- gbrain `finance` source (for credit-limit policy and dunning templates)

## Workflows

### AR Aging Sweep

1. Call `acct_get_aging_report(type="receivable")` — done when: aging buckets (0-30, 31-60, 61-90, 90+) are populated with amounts and invoice counts.
2. Cross-reference bucket totals against credit limits stored in `finance/credit-limits.json` in the gbrain finance source — done when: each overdue customer record is annotated with their approved credit limit.
3. Produce the dunning queue sorted by days overdue descending — done when: every overdue invoice has a dunning tier (Reminder / Escalation / Legal) assigned.
4. Generate follow-up messages per tier using dunning templates from the gbrain finance source — done when: each queued invoice has a draft message ready to send.

### Credit Limit Review

1. Call `acct_list_contacts` to retrieve customer profiles — done when: all active customers are listed.
2. Pull the last-12-months sales history via `acct_list_sales_invoices(date_from=12_months_ago)` — done when: lifetime revenue and payment velocity per customer are computed.
3. Compare proposed credit limit against payment history and aging risk — done when: a recommendation (approve / reduce / put on hold) is returned with rationale.

## Common Pitfalls

1. **Aging bucket drift** — "Invoice date" vs. "due date" aging produces very different buckets; always use the contractual due date as day-0.
2. **Partial-payment residuals** — a partially paid invoice still lives in the aging bucket; flag the outstanding balance, not the original invoice amount.
3. **Disputed invoice exclusions** — include a formal dispute flag; dunning a disputed invoice escalates rather than resolves collections issues.
4. **Credit-limit enforcement gap** — the AR skill surfaces the limit; the order-entry system must enforce it. Document the handoff clearly.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/ar-credit-control/`
- [ ] `/ar-credit-control` loads on the `finance-manager` profile
- [ ] Happy-path AR aging sweep completed once with real or test data
- [ ] Dunning queue partitions correctly into Reminder / Escalation / Legal tiers
