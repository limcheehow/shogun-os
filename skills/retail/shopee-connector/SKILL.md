# Shopee Open Platform API v2 Connector

Connects Shogun OS to Shopee Open Platform API v2 for marketplace operations. Provides read/write access to orders, products, listings, analytics, and returns. Uses HMAC-SHA256 request signing with zero external dependencies (stdlib only).

## Prerequisites

- Python 3.8+ (no extra packages required — uses `urllib.request` from stdlib)
- Shopee Seller Center account with API access enabled
- Shopee Partner ID and API Key (from Shopee Open Platform)

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `SHOPEE_PARTNER_ID` | Seller partner ID (integer) | Yes |
| `SHOPEE_API_KEY` | Partner API key for HMAC signing | Yes |
| `SHOPEE_ACCESS_TOKEN` | OAuth access token | Yes |
| `SHOPEE_SHOP_ID` | Shop ID (integer) | Yes |

## Usage

### As a Python module

```python
from shopee_connector import ShopeeAdapter

# Create adapter from environment variables
adapter = ShopeeAdapter()

# Or with explicit config for Malaysia region
adapter = ShopeeAdapter(
    partner_id=123456,
    api_key="your-api-key",
    access_token="your-access-token",
    shop_id=789012,
    region="my",  # th, sg, my, id, ph, vn, tw, br, mx, co, cl, pl
)

# Connect and verify
result = adapter.connect()
if result["success"]:
    print("Connected to Shopee!")

# Read orders (all statuses, recent)
result = adapter.read_orders()

# Read orders by status
result = adapter.read_orders(status="READY_TO_SHIP")

# Read orders since a date
result = adapter.read_orders(since="2025-06-01")

# Read all products
result = adapter.read_products()

# Update a product listing (price, stock)
result = adapter.update_listing({
    "item_id": 123456789,
    "price": 99.90,
    "stock": 50,
})

# Read analytics
result = adapter.read_analytics(period="this_month")

# Read return/refund requests
result = adapter.read_returns()
```

### From the command line

```bash
# Test connectivity
python shopee_connector.py connect

# Read orders
python shopee_connector.py orders
python shopee_connector.py orders READY_TO_SHIP
python shopee_connector.py orders READY_TO_SHIP 2025-06-01

# Read products
python shopee_connector.py products

# Update listing (from JSON file)
python shopee_connector.py update listing.json

# Read analytics
python shopee_connector.py analytics
python shopee_connector.py analytics this_week

# Read returns
python shopee_connector.py returns

# Health check
python shopee_connector.py health
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

- `ShopeeAuthError` — Authentication failures (invalid partner ID, expired token)
- `ShopeeAPIError` — Shopee API returned an error code with message
- `ShopeeError` — Generic connector errors (network issues, config missing)

## Supported Methods

| Method | Description |
|---|---|
| `connect()` | Verify API connectivity (fetches shop info) |
| `read_orders(status=None, since=None)` | Read orders, optionally filtered by status and date |
| `read_products()` | Read all products in the shop |
| `update_listing(product_data)` | Update product price/stock/description |
| `read_analytics(period)` | Read shop performance analytics |
| `read_returns()` | Read return/refund requests |

## API Authentication

Shopee uses HMAC-SHA256 signing. The signature is computed as:

```
base_string = partner_id + path + timestamp + access_token + shop_id
sign = HMAC_SHA256(api_key, base_string)
```

The adapter handles this automatically for every request.

## Supported Regions

| Code | Country |
|---|---|
| `th` | Thailand |
| `sg` | Singapore |
| `my` | Malaysia |
| `id` | Indonesia |
| `ph` | Philippines |
| `vn` | Vietnam |
| `tw` | Taiwan |
| `br` | Brazil |
| `mx` | Mexico |
| `co` | Colombia |
| `cl` | Chile |
| `pl` | Poland |

## Troubleshooting

1. **"Partner ID not set"** — Verify `SHOPEE_PARTNER_ID` environment variable
2. **401 Unauthorized** — Check `SHOPEE_ACCESS_TOKEN` has not expired (tokens expire ~4 hours; refresh via OAuth)
3. **Signature mismatch** — Verify `SHOPEE_API_KEY` matches the partner key in Shopee Open Platform
4. **"Unknown region"** — Use one of the supported region codes above
5. **Rate limiting** — Shopee limits API calls; implement retry with backoff for production use
6. **Access token expiry** — Shopee access tokens are short-lived; implement a token refresh mechanism for production