"""
Shopee Open Platform API v2 Connector for Shogun OS Retail Module.

Connects to Shopee Open Platform API v2 using OAuth + REST with SHA256
request signing. Uses only Python stdlib (urllib.request) — no extra
dependencies required.

Environment Variables:
    SHOPEE_PARTNER_ID    — Seller partner ID (integer)
    SHOPEE_API_KEY       — Partner API key (used for signing)
    SHOPEE_ACCESS_TOKEN  — OAuth access token
    SHOPEE_SHOP_ID       — Shop ID (integer)
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

# Shopee API base URLs by region
SHOPEE_API_BASES = {
    "th": "https://partner.shopeemobile.com",
    "sg": "https://partner.shopeemobile.com",
    "my": "https://partner.shopeemobile.com",
    "id": "https://partner.shopeemobile.com",
    "ph": "https://partner.shopeemobile.com",
    "vn": "https://partner.shopeemobile.com",
    "tw": "https://partner.shopeemobile.com",
    "br": "https://partner.shopeemobile.com",
    "mx": "https://partner.shopeemobile.com",
    "co": "https://partner.shopeemobile.com",
    "cl": "https://partner.shopeemobile.com",
    "pl": "https://partner.shopeemobile.com",
}

SHOPEE_API_VERSION = "/api/v2"


class ShopeeError(Exception):
    """Base exception for Shopee connector errors."""
    pass


class ShopeeAuthError(ShopeeError):
    """Authentication or authorization error."""
    pass


class ShopeeAPIError(ShopeeError):
    """API returned an error response."""
    def __init__(self, error_code: int, message: str, request_id: Optional[str] = None):
        self.error_code = error_code
        self.request_id = request_id
        super().__init__(f"Shopee API error {error_code}: {message}")


class ShopeeAdapter:
    """Adapter for Shopee Open Platform API v2.

    Provides methods to read orders, products, analytics, returns, and
    update product listings. All methods return a standardized dict
    with 'success', 'data', and 'error' keys.

    Shopee API authentication uses HMAC-SHA256 request signing.
    """

    def __init__(
        self,
        partner_id: Optional[int] = None,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
        shop_id: Optional[int] = None,
        region: str = "my",
    ):
        self.partner_id = partner_id or int(os.environ.get("SHOPEE_PARTNER_ID", "0"))
        self.api_key = api_key or os.environ.get("SHOPEE_API_KEY", "")
        self.access_token = access_token or os.environ.get("SHOPEE_ACCESS_TOKEN", "")
        self.shop_id = shop_id or int(os.environ.get("SHOPEE_SHOP_ID", "0"))
        self.region = region.lower()

        if self.region not in SHOPEE_API_BASES:
            raise ShopeeError(f"Unknown region '{region}'. Valid: {', '.join(SHOPEE_API_BASES.keys())}")

        self.base_url = SHOPEE_API_BASES[self.region]

        if not self.partner_id:
            logger.warning("SHOPEE_PARTNER_ID is not set.")
        if not self.api_key:
            logger.warning("SHOPEE_API_KEY is not set.")
        if not self.access_token:
            logger.warning("SHOPEE_ACCESS_TOKEN is not set.")
        if not self.shop_id:
            logger.warning("SHOPEE_SHOP_ID is not set.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sign(self, path: str, timestamp: int, access_token: str = "") -> str:
        """Generate HMAC-SHA256 signature per Shopee auth spec.

        The signature is HMAC-SHA256 over:
            partner_id + path + timestamp + access_token + shop_id
        using the API key as the secret.
        """
        base_string = f"{self.partner_id}{path}{timestamp}{access_token}{self.shop_id}"
        sign = hmac.new(
            self.api_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return sign

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        """Make a signed Shopee API request.

        Returns:
            dict with keys: success (bool), data (any), error (str | None)
        """
        timestamp = int(time.time())
        full_path = f"{SHOPEE_API_VERSION}{path}"

        # Build query string with auth params
        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self.access_token,
            "shop_id": self.shop_id,
            "sign": self._sign(full_path, timestamp, self.access_token),
        }
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}{full_path}?{query_string}"

        data_bytes = None
        if body is not None:
            data_bytes = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data_bytes,
            method=method,
            headers={
                "Content-Type": "application/json",
            },
        )

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

        # Check Shopee-specific error response
        error_code = parsed.get("error")
        if error_code and error_code != 0:
            msg = parsed.get("message", "Unknown error")
            request_id = parsed.get("request_id")
            return {
                "success": False,
                "data": None,
                "error": f"Shopee error {error_code}: {msg} [request_id={request_id}]",
            }

        return {"success": True, "data": parsed.get("response", parsed), "error": None}

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> dict:
        """Verify connectivity to Shopee API by fetching shop info.

        Returns:
            Standardized dict with shop information.
        """
        result = self._request("GET", "/shop/get_shop_info")
        if result["success"]:
            logger.info("Shopee connected: shop_id=%s", self.shop_id)
        else:
            logger.error("Shopee connection failed: %s", result["error"])
        return result

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def read_orders(self, status: Optional[str] = None, since: Optional[str] = None) -> dict:
        """Read orders, optionally filtered by status and date.

        Args:
            status: Order status filter (e.g., 'READY_TO_SHIP', 'SHIPPED',
                    'COMPLETED', 'CANCELLED', 'IN_CANCEL').
            since: ISO date string (YYYY-MM-DD) to fetch orders from.

        Returns:
            Standardized dict with order records.
        """
        params = {"time_unit": "create_time"}
        if since:
            params["create_time_from"] = int(datetime.fromisoformat(since).timestamp())
            params["create_time_to"] = int(time.time())
        if status:
            params["order_status"] = status
        return self._request("GET", "/order/get_order_list", body=params)

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def read_products(self) -> dict:
        """Read all products in the shop.

        Returns:
            Standardized dict with product records.
        """
        return self._request("GET", "/product/get_item_list", body={
            "offset": 0,
            "page_size": 100,
        })

    # ------------------------------------------------------------------
    # Listings
    # ------------------------------------------------------------------

    def update_listing(self, product_data: dict) -> dict:
        """Update a product listing (price, stock, etc.).

        Args:
            product_data: Dict with fields to update. Expected structure:
                {
                    "item_id": int,
                    "price": float (optional),
                    "stock": int (optional),
                    "description": str (optional),
                    "variations": [{"variation_id": int, "price": float, "stock": int}] (optional),
                }

        Returns:
            Standardized dict with update result.
        """
        return self._request("POST", "/product/update_item", body=product_data)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def read_analytics(self, period: str = "this_month") -> dict:
        """Read shop analytics / performance data.

        Args:
            period: Time period ('today', 'this_week', 'this_month', 'last_month').

        Returns:
            Standardized dict with analytics data.
        """
        return self._request("GET", "/shop/performance", body={
            "period": period,
        })

    # ------------------------------------------------------------------
    # Returns / Refunds
    # ------------------------------------------------------------------

    def read_returns(self) -> dict:
        """Read return/refund requests.

        Returns:
            Standardized dict with return/refund records.
        """
        return self._request("GET", "/returns/get_return_list", body={
            "page_size": 50,
            "page_offset": 0,
        })


# ------------------------------------------------------------------
# Convenience helpers
# ------------------------------------------------------------------

def default_adapter(region: str = "my") -> ShopeeAdapter:
    """Create a ShopeeAdapter from environment variables."""
    return ShopeeAdapter(region=region)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python shopee_connector.py <command> [args]")
        print("Commands: connect, orders, products, update, analytics, returns, health")
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
            print("Usage: python shopee_connector.py update <json_file>")
            sys.exit(1)
        with open(sys.argv[2]) as f:
            data = json.load(f)
        result = adapter.update_listing(data)
        print(json.dumps(result, indent=2, default=str))

    elif command == "analytics":
        period = sys.argv[2] if len(sys.argv) > 2 else "this_month"
        result = adapter.read_analytics(period=period)
        print(json.dumps(result, indent=2, default=str))

    elif command == "returns":
        result = adapter.read_returns()
        print(json.dumps(result, indent=2, default=str))

    elif command == "health":
        result = adapter.connect()
        if result["success"]:
            print("✓ Shopee API connection is healthy")
        else:
            print(f"✗ Shopee API connection failed: {result['error']}")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)