"""
Lazada Seller Center REST API Connector for Shogun OS Retail Module.

Connects to Lazada Open Platform (LOP) API for Southeast Asian marketplace
operations. Uses Python stdlib only (urllib.request) — no extra dependencies.

Lazada API authentication uses a custom signature scheme:
  - Sort all request parameters alphabetically by key
  - Concatenate as key=value pairs
  - Sign with HMAC-SHA256 using App Secret as the key
  - The signature is appended as a parameter

Environment Variables:
    LAZADA_APP_KEY        — Lazada Open Platform App Key (API Key)
    LAZADA_APP_SECRET     — Lazada Open Platform App Secret
    LAZADA_ACCESS_TOKEN   — OAuth access token
    LAZADA_SELLER_ID      — Lazada Seller ID
"""

import os
import json
import time
import hmac
import hashlib
import logging
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Lazada API base URLs by region
LAZADA_API_BASE = "https://api.lazada.com.my/rest"
LAZADA_API_BASES = {
    "sg": "https://api.lazada.sg/rest",
    "my": "https://api.lazada.com.my/rest",
    "th": "https://api.lazada.co.th/rest",
    "id": "https://api.lazada.co.id/rest",
    "ph": "https://api.lazada.com.ph/rest",
    "vn": "https://api.lazada.vn/rest",
}


class LazadaError(Exception):
    """Base exception for Lazada connector errors."""
    pass


class LazadaAuthError(LazadaError):
    """Authentication or authorization error."""
    pass


class LazadaAPIError(LazadaError):
    """API returned an error response."""
    def __init__(self, error_code: str, message: str, request_id: Optional[str] = None):
        self.error_code = error_code
        self.request_id = request_id
        super().__init__(f"Lazada API error {error_code}: {message}")


class LazadaAdapter:
    """Adapter for Lazada Seller Center REST API.

    Provides methods to read orders, products, finance data, and seller
    performance, plus update product listings. All methods return a
    standardized dict with 'success', 'data', and 'error' keys.

    Lazada API authentication uses a custom HMAC-SHA256 signature scheme
    with sorted parameters.
    """

    def __init__(
        self,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        seller_id: Optional[str] = None,
        region: str = "my",
    ):
        self.app_key = app_key or os.environ.get("LAZADA_APP_KEY", "")
        self.app_secret = app_secret or os.environ.get("LAZADA_APP_SECRET", "")
        self.access_token = access_token or os.environ.get("LAZADA_ACCESS_TOKEN", "")
        self.seller_id = seller_id or os.environ.get("LAZADA_SELLER_ID", "")
        self.region = region.lower()

        if self.region not in LAZADA_API_BASES:
            raise LazadaError(f"Unknown region '{region}'. Valid: {', '.join(LAZADA_API_BASES.keys())}")

        self.base_url = LAZADA_API_BASES[self.region]

        if not self.app_key:
            logger.warning("LAZADA_APP_KEY is not set.")
        if not self.app_secret:
            logger.warning("LAZADA_APP_SECRET is not set.")
        if not self.access_token:
            logger.warning("LAZADA_ACCESS_TOKEN is not set.")
        if not self.seller_id:
            logger.warning("LAZADA_SELLER_ID is not set.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict) -> str:
        """Generate Lazada API signature per auth spec.

        Lazada signing:
        1. Sort all parameters alphabetically by key
        2. Concatenate as key=value pairs (no separator between pairs)
        3. HMAC-SHA256 with App Secret as key
        4. Convert to uppercase hex

        Note: The 'sign' parameter itself is excluded from signing.
        """
        # Sort alphabetically by key
        sorted_keys = sorted(params.keys())
        # Build the concatenated string: key1value1key2value2...
        concat_string = "".join(f"{k}{params[k]}" for k in sorted_keys)
        # HMAC-SHA256
        sign = hmac.new(
            self.app_secret.encode("utf-8"),
            concat_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()
        return sign

    def _request(self, api_path: str, http_method: str = "GET", body: Optional[dict] = None) -> dict:
        """Make a signed Lazada API request.

        Lazada passes all parameters (including the API action) as query
        string parameters that are signed together.

        Args:
            api_path: The API method path (e.g., '/orders/get')
            http_method: HTTP method (GET or POST)
            body: Request body (for POST requests)

        Returns:
            dict with keys: success (bool), data (any), error (str | None)
        """
        timestamp = int(time.time() * 1000)  # Lazada uses milliseconds

        # Build base parameters (sorted for signing)
        params = {
            "app_key": self.app_key,
            "timestamp": str(timestamp),
            "access_token": self.access_token,
            "sign_method": "sha256",
        }

        # If there's a body, add its fields as top-level params for signing
        if body:
            for k, v in body.items():
                if isinstance(v, (dict, list)):
                    params[k] = json.dumps(v, separators=(",", ":"))
                else:
                    params[k] = str(v)

        # Generate signature over sorted params
        signature = self._sign(params)
        params["sign"] = signature

        # Build full URL
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}{api_path}?{query_string}"

        req = urllib.request.Request(url, method=http_method)

        if http_method == "POST" and body:
            data_bytes = json.dumps(body).encode("utf-8")
            req.data = data_bytes
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_body = resp.read().decode("utf-8")
                parsed = json.loads(response_body)
        except urllib.error.HTTPError as e:
            try:
                error_body = json.loads(e.read().decode("utf-8"))
            except Exception:
                error_body = {"message": str(e)}
            return {
                "success": False,
                "data": None,
                "error": f"HTTP {e.code}: {error_body.get('message', str(e))}",
            }
        except urllib.error.URLError as e:
            return {"success": False, "data": None, "error": f"URL error: {e.reason}"}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return {"success": False, "data": None, "error": f"Response parse error: {e}"}
        except OSError as e:
            return {"success": False, "data": None, "error": f"Network error: {e}"}

        # Check Lazada-specific error response
        code = parsed.get("code")
        if code and code != "0":
            msg = parsed.get("message", "Unknown error")
            request_id = parsed.get("request_id")
            return {
                "success": False,
                "data": None,
                "error": f"Lazada error {code}: {msg} [request_id={request_id}]",
            }

        # The data is usually in the 'data' field or 'result' field
        data = parsed.get("data") or parsed.get("result") or parsed
        return {"success": True, "data": data, "error": None}

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> dict:
        """Verify connectivity to Lazada API by fetching seller info.

        Returns:
            Standardized dict with seller information.
        """
        result = self._request("/seller/get")
        if result["success"]:
            logger.info("Lazada connected: seller_id=%s", self.seller_id)
        else:
            logger.error("Lazada connection failed: %s", result["error"])
        return result

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def read_orders(self, status: Optional[str] = None, since: Optional[str] = None) -> dict:
        """Read orders, optionally filtered by status and creation date.

        Args:
            status: Order status filter (e.g., 'pending', 'ready_to_ship',
                    'shipped', 'delivered', 'canceled', 'returned').
            since: ISO date string (YYYY-MM-DD) to fetch orders from.

        Returns:
            Standardized dict with order records.
        """
        params = {}
        if since:
            created_after = int(datetime.fromisoformat(since).timestamp() * 1000)
            params["created_after"] = str(created_after)
        if status:
            params["status"] = status
        return self._request("/orders/get", body=params)

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def read_products(self) -> dict:
        """Read all products in the Lazada store.

        Returns:
            Standardized dict with product records.
        """
        return self._request("/products/get", body={
            "filter": "all",
            "limit": "100",
            "offset": "0",
        })

    # ------------------------------------------------------------------
    # Product Updates
    # ------------------------------------------------------------------

    def update_product(self, data: dict) -> dict:
        """Update a product listing (price, stock, images, etc.).

        Args:
            data: Product update payload as dict. Expected structure:
                {
                    "seller_sku": str,
                    "price": float (optional),
                    "quantity": int (optional),
                    "images": [str] (optional),
                    "description": str (optional),
                }

        Returns:
            Standardized dict with update result.
        """
        return self._request("/product/update", http_method="POST", body=data)

    # ------------------------------------------------------------------
    # Finance
    # ------------------------------------------------------------------

    def read_finance(self) -> dict:
        """Read financial data (payouts, transaction history).

        Returns:
            Standardized dict with financial records.
        """
        return self._request("/finance/transactions/get", body={
            "limit": "100",
            "offset": "0",
        })

    # ------------------------------------------------------------------
    # Seller Performance
    # ------------------------------------------------------------------

    def read_seller_performance(self) -> dict:
        """Read seller performance metrics.

        Returns:
            Standardized dict with seller performance data (ratings,
            response time, shipping metrics, etc.).
        """
        return self._request("/seller/performance/get")


# ------------------------------------------------------------------
# Convenience helpers
# ------------------------------------------------------------------

def default_adapter(region: str = "my") -> LazadaAdapter:
    """Create a LazadaAdapter from environment variables."""
    return LazadaAdapter(region=region)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python lazada_connector.py <command> [args]")
        print("Commands: connect, orders, products, update, finance, performance, health")
        sys.exit(1)

    adapter = default_adapter()
    command = sys.argv[1].lower()

    if command == "connect":
        result = adapter.connect()
        print(json.dumps(result, indent=2, default=str))

    elif command == "orders":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        since = sys.argv[3] if len(sys.argv) > 3 else None
        result = adapter.read_orders(status=status, since=since)
        print(json.dumps(result, indent=2, default=str))

    elif command == "products":
        result = adapter.read_products()
        print(json.dumps(result, indent=2, default=str))

    elif command == "update":
        if len(sys.argv) < 3:
            print("Usage: python lazada_connector.py update <json_file>")
            sys.exit(1)
        with open(sys.argv[2]) as f:
            data = json.load(f)
        result = adapter.update_product(data)
        print(json.dumps(result, indent=2, default=str))

    elif command == "finance":
        result = adapter.read_finance()
        print(json.dumps(result, indent=2, default=str))

    elif command == "performance":
        result = adapter.read_seller_performance()
        print(json.dumps(result, indent=2, default=str))

    elif command == "health":
        result = adapter.connect()
        if result["success"]:
            print("✓ Lazada API connection is healthy")
        else:
            print(f"✗ Lazada API connection failed: {result['error']}")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)