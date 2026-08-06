---
name: malaysia-contractor-cp58-wht
description: "Use when tracking payouts to local independent contractors/agents for LHDN Form CP58 (>RM 5,000 threshold), LHDN Self-Billed e-Invoicing, or Section 107A/109B Withholding Tax (WHT) for foreign vendors. Produces a CP58 register and WHT computation."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, ops, tax, malaysia, cp58, wht, lhdn, einvoice, contractor]
    category: finance
    related_skills: [payroll-statutory-accounting, ap-vendor-management]
---

# Malaysian Contractor & Agent Tax Compliance

## Overview

Tracks payouts to local independent contractors/agents for LHDN Form CP58 (>RM 5,000 threshold), LHDN Self-Billed e-Invoicing, and Section 107A/109B Withholding Tax (WHT) for foreign vendors. The skill produces an annual CP58 register for LHDN submission and a per-payment WHT computation schedule, using existing `acct_*` contract tools — no new tax-filing integration is implied.

## When to Use

- A payment to an independent contractor or agent in Malaysia exceeds RM 5,000 in the calendar year (LHDN CP58 threshold)
- A self-billed e-Invoice must be issued to a local contractor under the LHDN e-Invoicing mandate
- A payment is made to a foreign vendor and Section 107A (contract payments) or Section 109B (royalties/interest) WHT must be deducted and remitted to LHDN
- Year-end CP58 forms require compilation and distribution to each contractor

Don't use for: regular employee payroll tax — see [payroll-statutory-accounting](../payroll-statutory-accounting/SKILL.md); corporate SST filing — see [tax-sst-compliance](../tax-sst-compliance/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_purchase_bills`, `acct_list_contacts` (existing `acct_*` contract tools)
- gbrain `finance` source (for contractor master register at `finance/contractors/`)

## Workflows

### CP58 Annual Register Build

1. Pull all contractor payments for the calendar year via `acct_list_purchase_bills(date_from=year_start, date_to=year_end)` — done when: every contractor bill is listed with payee, IC/ROC number, and gross amount.
2. Aggregate payments per contractor and flag payees whose cumulative total exceeds RM 5,000 — done when: the CP58-eligible list is produced with total gross payments per contractor.
3. Cross-reference with the contractor master register in `finance/contractors/` in the gbrain finance source to confirm IC/ROC numbers and contact addresses — done when: all flagged records have valid NRIC/BRN for LHDN submission.
4. Generate the CP58 register in the LHDN-required format — done when: each record contains payee name, NRIC/BRN, payment dates, and total amount for the year.

### Self-Billed e-Invoice Issuance

1. Identify contractor payments where the contractor is not VAT/GST-registered and LHDN Self-Billed e-Invoicing applies — done when: eligibility is confirmed per LHDN Self-Billed e-Invoice guidelines.
2. Generate the e-Invoice fields (UBL format: supplier = company, buyer = contractor) and record in the gbrain finance source — done when: e-Invoice reference number is recorded against the payment.

### WHT Deduction (Section 107A / 109B)

1. Identify bills from foreign vendors subject to WHT — done when: vendor country-of-residence is confirmed as non-Malaysian and the payment type (contract / royalty / interest) is classified.
2. Compute WHT amount: Section 107A — 10% (labour) + 3% (materials) on contract payments; Section 109B — prescribed rate on royalties/interest per the applicable tax treaty — done when: WHT amount and net payment are computed.
3. Post the WHT liability in QuickBooks via `acct_create_purchase_bill` for the WHT payable account — done when: WHT liability is posted and the net payment equals gross minus WHT.
4. Flag the WHT remittance due date (on or before the last day of the following month) — done when: remittance date is recorded.

## Common Pitfalls

1. **CP58 >RM 5,000 threshold** — LHDN CP58 is triggered when the aggregate payments to a single contractor/agent exceed RM 5,000 in a calendar year; per-invoice amounts below RM 5,000 are still aggregated.
2. **LHDN Self-Billed e-Invoicing mandate** — failure to issue a self-billed e-Invoice for eligible contractor payments constitutes non-compliance under the LHDN e-Invoice phase rollout; confirm the current implementation date for the company's revenue tier.
3. **Section 107A / 109B WHT rates** — Section 107A splits WHT into 10% on labour and 3% on materials components; Section 109B rate depends on whether a Double Taxation Agreement (DTA) applies between Malaysia and the vendor's country.
4. **WHT remittance deadline** — WHT must be remitted to LHDN by the last day of the month following deduction; late remittance attracts a 10% penalty under the Income Tax Act 1967.
5. **Misclassification: employee vs. contractor** — LHDN may reclassify a contractor as an employee (PCB applies instead of WHT/CP58) if the engagement characteristics indicate an employment relationship.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/malaysia-contractor-cp58-wht/`
- [ ] `/malaysia-contractor-cp58-wht` loads on the `finance-manager` profile
- [ ] Happy-path CP58 register build completed with at least one contractor exceeding RM 5,000
- [ ] WHT computation produces correct gross / WHT / net split for a Section 107A test case
