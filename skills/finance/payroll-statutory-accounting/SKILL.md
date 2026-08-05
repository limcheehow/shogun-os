---
name: payroll-statutory-accounting
description: "Use when auditing monthly payroll disbursements and verifying statutory employee/employer contributions for EPF (KWSP), SOCSO (PERKESO), EIS (SIP), and PCB tax. Produces a payroll reconciliation and statutory contribution schedule."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, ops, payroll, malaysia, epf, kwsp, socso, perkeso, eis, pcb, statutory]
    category: finance
    related_skills: [malaysia-contractor-cp58-wht, expense-claim-audit]
---

# Payroll & Statutory Deductions Accounting

## Overview

Audits monthly payroll disbursements and verifies statutory employee/employer contributions for EPF (KWSP), SOCSO (PERKESO), EIS (SIP), and PCB tax. The skill produces a monthly payroll reconciliation journal and a statutory contribution schedule ready for remittance to KWSP, PERKESO/EIS, and LHDN, using existing `acct_*` contract tools against payroll data in the gbrain finance source — no new payroll-system integration is implied.

## When to Use

- Month-end payroll has been processed and statutory contribution amounts must be verified before remittance
- A new employee is onboarded and their contribution bands (EPF, SOCSO, EIS, PCB) must be configured
- Year-end EA Form preparation requires reconciliation of PCB deducted vs. remitted
- An audit queries whether statutory deductions match contribution statements from KWSP or PERKESO

Don't use for: contractor/agent WHT tracking — see [malaysia-contractor-cp58-wht](../malaysia-contractor-cp58-wht/SKILL.md); expense reimbursement audit — see [expense-claim-audit](../expense-claim-audit/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_purchase_bills`, `acct_get_profit_loss` (existing `acct_*` contract tools)
- gbrain `finance` source (payroll register at `finance/payroll/`, contribution schedules at `finance/statutory/`)

## Workflows

### Monthly Payroll Audit & Reconciliation

1. Load the monthly payroll register from `finance/payroll/` in the gbrain finance source — done when: every employee record has gross salary, allowances, and deductions listed.
2. Verify EPF (KWSP) contributions: employee 11% (or 9% optional), employer 13% (or as per current gazette rates for the applicable salary band) — done when: computed EPF matches the payroll register deduction line.
3. Verify SOCSO (PERKESO) contributions: employer and employee rates per the contribution table applicable to the employee's monthly wages (capped per the SOCSO schedule) — done when: SOCSO computed amounts match the register.
4. Verify EIS (SIP) contributions: employer and employee rates per the EIS contribution table (capped per the current schedule) — done when: EIS computed amounts match.
5. Verify PCB (Potongan Cukai Berjadual) deduction using the LHDN PCB schedule or `e-PCB` calculation for the employee's YTD income and relief elections — done when: PCB computed amount matches the register.
6. Post the payroll journal (gross wages Dr, EPF payable Cr, SOCSO payable Cr, EIS payable Cr, PCB payable Cr, net salary payable Cr) via `acct_create_purchase_bill` or equivalent GL entry — done when: trial balance reflects payroll for the period.

### Statutory Remittance Schedule

1. Aggregate EPF, SOCSO, EIS, and PCB totals from the payroll audit — done when: contribution amounts per statutory body are summed.
2. Record remittance due dates: EPF and SOCSO/EIS are due by the 15th of the following month; PCB is due by the 15th of the following month — done when: calendar entries are added to the gbrain finance source at `finance/statutory/remittance-calendar.json`.

## Common Pitfalls

1. **EPF (KWSP) rate bands** — contribution rates vary by employee age and salary band; using a flat rate without checking the current KWSP contribution table leads to underpayment.
2. **SOCSO (PERKESO) wage ceiling** — SOCSO contributions are capped at RM 5,000 gross monthly wage (current schedule); contributions on wages above the ceiling are not required.
3. **EIS (SIP) wage ceiling** — EIS contributions are similarly capped; confirm the current ceiling under the Employment Insurance System Act 2017.
4. **PCB vs. actual tax** — PCB is a monthly withholding estimate; the employee's actual annual tax liability (Form BE/B) may differ; EA Forms must reconcile PCB deducted vs. tax assessed.
5. **Late remittance penalties** — KWSP, PERKESO, and LHDN each impose penalties and compounding interest on late statutory remittances; monitor due dates strictly.
6. **Foreign employee exemptions** — foreign employees on employment passes may be exempt from SOCSO/EIS; verify work-pass type before applying contribution schedules.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/payroll-statutory-accounting/`
- [ ] `/payroll-statutory-accounting` loads on the `finance-manager` profile
- [ ] Happy-path monthly payroll audit completed with correct EPF / SOCSO / EIS / PCB amounts
- [ ] Remittance calendar updated with due dates for the audited month
