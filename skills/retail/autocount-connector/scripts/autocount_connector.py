"""
AutoCount AOTG API Connector for Shogun OS Retail Module.

Connects to AutoCount Online Transfer Gateway (AOTG) — Malaysia's most popular
SMB accounting software. Uses RESTful JSON API with API key authentication.

Environment Variables:
    AUTOCOUNT_API_URL     — Base URL of the AutoCount AOTG API (e.g., https://api.autocount.my/v1)
    AUTOCOUNT_API_KEY     — API key for authentication
    AUTOCOUNT_COMPANY_DB  — Target company database name in AutoCount
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("'requests' library not found. Install with: pip install requests")


class AutoCountError(Exception):
    """Base exception for AutoCount connector errors."""
    pass


class AutoCountAuthError(AutoCountError):
    """Authentication or authorization error."""
    pass


class AutoCountAPIError(AutoCountError):
    """API returned a non-success status code."""
    def __init__(self, status_code: int, message: str, response_body: Optional[str] = None):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"AutoCount API error {status_code}: {message}")


class AutoCountAdapter:
    """Adapter for AutoCount AOTG REST API.

    Provides methods to read and write accounting data: stock balances,
    sales invoices, debtor aging, purchase orders, and stock adjustments.
    All methods return a standardized dict with 'success', 'data', and 'error' keys.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        company_db: Optional[str] = None,
    ):
        self.api_url = (api_url or os.environ.get("AUTOCOUNT_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("AUTOCOUNT_API_KEY", "")
        self.company_db = company_db or os.environ.get("AUTOCOUNT_COMPANY_DB", "")
        self._session: Optional[requests.Session] = None

        if not self.api_url:
            logger.warning("AUTOCOUNT_API_URL is not set. Set it via env var or constructor.")
        if not self.api_key:
            logger.warning("AUTOCOUNT_API_KEY is not set. Set it via env var or constructor.")
        if not self.company_db:
            logger.warning("AUTOCOUNT_COMPANY_DB is not set. Set it via env var or constructor.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_session(self) -> "requests.Session":
        """Return or create a requests Session with auth headers."""
        if not HAS_REQUESTS:
            raise AutoCountError(
                "The 'requests' library is required. Install it with: pip install requests"
            )
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Company-DB": self.company_db,
            })
        return self._session

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make a JSON API request and return a standardized result dict.

        Returns:
            dict with keys: success (bool), data (any), error (str | None)
        """
        url = f"{self.api_url}{path}"
        session = self._get_session()

        try:
            resp = session.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
        except requests.exceptions.Timeout:
            return {"success": False, "data": None, "error": f"Request timed out: {method} {path}"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "data": None, "error": f"Connection error: {e}"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "data": None, "error": f"Request failed: {e}"}

        try:
            body = resp.json()
        except json.JSONDecodeError:
            body = resp.text

        if not resp.ok:
            msg = body.get("message") or body.get("error") or str(body) if isinstance(body, dict) else str(body)
            return {
                "success": False,
                "data": None,
                "error": f"HTTP {resp.status_code}: {msg}",
            }

        return {"success": True, "data": body, "error": None}

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> dict:
        """Verify connectivity to AutoCount AOTG API.

        Returns:
            Standardized dict. On success, data contains server info.
        """
        result = self._request("GET", "/system/info")
        if result["success"]:
            logger.info("AutoCount AOTG connected: %s", result["data"])
        else:
            logger.error("AutoCount AOTG connection failed: %s", result["error"])
        return result

    # ------------------------------------------------------------------
    # Stock / Inventory
    # ------------------------------------------------------------------

    def read_stock_balance(self, sku: Optional[str] = None) -> dict:
        """Read current stock balances, optionally filtered by SKU.

        Args:
            sku: Optional stock-keeping unit code to filter by.

        Returns:
            Standardized dict with stock balance records.
        """
        params = {}
        if sku:
            params["sku"] = sku
        return self._request("GET", "/stock/balance", params=params)

    # ------------------------------------------------------------------
    # Sales
    # ------------------------------------------------------------------

    def read_sales_invoices(self, since: Optional[str] = None) -> dict:
        """Read sales invoices, optionally filtered by date.

        Args:
            since: ISO date string (YYYY-MM-DD) to fetch invoices from.

        Returns:
            Standardized dict with sales invoice records.
        """
        params = {}
        if since:
            params["date_from"] = since
        return self._request("GET", "/sales/invoices", params=params)

    # ------------------------------------------------------------------
    # Debtors
    # ------------------------------------------------------------------

    def read_debtor_aging(self) -> dict:
        """Read debtor aging report.

        Returns:
            Standardized dict with debtor aging data grouped by aging bucket.
        """
        return self._request("GET", "/debtor/aging")

    # ------------------------------------------------------------------
    # Purchasing
    # ------------------------------------------------------------------

    def read_purchase_orders(self, status: Optional[str] = None) -> dict:
        """Read purchase orders, optionally filtered by status.

        Args:
            status: Optional status filter (e.g., 'Open', 'Pending', 'Completed').

        Returns:
            Standardized dict with purchase order records.
        """
        params = {}
        if status:
            params["status"] = status
        return self._request("GET", "/purchase/orders", params=params)

    # ------------------------------------------------------------------
    # Write Operations
    # ------------------------------------------------------------------

    def write_sales_invoice(self, data: dict) -> dict:
        """Create a new sales invoice in AutoCount.

        Args:
            data: Invoice payload as dict. Expected structure:
                {
                    "customer_code": str,
                    "date": "YYYY-MM-DD",
                    "items": [{"sku": str, "quantity": int, "unit_price": float}, ...],
                    "reference_no": str (optional),
                    "description": str (optional),
                }

        Returns:
            Standardized dict with the created invoice details.
        """
        return self._request("POST", "/sales/invoices", json=data)

    def write_stock_adjustment(self, data: dict) -> dict:
        """Post a stock adjustment/write-off in AutoCount.

        Args:
            data: Adjustment payload as dict. Expected structure:
                {
                    "date": "YYYY-MM-DD",
                    "items": [{"sku": str, "quantity": int, "reason": str}, ...],
                    "reference_no": str (optional),
                    "remarks": str (optional),
                }

        Returns:
            Standardized dict with the created adjustment details.
        """
        return self._request("POST", "/stock/adjustments", json=data)


# ------------------------------------------------------------------
# Convenience helpers
# ------------------------------------------------------------------

def default_adapter() -> AutoCountAdapter:
    """Create an AutoCountAdapter from environment variables."""
    return AutoCountAdapter()


def format_currency(amount: float) -> str:
    """Format a number as MYR currency string."""
    return f"RM {amount:,.2f}"


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    adapter = default_adapter()

    if len(sys.argv) < 2:
        print("Usage: python autocount_connector.py <command> [args]")
        print("Commands: connect, stock, invoices, aging, orders, health")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "connect":
        result = adapter.connect()
        print(json.dumps(result, indent=2))

    elif command == "stock":
        sku = sys.argv[2] if len(sys.argv) > 2 else None
        result = adapter.read_stock_balance(sku=sku)
        print(json.dumps(result, indent=2, default=str))

    elif command == "invoices":
        since = sys.argv[2] if len(sys.argv) > 2 else None
        result = adapter.read_sales_invoices(since=since)
        print(json.dumps(result, indent=2, default=str))

    elif command == "aging":
        result = adapter.read_debtor_aging()
        print(json.dumps(result, indent=2, default=str))

    elif command == "orders":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        result = adapter.read_purchase_orders(status=status)
        print(json.dumps(result, indent=2, default=str))

    elif command == "health":
        result = adapter.connect()
        if result["success"]:
            print("✓ AutoCount AOTG connection is healthy")
        else:
            print(f"✗ AutoCount AOTG connection failed: {result['error']}")
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)