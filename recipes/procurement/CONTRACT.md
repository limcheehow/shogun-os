---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Procurement Provider Contract

> **Standard tool names and response shapes for procurement integrations.**
> Covers purchase orders, vendor management, contract lifecycle, and RFQ processes.

## Tools

### proc_list_purchase_orders

List purchase orders with filters.

**Input:** `{ "search": "string", "vendor_id": "string", "status": "string", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50, "offset": 0 }`

**Output:** `{ "orders": [{ "id": "string", "number": "string", "vendor_id": "string", "vendor_name": "string", "total": 0, "status": "string", "date": "YYYY-MM-DD" }], "total": 0 }`

### proc_create_purchase_order

Create a new purchase order.

**Input:** `{ "vendor_id": "string (required)", "date": "YYYY-MM-DD (required)", "currency_code": "string", "delivery_date": "YYYY-MM-DD", "notes": "string", "line_items": [{ "description": "string", "quantity": 0, "unit_price": 0, "account_id": "string" }] }`

**Output:** `{ "id": "string", "number": "string", "status": "draft", "total": 0 }`

### proc_list_vendors

List vendors/suppliers.

**Input:** `{ "search": "string", "status": "string", "limit": 50, "offset": 0 }`

**Output:** `{ "vendors": [{ "id": "string", "name": "string", "email": "string", "phone": "string", "status": "string", "payment_terms": "string" }], "total": 0 }`

### proc_create_vendor

Create a new vendor.

**Input:** `{ "name": "string (required)", "email": "string", "phone": "string", "payment_terms": "string", "billing_address": "string" }`

**Output:** `{ "id": "string", "name": "string" }`

### proc_list_contracts

List contracts with filters.

**Input:** `{ "vendor_id": "string", "status": "string", "expiring_within_days": 30, "limit": 50 }`

**Output:** `{ "contracts": [{ "id": "string", "name": "string", "vendor_name": "string", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "value": 0, "status": "string" }], "total": 0 }`

### proc_list_rfqs

List requests for quotation.

**Input:** `{ "status": "string", "vendor_id": "string", "limit": 50 }`

**Output:** `{ "rfqs": [{ "id": "string", "number": "string", "subject": "string", "status": "string", "vendor_count": 0, "due_date": "YYYY-MM-DD" }], "total": 0 }`

## Error Response Shape

All tools return `{"error": "string", "code": "MISSING_FIELD | AUTH_FAILED | RATE_LIMITED | NOT_FOUND | PROVIDER_ERROR | NOT_IMPLEMENTED"}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `proc_list_purchase_orders` | P0 |
| `proc_create_purchase_order` | P0 |
| `proc_list_vendors` | P0 |
| `proc_create_vendor` | P0 |
| `proc_list_contracts` | P1 |
| `proc_list_rfqs` | P1 |