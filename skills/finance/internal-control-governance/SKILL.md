---
name: internal-control-governance
description: "Use when testing internal controls aligned with MCCG (Malaysian Code on Corporate Governance) and Bursa Malaysia SRMIC guidelines. Produces an internal control test report and segregation-of-duties matrix."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, governance, mccg, bursa, srmic, internal-controls, sod, audit, malaysia]
    category: finance
    related_skills: [isa530-audit-pbc-support, tax-sst-compliance, period-end-close-checklist]
---

# Internal Controls & Segregation of Duties

## Overview

Tests internal controls aligned with MCCG (Malaysian Code on Corporate Governance) and Bursa Malaysia SRMIC guidelines. The skill produces an internal control test report and a Segregation of Duties (SoD) matrix, identifying control gaps and recommendations for remediation — using existing `acct_*` tools for transaction-level testing and the gbrain finance source for control documentation.

## When to Use

- Annual internal control review or board audit committee requires a control assurance report
- A new financial process (e.g., a new payment workflow) needs a SoD assessment before go-live
- Bursa Malaysia or an external auditor requests evidence of internal control testing
- A control failure (e.g., unauthorised payment approval) needs root-cause investigation

Don't use for: external audit sampling — see [isa530-audit-pbc-support](../isa530-audit-pbc-support/SKILL.md); tax compliance filing — see [tax-sst-compliance](../tax-sst-compliance/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_purchase_bills`, `acct_list_sales_invoices`, `acct_list_contacts` (existing `acct_*` contract tools)
- gbrain `finance` source (control register at `finance/governance/controls.json`, SoD matrix at `finance/governance/sod-matrix.json`)

## Workflows

### Internal Control Test

1. Load the control register from `finance/governance/controls.json` in the gbrain finance source — done when: all in-scope controls are listed with their owner, frequency, and test procedure.
2. For each control, execute the test procedure (e.g., sample payment approvals from `acct_list_purchase_bills`, verify dual-approval evidence, check amounts against approved-vendor list) — done when: each tested control is marked pass / fail / exception.
3. Produce the internal control test report with pass/fail per control, exception details, and recommended remediation — done when: every in-scope control has a test result and exceptions are documented.

### Segregation of Duties (SoD) Matrix

1. Load the SoD matrix from `finance/governance/sod-matrix.json` — done when: all finance roles and their system-access permissions are listed.
2. Identify conflicting access combinations (e.g., same person can create a vendor and approve a payment, or create an invoice and receive cash) — done when: all SoD conflicts are surfaced with role names and access rights.
3. Produce a conflict-resolution recommendation (compensating control or access removal) for each identified conflict — done when: every conflict has a recommended action with an owner and a target remediation date.

## Common Pitfalls

1. **MCCG (Malaysian Code on Corporate Governance)** — MCCG 2021 applies to public listed companies and large companies; private companies may choose to adopt it voluntarily. Key MCCG provisions relevant to finance internal controls include board-level audit committee oversight, risk management frameworks, and internal audit function independence.
2. **Bursa Malaysia SRMIC** — the Securities Commission and Bursa Malaysia publish the Statement on Risk Management and Internal Control (SRMIC) guidelines, which require listed companies to include a Directors' Statement on Risk Management and Internal Control in the annual report. Evidence of internal control testing supports this statement.
3. **SoD conflicts in small teams** — in small finance teams, SoD conflicts are common and may be unavoidable; implement compensating controls (e.g., MD review of all payments, independent bank reconciliation) and document them formally.
4. **Control test frequency** — controls must be tested at the frequency specified in the control register (some are daily, some quarterly); testing a quarterly control only annually does not constitute adequate assurance.
5. **Control design vs. operating effectiveness** — distinguish between a well-designed control (what it should do) and an operating-effective control (whether it actually did it); a well-designed but inconsistently applied control fails the test.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/internal-control-governance/`
- [ ] `/internal-control-governance` loads on the `finance-manager` profile
- [ ] Happy-path control test produces a pass/fail report for at least 5 controls from the register
- [ ] SoD matrix identifies at least one conflict and produces a remediation recommendation
