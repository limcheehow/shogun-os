---
name: expense-claim-audit
description: "Use when auditing staff expense reimbursement claims for receipt validity, corporate travel policy limits, and SST compliance before payout. Produces an approved/rejected claims list with compliance flags."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, ops, expense, audit, sst, malaysia, reimbursement, travel-policy]
    category: finance
    related_skills: [payroll-statutory-accounting, ap-vendor-management]
---

# Employee Expense Claim Audit & Processing

## Overview

Audits staff expense reimbursement claims for receipt validity, corporate travel policy limits, and SST compliance before payout. The skill produces an approved/rejected claims list with compliance flags, ensuring every reimbursement is supported by a valid receipt, within policy limits, and SST-treated correctly before the payment run — using existing `acct_*` contract tools and the gbrain finance source for policy documents.

## When to Use

- An employee submits an expense reimbursement claim and it requires audit before the payment cycle
- Month-end expense run requires batch review of all pending claims for the period
- An expense claim includes entertainment, meals, or travel that may carry SST implications
- Policy limit exceptions require a manager override and documented approval

Don't use for: supplier invoice processing — see [ap-vendor-management](../ap-vendor-management/SKILL.md); payroll statutory deductions — see [payroll-statutory-accounting](../payroll-statutory-accounting/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_create_purchase_bill`, `acct_list_purchase_bills` (existing `acct_*` contract tools)
- gbrain `finance` source (expense policy at `finance/policies/expense-policy.md`, claim register at `finance/expense-claims/`)

## Workflows

### Expense Claim Batch Audit

1. Load the pending expense claims from `finance/expense-claims/` in the gbrain finance source — done when: all claims for the period are listed with claimant, category, amount, receipt reference, and submission date.
2. Validate receipt completeness: each claim must have a receipt with supplier name, date, and amount matching the claim — done when: every claim is marked valid-receipt or missing-receipt.
3. Check each claim against the corporate travel policy limits loaded from `finance/policies/expense-policy.md` (e.g., daily meal allowance, hotel cap, flight class) — done when: every claim is marked within-policy or over-limit with the excess amount flagged.
4. Apply SST compliance check: reimbursed expenses with SST charged must be assessed — SST on entertainment, hotel stays, and certain professional services is generally not reclaimable as an input tax credit for non-GST-registered businesses; flag accordingly — done when: each claim has an SST-status (SST-inclusive / SST-exempt / SST-flag-for-review).
5. Produce the final approved/rejected list with compliance flags — done when: every claim has a disposition (approved / rejected / pending-override) and a reason.

### Policy Exception Approval

1. Route over-limit or missing-receipt claims to the claimant's line manager via the gbrain finance source — done when: the exception record is written to `finance/expense-claims/exceptions/` with a required-by date.
2. On manager approval, post the approved amount via `acct_create_purchase_bill` — done when: the reimbursement bill is posted in QuickBooks with the correct GL code and cost centre.

## Common Pitfalls

1. **SST compliance for reimbursed expenses** — under the Sales and Services Tax Act 2018, SST is a single-stage tax; businesses that are SST-registered may not be entitled to claim back SST on most expense categories as an input credit. Reimbursed entertainment and meals carry SST at 6% (service tax) but do not reduce the company's SST output tax liability. Flag these for tax review rather than auto-approving.
2. **Receipt date vs. claim date mismatch** — a receipt dated outside the claim period suggests a late submission or period cutoff issue; flag for the claimant to confirm.
3. **Personal vs. business mileage** — mileage claims require a trip log (origin, destination, purpose); claims without logs should be rejected or sent back for supporting documentation.
4. **Foreign currency claims** — expense receipts in foreign currency must be converted at the rate on the receipt date (e.g., BNM indicative rate or bank debit rate); do not use the claim-submission-date rate.
5. **Consecutive entertainment claims** — repeated entertainment claims for the same client within a short window (e.g., weekly) may be a policy-abuse pattern; flag for manager review.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/expense-claim-audit/`
- [ ] `/expense-claim-audit` loads on the `finance-manager` profile
- [ ] Happy-path batch audit completed: at least one approved, one rejected (missing receipt), and one SST-flagged claim processed
- [ ] Approved claims are posted as purchase bills in QuickBooks with correct GL codes
