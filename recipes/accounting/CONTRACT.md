---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Accounting Provider Contract

> **Standard tool names and response shapes for accounting integrations.**
> Any provider that implements these tools can be plugged into any Hermes Agent profile.

## Tools

### acct_list_sales_invoices

List sales invoices with optional filters.

**Input:**
```json
{
  "search": "string (optional)",
  "contact_id": "integer (optional)",
  "date_from": "string (YYYY-MM-DD, optional)",
  "date_to": "string (YYYY-MM-DD, optional)",
  "status": "string (optional: draft | pending_approval | ready | void)",
  "limit": "integer (optional, default: 50)",
  "offset": "integer (optional, default: 0)"
}
```

**Output:**
```json
{
  "invoices": [
    {
      "id": "integer",
      "number": "string",
      "number2": "string (reference/DO number)",
      "date": "YYYY-MM-DD",
      "contact_id": "integer",
      "contact_name": "string",
      "currency_code": "string",
      "total": "number",
      "balance_due": "number",
      "status": "string",
      "payment_mode": "string (credit | cash)"
    }
  ],
  "total": "integer"
}
```

### acct_create_sales_invoice

Create a new sales invoice.

**Input:**
```json
{
  "contact_id": "integer (required)",
  "date": "string (YYYY-MM-DD, required)",
  "currency_code": "string (default: MYR)",
  "exchange_rate": "number (default: 1)",
  "number2": "string (optional, reference/DO number)",
  "payment_mode": "string (required: credit | cash)",
  "status": "string (required: draft | ready)",
  "tax_mode": "string (required: exclusive | inclusive)",
  "description": "string (optional)",
  "remarks": "string (optional)",
  "billing_party": "string (optional)",
  "shipping_party": "string (optional)",
  "term_items": [
    {
      "term_id": "integer (required for credit mode)",
      "date": "YYYY-MM-DD",
      "amount": "number",
      "payment_due": "string"
    }
  ],
  "deposit_items": [
    {
      "account_id": "integer (required for cash mode)",
      "amount": "number"
    }
  ],
  "form_items": [
    {
      "account_id": "integer (required)",
      "description": "string (required)",
      "product_id": "integer (optional)",
      "quantity": "number (required)",
      "unit_price": "number (required)",
      "amount": "number (optional, auto-calc)",
      "service_date": "string (YYYY-MM-DD, optional)"
    }
  ]
}
```

**Output:**
```json
{
  "id": "integer",
  "number": "string",
  "status": "string",
  "total": "number"
}
```

### acct_list_purchase_bills

List purchase bills with optional filters.

**Input:**
```json
{
  "search": "string (optional)",
  "contact_id": "integer (optional)",
  "date_from": "string (YYYY-MM-DD, optional)",
  "date_to": "string (YYYY-MM-DD, optional)",
  "status": "string (optional)",
  "limit": "integer (optional, default: 50)",
  "offset": "integer (optional, default: 0)"
}
```

**Output:**
```json
{
  "bills": [
    {
      "id": "integer",
      "number": "string",
      "number2": "string (vendor reference)",
      "date": "YYYY-MM-DD",
      "contact_id": "integer",
      "contact_name": "string",
      "currency_code": "string",
      "total": "number",
      "balance_due": "number",
      "status": "string"
    }
  ],
  "total": "integer"
}
```

### acct_create_purchase_bill

Create a new purchase bill (expense).

**Input:**
```json
{
  "contact_id": "integer (required)",
  "date": "string (YYYY-MM-DD, required)",
  "currency_code": "string (default: MYR)",
  "exchange_rate": "number (default: 1)",
  "number2": "string (optional, vendor invoice ref)",
  "payment_mode": "string (required: credit | cash)",
  "status": "string (required: draft | ready)",
  "tax_mode": "string (required: exclusive | inclusive)",
  "description": "string (optional)",
  "billing_party": "string (optional)",
  "form_items": [
    {
      "account_id": "integer (required)",
      "description": "string (required)",
      "quantity": "number (required)",
      "unit_price": "number (required)",
      "amount": "number (optional, auto-calc)"
    }
  ]
}
```

**Output:**
```json
{
  "id": "integer",
  "number": "string",
  "status": "string",
  "total": "number"
}
```

### acct_list_contacts

List customers and/or vendors.

**Input:**
```json
{
  "type": "string (optional: customer | supplier | all, default: all)",
  "search": "string (optional)",
  "limit": "integer (optional, default: 50)",
  "offset": "integer (optional, default: 0)"
}
```

**Output:**
```json
{
  "contacts": [
    {
      "id": "integer",
      "name": "string",
      "email": "string",
      "phone": "string",
      "type": "string (customer | supplier)",
      "billing_party": "string",
      "reg_no": "string (optional)"
    }
  ],
  "total": "integer"
}
```

### acct_create_contact

Create a new customer or supplier contact.

**Input:**
```json
{
  "name": "string (required)",
  "email": "string (optional)",
  "phone": "string (optional)",
  "type": "string (required: customer | supplier | both)",
  "entity_type": "string (optional: MALAYSIAN_COMPANY | GENERAL_PUBLIC)",
  "reg_no": "string (optional)",
  "billing_party": "string (optional)",
  "shipping_party": "string (optional)"
}
```

**Output:**
```json
{
  "id": "integer",
  "name": "string",
  "type": "string"
}
```

### acct_list_products

List products/services.

**Input:**
```json
{
  "search": "string (optional)",
  "limit": "integer (optional, default: 50)",
  "offset": "integer (optional, default: 0)"
}
```

**Output:**
```json
{
  "products": [
    {
      "id": "integer",
      "name": "string",
      "unit_label": "string",
      "unit_price": "number",
      "account_id": "integer",
      "account_name": "string"
    }
  ],
  "total": "integer"
}
```

### acct_get_profit_loss

Get Profit & Loss summary for a date range.

**Input:**
```json
{
  "date_from": "string (YYYY-MM-DD, required)",
  "date_to": "string (YYYY-MM-DD, required)"
}
```

**Output:**
```json
{
  "total_revenue": "number",
  "total_expenses": "number",
  "net_profit": "number",
  "revenue_accounts": [
    {
      "account_id": "integer",
      "account_name": "string",
      "amount": "number"
    }
  ],
  "expense_accounts": [
    {
      "account_id": "integer",
      "account_name": "string",
      "amount": "number"
    }
  ]
}
```

### acct_get_balance_sheet

Get balance sheet summary.

**Input:**
```json
{
  "as_of_date": "string (YYYY-MM-DD, optional, default: today)"
}
```

**Output:**
```json
{
  "total_assets": "number",
  "total_liabilities": "number",
  "total_equity": "number",
  "asset_accounts": [
    {
      "account_id": "integer",
      "account_name": "string",
      "amount": "number"
    }
  ],
  "liability_accounts": [
    {
      "account_id": "integer",
      "account_name": "string",
      "amount": "number"
    }
  ],
  "equity_accounts": [
    {
      "account_id": "integer",
      "account_name": "string",
      "amount": "number"
    }
  ]
}
```

### acct_get_aging_report

Get Accounts Receivable / Accounts Payable aging report.

**Input:**
```json
{
  "type": "string (required: receivable | payable)",
  "as_of_date": "string (YYYY-MM-DD, optional, default: today)"
}
```

**Output:**
```json
{
  "type": "string",
  "as_of_date": "YYYY-MM-DD",
  "total": "number",
  "buckets": [
    {
      "range": "string (e.g. 0-30, 31-60, 61-90, 90+)",
      "total": "number"
    }
  ],
  "items": [
    {
      "contact_id": "integer",
      "contact_name": "string",
      "invoice_number": "string",
      "date": "YYYY-MM-DD",
      "due_date": "YYYY-MM-DD",
      "amount": "number",
      "days_overdue": "integer"
    }
  ]
}
```

### acct_update_invoice_status

Update the status of an existing invoice (void, approve, etc.).

**Input:**
```json
{
  "id": "integer (required)",
  "type": "string (required: invoice | bill)",
  "status": "string (required: void | ready | draft)"
}
```

**Output:**
```json
{
  "id": "integer",
  "number": "string",
  "status": "string"
}
```

## Error Response Shape

All tools return this on error:

```json
{
  "error": "string description",
  "code": "MISSING_FIELD | AUTH_FAILED | RATE_LIMITED | NOT_FOUND | PROVIDER_ERROR | NOT_IMPLEMENTED"
}
```

## Provider Requirements

To support this contract, a provider MUST implement these P0 tools:

| Tool | Priority | Required for MVP |
|------|----------|-----------------|
| `acct_list_sales_invoices` | P0 | ✅ |
| `acct_create_sales_invoice` | P0 | ✅ |
| `acct_list_purchase_bills` | P0 | ✅ |
| `acct_create_purchase_bill` | P0 | ✅ |
| `acct_list_contacts` | P0 | ✅ |
| `acct_create_contact` | P0 | ✅ |
| `acct_list_products` | P0 | ✅ |
| `acct_get_profit_loss` | P0 | ✅ |
| `acct_get_balance_sheet` | P0 | ✅ |
| `acct_get_aging_report` | P0 | ✅ |
| `acct_update_invoice_status` | P0 | ✅ |

Missing tools return `{"error": "Not implemented", "code": "NOT_IMPLEMENTED"}`.