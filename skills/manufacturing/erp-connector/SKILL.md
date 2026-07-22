---
name: erp-connector
description: "Generic ERP connector framework. Adapters for Odoo (XML-RPC), ERPNext (Frappe REST). Reads: work orders, BOMs, inventory levels. All credentials via env vars."
version: 1.0.0
tags: [manufacturing, erp, connector, odoo, erpnext, integration]
triggers:
  - "connect erp"
  - "sync erp"
  - "odoo connector"
  - "erpnext connector"
  - "erp work orders"
  - "erp bom"
  - "erp inventory"
---

# ERP Connector

Generic ERP connector framework supporting multiple backend adapters. Provides a unified interface for reading work orders, bills of materials (BOMs), and inventory levels. All credentials are configured via environment variables.

## Supported Adapters

| Adapter | Protocol | Endpoints | Authentication |
|---------|----------|-----------|----------------|
| Odoo | XML-RPC | `/xmlrpc/2/common`, `/xmlrpc/2/object` | API key + database |
| ERPNext | REST (Frappe) | `/api/method/`, `/api/resource/` | API key + secret |

## Usage

### List Work Orders

```
erp work-orders --status "In Progress" [--limit 50]
```

### Get BOM

```
erp bom --product PRODUCT-001
```

### Check Inventory

```
erp inventory --sku RM-001 [--location WH-A]
```

### Sync to Local Storage

```
erp sync --entities work_orders,inventory,boms --output-dir ./data/erp/
```

### Test Connection

```
erp test-connection
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ERP_ADAPTER` | ERP adapter name (odoo, erpnext) | `odoo` |
| `ERP_HOST` | ERP server hostname | `localhost` |
| `ERP_PORT` | ERP server port | `8069` |
| `ERP_DATABASE` | ERP database name | `production` |
| `ERP_USERNAME` | ERP API username | — |
| `ERP_API_KEY` | ERP API key or password | — |
| `ERP_API_SECRET` | ERP API secret (ERPNext only) | — |
| `ERP_TIMEOUT` | API request timeout in seconds | `30` |
| `ERP_SYNC_INTERVAL` | Default sync interval in minutes | `15` |
| `ERP_CACHE_TTL` | Local cache TTL in seconds | `300` |

### Adapter-Specific Configuration

#### Odoo

```env
ERP_ADAPTER=odoo
ERP_HOST=odoo.example.com
ERP_PORT=8069
ERP_DATABASE=production_db
ERP_USERNAME=api_user
ERP_API_KEY=odoo_api_key_here
```

#### ERPNext

```env
ERP_ADAPTER=erpnext
ERP_HOST=erpnext.example.com
ERP_PORT=80
ERP_USERNAME=api_user
ERP_API_KEY=erpnext_api_key
ERP_API_SECRET=erpnext_api_secret
```

## Data Models

### Work Order

```json
{
  "id": "WO-001234",
  "product": "PROD-001",
  "quantity": 100,
  "status": "in_progress",
  "released_date": "2024-01-01",
  "due_date": "2024-01-10",
  "bom_id": "BOM-001",
  "routing_id": "ROUTING-001"
}
```

### Bill of Materials

```json
{
  "id": "BOM-001",
  "product": "PROD-001",
  "type": "normal",
  "components": [
    {"sku": "RM-001", "quantity": 2.0, "unit": "pcs"},
    {"sku": "RM-002", "quantity": 0.5, "unit": "kg"}
  ]
}
```

## Scripts

### `scripts/erp-adapter-base.py`

Base adapter class with connection management, retry logic, and error handling.

### `scripts/erp-adapter-odoo.py`

Odoo-specific adapter using XML-RPC with read/write/search operations.

### `scripts/erp-adapter-erpnext.py`

ERPNext-specific adapter using Frappe REST API.

### `scripts/erp-sync.py`

Scheduled sync engine that pulls data from ERP to local storage.

## Related Skills

- [work-order-tracking](../work-order-tracking/SKILL.md) — Work orders from ERP
- [warehouse-inventory](../warehouse-inventory/SKILL.md) — Inventory levels from ERP
- [mes-connector](../mes-connector/SKILL.md) — Production data may need ERP reference
- [production-oee](../production-oee/SKILL.md) — BOM and routing data for OEE calculation

## Pitfalls

- **API rate limits**: ERP systems may throttle API calls. Implement exponential backoff and batch requests.
- **Session management**: XML-RPC sessions expire. Implement automatic reconnection with session renewal.
- **Data model drift**: ERP customizations change field names. Version-lock your adapter to the ERP schema version.
- **ID mismatch**: Local IDs may differ from ERP IDs. Maintain a mapping table for cross-referencing.
- **Incremental sync**: Full syncs are expensive. Use timestamp-based or sequence-based incremental sync where possible.
- **Credential rotation**: API keys expire. Set up monitoring for credential expiry and implement a rotation workflow.
- **Network segmentation**: ERP servers may be on isolated networks. Verify connectivity and configure proxy settings if needed.