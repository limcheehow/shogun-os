---
name: procurement-provider
category: connector
setup_time: 5 min
cost: $0
depends_on: []
---

# Procurement Skill (Generic)

> **Works with any procurement provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**

## Prerequisites

- An MCP server named `procurement` configured in the profile's `config.yaml`
- Provider-specific env vars set in the profile's `.env`

## Workflows

### "List recent purchase orders"
1. Call `proc_list_purchase_orders` with optional filters
2. Format as table: PO# | Vendor | Date | Total | Status

### "Create a purchase order"
1. Gather: vendor, date, line items (description, qty, unit price)
2. Call `proc_create_purchase_order` with structured data
3. Confirm with PO number and total

### "Find or create a vendor"
1. Search via `proc_list_vendors(search=name)`
2. If found → return existing ID
3. If not → call `proc_create_vendor` with details

### "Check expiring contracts"
1. Call `proc_list_contracts(expiring_within_days=30)`
2. List contracts expiring soon with dates and values

### "Open RFQs"
1. Call `proc_list_rfqs(status=open)`
2. List open RFQs sorted by due date

## Cron Job Templates

**Contract expiry** (Monday 9AM):
```bash
hermes cron create "0 9 * * 1" --name "Contract Expiry Check" --prompt "Check for expiring contracts using proc_list_contracts(expiring_within_days=30). List contracts expiring in the next 30 days sorted by end date." --skill "procurement-provider" --deliver origin
```