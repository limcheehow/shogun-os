---
name: compliance-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# Compliance Skill (Generic)

> **Works with any compliance provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `compliance` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List pending documents for signature"
1. Call `comp_list_documents(status=signed)` or all statuses
2. Format as table: Document | Type | Status | Signers | Completed Date

### "Send a document for signature"
1. Gather: document name, file path, signers (name + email)
2. Call `comp_send_for_signature` with structured data
3. Confirm with signing URL

### "List active policies"
1. Call `comp_list_policies(status=active)` sorted by review date
2. Flag policies approaching their review date

### "View audit trail"
1. Call `comp_list_audit_logs(date_from=..., date_to=...)` for a date range
2. List recent actions with user, action, and timestamp

### "Compliance check"
1. Call `comp_check_compliance(standard=...)` for a specific standard
2. Report overall status and control-level breakdown

## Cron Job Templates

**Policy review** (Monday 9AM):
```bash
hermes cron create "0 9 * * 1" --name "Policy Review" --prompt "Check for policies approaching review date using comp_list_policies(status=active). Flag policies with review_date within 30 days." --skill "compliance-provider" --deliver origin
```