# AutoCount AOTG Connector

Connects Shogun OS to AutoCount AOTG (AutoCount Online Transfer Gateway) — Malaysia's most popular SMB accounting software. Provides read/write access to stock balances, sales invoices, debtor aging, purchase orders, and stock adjustments.

## Prerequisites

- Python 3.8+
- `requests` library (`pip install requests`)
- AutoCount AOTG API credentials (API URL, API Key, Company DB)

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `AUTOCOUNT_API_URL` | Base URL of the AutoCount AOTG API | Yes |
| `AUTOCOUNT_API_KEY` | API key for authentication | Yes |
| `AUTOCOUNT_COMPANY_DB` | Target company database name | Yes |

## Usage

### As a Python module

```python
from autocount_connector import AutoCountAdapter

# Create adapter with explicit config
adapter = AutoCountAdapter(
    api_url="https://api.autocount.my/v1",
    api_key="your-api-key",
    company_db="MyCompanyDB",
)

# Or from environment variables
adapter = AutoCountAdapter()

# Connect and verify
result = adapter.connect()
if result["success"]:
    print("Connected!")

# Read stock balances
result = adapter.read_stock_balance()
print(result["data"])

# Read stock balance for a specific SKU
result = adapter.read_stock_balance(sku="PROD-001")

# Read sales invoices since a date
result = adapter.read_sales_invoices(since="2025-01-01")

# Read debtor aging report
result = adapter.read_debtor_aging()

# Read purchase orders by status
result = adapter.read_purchase_orders(status="Open")

# Create a new sales invoice
result = adapter.write_sales_invoice({
    "customer_code": "CUST001",
    "date": "2025-06-01",
    "items": [
        {"sku": "PROD-001", "quantity": 10, "unit_price": 150.00},
        {"sku": "PROD-002", "quantity": 5, "unit_price": 75.50},
    ],
    "reference_no": "INV-2025-001",
})

# Post a stock adjustment
result = adapter.write_stock_adjustment({
    "date": "2025-06-01",
    "items": [
        {"sku": "PROD-001", "quantity": -2, "reason": "Damaged inventory"},
    ],
    "reference_no": "ADJ-001",
})
```

### From the command line

```bash
# Test connectivity
python autocount_connector.py connect

# Read stock balances
python autocount_connector.py stock
python autocount_connector.py stock PROD-001

# Read sales invoices
python autocount_connector.py invoices
python autocount_connector.py invoices 2025-01-01

# Read debtor aging
python autocount_connector.py aging

# Read purchase orders
python autocount_connector.py orders
python autocount_connector.py orders Open

# Health check
python autocount_connector.py health
```

## Return Format

All methods return a standardized dict:

```python
{
    "success": bool,   # True if the operation succeeded
    "data": any,       # The response data (None on failure)
    "error": str|None, # Error message on failure (None on success)
}
```

## Error Handling

- `AutoCountAuthError` — Authentication failures (invalid API key, expired token)
- `AutoCountAPIError` — Non-success HTTP status codes with server error message
- `AutoCountError` — Generic connector errors (missing config, network issues)

## Supported Methods

| Method | Description |
|---|---|
| `connect()` | Verify API connectivity |
| `read_stock_balance(sku=None)` | Read stock balances, optionally filtered by SKU |
| `read_sales_invoices(since=None)` | Read sales invoices, optionally filtered by date |
| `read_debtor_aging()` | Read debtor aging report |
| `read_purchase_orders(status=None)` | Read purchase orders, optionally filtered by status |
| `write_sales_invoice(data)` | Create a new sales invoice |
| `write_stock_adjustment(data)` | Post a stock adjustment (write-off) |

## API Endpoints

The connector uses these API paths (relative to `AUTOCOUNT_API_URL`):

| Path | Method | Description |
|---|---|---|
| `/system/info` | GET | Connection test / server info |
| `/stock/balance` | GET | Stock balance lookup |
| `/sales/invoices` | GET | List sales invoices |
| `/sales/invoices` | POST | Create sales invoice |
| `/debtor/aging` | GET | Debtor aging report |
| `/purchase/orders` | GET | List purchase orders |
| `/stock/adjustments` | POST | Create stock adjustment |

## Troubleshooting

1. **"requests library not found"** — Run `pip install requests`
2. **Connection timeout** — Verify `AUTOCOUNT_API_URL` is reachable and the API is running
3. **401 Unauthorized** — Check `AUTOCOUNT_API_KEY` and `AUTOCOUNT_COMPANY_DB`
4. **Empty results** — Verify the company database has data and date filters are correct
5. **Rate limiting** — AutoCount AOTG may throttle requests; add backoff if needed