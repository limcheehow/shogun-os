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
| `proc_list_inventory` | P0 |
| `proc_get_item` | P0 |
| `proc_update_stock` | P0 |
| `proc_check_reorder_alerts` | P0 |
| `proc_record_stock_movement` | P1 |
| `proc_list_stock_movements` | P1 |

---

## Inventory Tools (Extension)

> **Inventory tool specs for the procurement inventory layer. Implemented in `recipes/procurement/plugins/brain_inventory.py`.**

### proc_list_inventory

List all inventory items with optional filters.

**Input:** `{ "search": "string", "category": "string", "status": "string", "below_reorder": false, "limit": 50, "offset": 0 }`

**Output:** `{ "items": [{ "sku": "string", "name": "string", "category": "string", "current_stock": 0, "unit_cost": 0.0, "reorder_point": 0, "preferred_vendor_id": "string", "location_id": "string", "status": "string" }], "total": 0 }`

### proc_get_item

Get a single inventory item by SKU.

**Input:** `{ "sku": "string (required)" }`

**Output:** `{ "sku": "string", "name": "string", "category": "string", "current_stock": 0, "unit_cost": 0.0, "reorder_point": 0, "safety_stock": 0, "preferred_vendor_id": "string", "location_id": "string", "last_movement_date": "YYYY-MM-DD", "status": "string" }`

### proc_update_stock

Update stock level for an inventory item (atomic delta or absolute set).

**Input:** `{ "sku": "string (required)", "delta": 0, "absolute": 0, "note": "string" }` — supply either `delta` or `absolute`, not both.

**Output:** `{ "sku": "string", "previous_stock": 0, "new_stock": 0, "unit_cost": 0.0, "total_value": 0.0 }`

### proc_record_stock_movement

Append an immutable stock movement log entry to `procurement/stock-movements/`.

**Input:** `{ "sku": "string (required)", "movement_type": "receive | issue | adjustment | return | damage (required)", "quantity": 0, "reference_id": "string", "location_id": "string", "actor": "string", "note": "string" }`

**Output:** `{ "movement_id": "string", "sku": "string", "movement_type": "string", "quantity": 0, "timestamp": "ISO8601", "reference_id": "string" }`

### proc_list_stock_movements

List stock movement log entries from `procurement/stock-movements/`. Closes the
write/read asymmetry — the council can now *list* movements, not just *log*
them via `proc_record_stock_movement`.

**Input:** `{ "sku": "string (optional)", "date_from": "YYYY-MM-DD (optional)", "date_to": "YYYY-MM-DD (optional)", "movement_type": "receive | issue | adjustment | return | damage (optional)", "limit": 100, "offset": 0 }`

**Output:** `{ "movements": [{ "movement_id": "string", "sku": "string", "movement_type": "string", "quantity": 0, "timestamp": "ISO8601", "reference_id": "string", "location_id": "string", "actor": "string", "note": "string" }], "total": 0 }`

### proc_check_reorder_alerts

Return all items whose current stock is at or below their reorder point, sorted by severity.

**Input:** `{ "category": "string", "location_id": "string" }`

**Output:** `{ "alerts": [{ "sku": "string", "name": "string", "current_stock": 0, "reorder_point": 0, "safety_stock": 0, "preferred_vendor_id": "string", "recommended_order_qty": 0, "severity": "critical | warning" }], "total": 0 }`