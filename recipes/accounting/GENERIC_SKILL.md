---
name: accounting-provider
category: connector
setup_time: 10 min
cost: $0
depends_on: []
---

# Accounting Skill (Generic)

> **Works with any accounting provider that implements the [CONTRACT.md](CONTRACT.md) standard tools.**
> The unified bridge (`bridges/acct-bridge.py`) loads a provider plugin based on the `ACCT_PROVIDER` env var.

This skill teaches the agent how to handle accounting queries and workflows using standard `acct_*` tool names. It works identically whether the backend is Bukku, QuickBooks, Xero, or a custom provider — the bridge translates.

## Prerequisites

- An MCP server named `accounting` configured in the profile's `config.yaml`
- The server exposes tools: `acct_list_sales_invoices`, `acct_create_sales_invoice`, `acct_list_purchase_bills`, `acct_create_purchase_bill`, `acct_list_contacts`, `acct_create_contact`, `acct_list_products`, `acct_get_profit_loss`, `acct_get_balance_sheet`, `acct_get_aging_report`, `acct_update_invoice_status`
- Provider-specific env vars set in the profile's `.env` (see provider docs)

## Workflows

### "List recent invoices"

1. Call `acct_list_sales_invoices` with optional filters (date range, status, contact)
2. Format as a table with: Number | Date | Customer | Total | Balance | Status
3. Default to last 30 days if no filter specified

### "Create a sales invoice"

1. Gather: customer, date, line items (product, qty, unit price), payment mode
2. Call `acct_create_sales_invoice` with the structured data
3. Verify the invoice was created by checking the returned ID
4. Confirm to the user with the invoice number and total

### "Check duplicate invoice"

1. Search by reference number via `acct_list_sales_invoices(search=ref_no)`
2. If match found → report as existing, do not create
3. If no match → proceed with creation

### "List purchase bills"

1. Call `acct_list_purchase_bills` with optional filters
2. Format as a table: Number | Date | Vendor | Total | Balance | Status

### "Record an expense / purchase bill"

1. Gather: vendor, date, items (account, description, qty, unit price)
2. Check for duplicates via `acct_list_purchase_bills(search=ref_no)`
3. Call `acct_create_purchase_bill` with structured data
4. Confirm with bill number and total

### "Find or create a contact"

1. Search via `acct_list_contacts(search=name)`
2. If found → return existing contact ID
3. If not found → call `acct_create_contact` with provided details
4. Return the new contact ID

### "P&L report"

1. Call `acct_get_profit_loss(date_from=start, date_to=end)`
2. Format: Total Revenue, Total Expenses, Net Profit
3. Provide a breakdown by top revenue/expense accounts

### "Balance sheet"

1. Call `acct_get_balance_sheet(as_of_date=date)`
2. Format: Total Assets, Total Liabilities, Total Equity

### "Aging report"

1. Call `acct_get_aging_report(type=receivable | payable)`
2. Format by aging buckets (0-30, 31-60, 61-90, 90+)
3. List overdue items with contact name and amount

### "Void an invoice"

1. Call `acct_update_invoice_status(id=..., type=invoice, status=void)`
2. Confirm the status change

## Cron Job Templates

**Daily burn rate** (daily 8AM):
```bash
hermes cron create "0 8 * * *" \
  --name "Daily Burn Rate" \
  --prompt "Run daily burn rate check using acct_get_profit_loss for current month and acct_list_purchase_bills for recent 7 days. Report total spend month-to-date, largest recent expenses, and compare against budget." \
  --skill "accounting-provider" \
  --deliver origin
```

**Invoice aging** (Monday 8AM):
```bash
hermes cron create "0 8 * * 1" \
  --name "Invoice Aging" \
  --prompt "Run invoice aging report using acct_get_aging_report(type=receivable). List overdue invoices grouped by aging bucket. Flag invoices over 60 days overdue." \
  --skill "accounting-provider" \
  --deliver origin
```

**Monthly P&L** (1st of month 8AM):
```bash
hermes cron create "0 8 1 * *" \
  --name "Monthly P&L" \
  --prompt "Run monthly P&L using acct_get_profit_loss for last month. Report total revenue, expenses, net profit, and compare against the previous month. Highlight any significant changes." \
  --skill "accounting-provider" \
  --deliver origin
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Tool acct_list_sales_invoices not found` | MCP bridge not configured | Check `mcp_servers.accounting` in config.yaml |
| `AUTH_FAILED` | API key or token invalid | Check `ACCT_API_KEY` in profile `.env` |
| `PROVIDER_ERROR` | Provider API error | Check provider API status and credentials |
| Bukku returns 422 | Missing required fields | Check `payment_mode`, `status`, `tax_mode` are all provided |
| QuickBooks OAuth expired | Refresh token stale | Re-run OAuth flow, update `ACCT_REFRESH_TOKEN` |

## Adding a New Provider

If you're adding a new accounting provider (not Bukku/QuickBooks/Xero):

1. Create `~/.hermes/scripts/accounting/plugins/<provider>.py`
2. Implement `get_tool_schemas()` and `handle_tool()` per [CONTRACT.md](CONTRACT.md)
3. Set `ACCT_PROVIDER=<provider>` in the profile's `.env`
4. Configure the MCP bridge:
   ```yaml
   mcp_servers:
     accounting:
       command: python3
       args: [~/.hermes/scripts/acct-bridge.py]
       env:
         ACCT_PROVIDER: "${ACCT_PROVIDER}"
         ACCT_API_KEY: "${ACCT_API_KEY}"
   ```
5. Set additional env vars as required by the provider:
   - **Bukku** also needs `ACCT_SUBDOMAIN`
   - **QuickBooks** also needs `ACCT_CLIENT_ID`, `ACCT_CLIENT_SECRET`, `ACCT_REFRESH_TOKEN`, `ACCT_COMPANY_ID`
   - **Xero** also needs `ACCT_CLIENT_ID`, `ACCT_CLIENT_SECRET`, `ACCT_REFRESH_TOKEN`, `ACCT_TENANT_ID`
   See provider docs in `providers/` for full details.
6. This skill works immediately — no changes needed