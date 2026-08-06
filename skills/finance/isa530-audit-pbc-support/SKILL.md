---
name: isa530-audit-pbc-support
description: "Use when executing ISA 530 Audit Sampling (deterministic Python random sampling), packaging Prepared by Client (PBC) documents, or vaulting audit trails. Produces a sample selection list and a PBC document package."
version: 1.0.0
author: Shogun OS
license: MIT
metadata:
  hermes:
    tags: [finance, audit, isa530, sampling, pbc, audit-trail, governance, malaysia]
    category: finance
    related_skills: [internal-control-governance, financial-statement-prep, period-end-close-checklist]
---

# ISA 530 Audit Sampling & PBC Request Management

## Overview

Executes ISA 530 Audit Sampling (deterministic Python random sampling), Prepared by Client (PBC) document packaging, and audit trail vaulting. The skill produces a sample selection list (with seed-documented deterministic random selection) and a structured PBC document package for external auditors — using existing `acct_*` contract tools for population data and the gbrain finance source for document storage. No new audit-software integration is implied.

## When to Use

- External auditors have issued a PBC request list and the finance team must gather and package the requested documents
- Audit fieldwork requires a random sample from a transaction population (e.g., invoices, payment vouchers) under ISA 530
- Internal audit requires a statistically supportable sample for substantive testing
- Year-end close requires an audit trail vault of period-end journals and reconciliations

Don't use for: internal control testing — see [internal-control-governance](../internal-control-governance/SKILL.md); statutory financial statement preparation — see [financial-statement-prep](../financial-statement-prep/SKILL.md).

## Prerequisites

- Owning profile: `finance-manager`
- MCP / tools: `acct_list_sales_invoices`, `acct_list_purchase_bills`, `acct_list_contacts` (existing `acct_*` contract tools)
- gbrain `finance` source (PBC packages at `finance/audit/pbc/`, audit trail vault at `finance/audit/trail/`)
- Script: deterministic Python `random.seed(audit_ref)` sampling (inline, no external library beyond stdlib)

## Workflows

### ISA 530 Sample Selection

1. Define the sampling population: pull the full transaction list for the audit period via the relevant `acct_*` tool (e.g., `acct_list_sales_invoices` for revenue sampling, `acct_list_purchase_bills` for AP sampling) — done when: every item in the population is listed with a unique identifier and amount.
2. Determine sample size per ISA 530 guidance (tolerable misstatement, expected error rate, confidence level — provided by the auditor or agreed with the audit committee) — done when: sample size N is confirmed.
3. Execute deterministic random sampling: `random.seed(audit_reference_string)` then `random.sample(population, N)` — done when: the sample list is produced with a documented seed (audit_reference_string) to allow replication by the auditor.
4. Output the sample selection list with: item ID, transaction date, amount, description, and the population size / seed used — done when: the sample list is saved to `finance/audit/pbc/sample-<audit_ref>.json`.

### PBC Document Packaging

1. Load the auditor's PBC request list from `finance/audit/pbc/pbc-requests-<audit_ref>.json` in the gbrain finance source — done when: each PBC line item is listed with a request number, description, and required evidence.
2. For each PBC item, locate or generate the supporting document (journal entry printout, reconciliation, invoice, approval email reference) — done when: every PBC item is matched to a document reference or flagged as "pending".
3. Package all documents into a structured folder `finance/audit/pbc/package-<audit_ref>/` with a cover index — done when: the PBC package is complete and the cover index lists every item with its document reference and status (provided / pending).

### Audit Trail Vault

1. At period-end, gather all GL journal entries, bank reconciliations, and management accounts for the period from the gbrain finance source — done when: all period-end documents are identified.
2. Archive them to `finance/audit/trail/<YYYY-MM>/` with timestamps — done when: the vault folder is complete and the index file lists every document with its timestamp.

## Common Pitfalls

1. **ISA 530 audit sampling** — ISA 530 requires the auditor to design the sample to provide a reasonable basis for drawing conclusions about the population. The deterministic seed (`random.seed(audit_reference_string)`) must be documented so the selection is replicable; an undocumented seed makes the sample unverifiable by the auditor.
2. **Population completeness** — the sample is only as valid as the completeness of the population; if some invoices are missing from the `acct_*` tool output, the sample will have a completeness deficiency. Confirm population counts before sampling.
3. **PBC timeliness** — late PBC responses are a common audit delay; flag PBC items as "pending" with a due date and escalate to the CFO if the due date is exceeded.
4. **Audit trail retention** — Malaysian companies must retain accounting records for at least 7 years under the Companies Act 2016 and the Income Tax Act 1967; ensure the vault path in the gbrain finance source is on persistent storage.
5. **Deterministic vs. monetary-unit sampling** — ISA 530 allows statistical and non-statistical sampling; the skill implements simple random sampling. For monetary-unit sampling (weighted by transaction value), a separate approach is required and should be agreed with the auditor.

## Verification Checklist

- [ ] Skill installed under owning profile `skills/isa530-audit-pbc-support/`
- [ ] `/isa530-audit-pbc-support` loads on the `finance-manager` profile
- [ ] Happy-path sample selection produces a deterministic sample list with a documented seed that can be reproduced
- [ ] PBC package is produced with a cover index listing all items and their status (provided / pending)
