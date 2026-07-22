# Lazada Seller Center REST API Connector

Connects Shogun OS to Lazada Open Platform (LOP) API for Southeast Asian marketplace operations. Provides read/write access to orders, products, finance data, and seller performance. Uses Lazada's custom HMAC-SHA256 signing with zero external dependencies (stdlib only).

## Prerequisites

- Python 3.8+ (no extra packages required — uses `urllib.request` from stdlib)
- Lazada Seller Center account with API access enabled
- Lazada Open Platform App Key and App Secret

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `LAZADA_APP_KEY` | Lazada Open Platform App Key | Yes |
| `LAZADA_APP_SECRET` | Lazada Open Platform App Secret (used for signing) | Yes |
| `LAZADA_ACCESS_TOKEN` | OAuth access token | Yes |
| `LAZADA_SELLER_ID` | Lazada Seller ID | Yes |

## Usage

### As a Python module

```python
from lazada_connector import LazadaAdapter

# Create adapter from environment variables
adapter = LazadaAdapter()

# Or with explicit config for Malaysia
adapter = LazadaAdapter(
    app_key="your-app-key",
    app_secret="your-app-secret",
    access_token="your-access-token",
    seller_id="your-seller-id",
    region="my",  # sg, my, th, id, ph, vn
)

# Connect and verify
result = adapter.connect()
if result["success"]:
    print("Connected to Lazada!")

# Read orders (all statuses, recent)
result = adapter.read_orders()

# Read orders by status
result = adapter.read_orders(status="pending")

# Read orders since a date
result = adapter.read_orders(since="2025-06-01")

# Read all products
result = adapter.read_products()

# Update a product (price, stock, images)
result = adapter.update_product({
    "seller_sku": "PROD-SKU-001",
    "price": 149.90,
    "quantity": 100,
})

# Read financial transactions
result = adapter.read_finance()

# Read seller performance metrics
result = adapter.read_seller_performance()
```

### From the command line

```bash
# Test connectivity
python lazada_connector.py connect

# Read orders
python lazada_connector.py orders
python lazada_connector.py orders pending
python lazada_connector.py orders pending 2025-06-01

# Read products
python lazada_connector.py products

# Update product (from JSON file)
python lazada_connector.py update product.json

# Read finance data
python lazada_connector.py finance

# Read seller performance
python lazada_connector.py performance

# Health check
python lazada_connector.py health
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

- `LazadaAuthError` — Authentication failures (invalid app key/secret, expired token)
- `LazadaAPIError` — Lazada returned an error code with message
- `LazadaError` — Generic connector errors (network issues, missing config)

## Supported Methods

| Method | Description |
|---|---|
| `connect()` | Verify API connectivity (fetches seller info) |
| `read_orders(status=None, since=None)` | Read orders, optionally filtered by status and date |
| `read_products()` | Read all products in the store |
| `update_product(data)` | Update product price, stock, images, description |
| `read_finance()` | Read financial transactions and payouts |
| `read_seller_performance()` | Read seller performance metrics |

## API Authentication

Lazada uses a custom HMAC-SHA256 signing scheme:

1. Collect all request parameters (excluding `sign`)
2. Sort alphabetically by key name
3. Concatenate as `key1value1key2value2...` (no separators)
4. Sign with HMAC-SHA256 using App Secret as the key
5. Convert signature to uppercase hex

The adapter handles this automatically for every request.

## Supported Regions

| Code | Country | API Base URL |
|---|---|---|
| `sg` | Singapore | `https://api.lazada.sg/rest` |
| `my` | Malaysia | `https://api.lazada.com.my/rest` |
| `th` | Thailand | `https://api.lazada.co.th/rest` |
| `id` | Indonesia | `https://api.lazada.co.id/rest` |
| `ph` | Philippines | `https://api.lazada.com.ph/rest` |
| `vn` | Vietnam | `https://api.lazada.vn/rest` |

## Troubleshooting

1. **"App Key not set"** — Verify `LAZADA_APP_KEY` environment variable
2. **401 Unauthorized / Signature error** — Check `LAZADA_APP_SECRET` matches the Lazada Open Platform secret; verify timestamps are in sync (Lazada enforces clock skew limits)
3. **Access token expired** — Lazada tokens expire; implement a token refresh mechanism for production
4. **"Unknown region"** — Use one of the supported region codes above
5. **Empty results** — Verify the seller ID has data and date filters are correct
6. **Rate limiting** — Lazada enforces API call limits; add retry with backoff for production use
7. **Clock skew** — Lazada's signature validation is time-sensitive; ensure the system clock is accurate (NTP sync recommended)