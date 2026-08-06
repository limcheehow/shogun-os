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

### "Check inventory levels"
1. Call `proc_list_inventory` with optional `search`, `category`, or `below_reorder=true` filters
2. Format as table: SKU | Item Name | Category | Qty | Unit Cost | Reorder Point | Status

### "Get a specific inventory item"
1. Call `proc_get_item(sku=<SKU>)` to retrieve the item master record
2. Return SKU, name, category, current stock, unit cost, reorder point, safety stock, location, and last movement date

### "Update stock level"
1. Gather: SKU and either a delta (positive for receipt, negative for issue) or an absolute quantity
2. Call `proc_update_stock(sku=<SKU>, delta=<delta>)` or `proc_update_stock(sku=<SKU>, absolute=<qty>)`
3. Confirm new stock level and updated total value

### "Check reorder alerts"
1. Call `proc_check_reorder_alerts()` to get all items at or below reorder point
2. If empty: report "All stock levels healthy — no reorders required"
3. If alerts: format as table grouped by severity (critical first): SKU | Qty | Reorder Pt | Rec. Order Qty | Vendor

### "Record a stock movement"
1. Gather: SKU, movement_type (receive/issue/adjustment/return/damage), quantity, reference_id (PO# or ticket#), location_id, actor
2. Call `proc_record_stock_movement(...)` to append an immutable log entry
3. Confirm movement ID and timestamp

## Cron Job Templates

**Contract expiry** (Monday 9AM):
```bash
hermes cron create "0 9 * * 1" --name "Contract Expiry Check" --prompt "Check for expiring contracts using proc_list_contracts(expiring_within_days=30). List contracts expiring in the next 30 days sorted by end date." --skill "procurement-provider" --deliver origin
```