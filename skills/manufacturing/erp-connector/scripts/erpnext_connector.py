#!/usr/bin/env python3
"""
ERPNext ERP Adapter — connects to ERPNext via Frappe REST API.

ERPNext is a popular open-source ERP in Asia (India, SE Asia, Middle East).
This adapter reads manufacturing orders, BOMs, inventory via REST API.

Configure via env vars:
  ERPNEXT_URL       — ERPNext site URL (e.g. https://mycompany.erpnext.com)
  ERPNEXT_API_KEY   — ERPNext API key
  ERPNEXT_SECRET    — ERPNext API secret
  ERPNEXT_TIMEOUT   — Request timeout in seconds (default: 30)

Usage:
    from erp_interface import get_adapter
    erp = get_adapter("erpnext")
    erp.connect()
    orders = erp.read_work_orders()
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional
from erp_interface import ERPAdapter


class ERPNextAdapter(ERPAdapter):
    """ERPNext REST API adapter for manufacturing operations."""

    def __init__(self, url: str = "", api_key: str = "",
                 secret: str = "", timeout: int = 30):
        self.url = url.rstrip("/") or os.environ.get("ERPNEXT_URL", "")
        self.api_key = api_key or os.environ.get("ERPNEXT_API_KEY", "")
        self.secret = secret or os.environ.get("ERPNEXT_SECRET", "")
        self.timeout = int(os.environ.get("ERPNEXT_TIMEOUT", str(timeout)))
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _auth_headers(self) -> dict:
        h = dict(self._headers)
        if self.api_key and self.secret:
            h["Authorization"] = f"token {self.api_key}:{self.secret}"
        return h

    def _request(self, method: str, path: str, data: dict = None) -> dict:
        url = f"{self.url}/api/{path.lstrip('/')}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=self._auth_headers(),
                                     method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()[:500]
            raise ConnectionError(f"ERPNext HTTP {e.code}: {err_body}")
        except urllib.error.URLError as e:
            raise ConnectionError(f"ERPNext connection failed: {e.reason}")

    def _get(self, resource: str, filters: dict = None,
             fields: list = None, limit: int = 50) -> list[dict]:
        """GET a Frappe REST resource."""
        params = f"?limit_page_length={limit}&limit_start=0"
        if fields:
            params += "&" + "&".join(f"fields=[{json.dumps(fields)}]")
        if filters:
            params += "&filters=" + json.dumps(filters).replace(" ", "")
        result = self._request("GET", f"resource/{resource}{params}")
        return result.get("data", [])

    def connect(self) -> bool:
        """Test connection by fetching the current user info."""
        try:
            self._request("GET", "method/frappe.auth.get_logged_user")
            return True
        except Exception as e:
            raise ConnectionError(f"ERPNext connection failed: {e}")

    def read_work_orders(self, status: Optional[str] = None,
                         limit: int = 50, since: Optional[str] = None) -> list[dict]:
        """Read Work Orders from ERPNext."""
        filters = {}
        if status:
            filters["status"] = status
        if since:
            filters["planned_start_date"] = [">=", since]

        records = self._get("Work Order", filters=filters, limit=limit)
        return [{
            "id": r.get("name"),
            "name": r.get("name", ""),
            "product": r.get("production_item", ""),
            "product_id": r.get("production_item", ""),
            "qty": r.get("qty", 0),
            "qty_produced": r.get("produced_qty", 0),
            "uom": r.get("stock_uom", ""),
            "state": r.get("status", "").lower(),
            "date_planned_start": r.get("planned_start_date", ""),
            "date_planned_finished": r.get("planned_end_date", ""),
            "priority": r.get("priority", "Medium"),
            "assigned_to": "",
        } for r in records]

    def read_boms(self, product_id: Optional[str] = None) -> list[dict]:
        """Read Bills of Materials from ERPNext."""
        filters = {"is_active": 1}
        if product_id:
            filters["item"] = product_id

        records = self._get("BOM", filters=filters, limit=50)
        result = []
        for rec in records:
            # Fetch BOM items (components)
            items = self._get("BOM Item",
                              filters={"parent": rec.get("name")},
                              limit=100)
            result.append({
                "id": rec.get("name"),
                "product": rec.get("item", ""),
                "qty": rec.get("quantity", 0),
                "components": [
                    {"product": i.get("item_code", ""),
                     "qty": i.get("qty", 0),
                     "uom": i.get("uom", "")}
                    for i in items
                ],
            })
        return result

    def read_inventory(self, category: Optional[str] = None,
                       location: Optional[str] = None) -> list[dict]:
        """Read inventory from ERPNext Bin or Stock Ledger."""
        filters = {}
        if location:
            filters["warehouse"] = location

        records = self._get("Bin", filters=filters,
                            fields=["item_code", "actual_qty", "warehouse",
                                    "stock_uom", "item_name"],
                            limit=200)
        return [{
            "product_id": r.get("item_code", ""),
            "product_name": r.get("item_name", r.get("item_code", "")),
            "qty": r.get("actual_qty", 0),
            "uom": r.get("stock_uom", ""),
            "location": r.get("warehouse", ""),
            "category": category or "",
            "value": 0,
        } for r in records]

    def read_production_orders(self, status: Optional[str] = None,
                               limit: int = 50) -> list[dict]:
        """Read production orders (same as work orders in ERPNext)."""
        return self.read_work_orders(status=status, limit=limit)

    def read_workcenters(self) -> list[dict]:
        """Read Workstations from ERPNext."""
        records = self._get("Workstation", limit=100)
        return [{
            "id": r.get("name"),
            "name": r.get("name", ""),
            "code": r.get("name", ""),
            "capacity": 1,
            "efficiency": r.get("hour_rate_electricity", 1) or 1,
            "cost_per_hour": r.get("hour_rate", 0),
            "active": True,
        } for r in records]

    def read_products(self, category: Optional[str] = None) -> list[dict]:
        """Read Item catalog from ERPNext."""
        filters = {"disabled": 0}
        if category:
            filters["item_group"] = category

        records = self._get("Item", filters=filters,
                            fields=["name", "item_name", "item_code",
                                    "item_group", "stock_uom",
                                    "valuation_rate", "standard_rate"],
                            limit=200)
        return [{
            "id": r.get("name"),
            "name": r.get("item_name", r.get("name", "")),
            "code": r.get("item_code", ""),
            "category": r.get("item_group", ""),
            "uom": r.get("stock_uom", ""),
            "list_price": r.get("standard_rate", 0),
            "cost": r.get("valuation_rate", 0),
            "type": "product",
        } for r in records]

    def update_work_order_status(self, order_id: str, new_state: str) -> bool:
        """Update a Work Order's status."""
        state_map = {
            "draft": "Draft", "confirmed": "Submitted",
            "in_progress": "In Process", "done": "Completed",
            "cancel": "Cancelled",
        }
        status = state_map.get(new_state, new_state)
        try:
            self._request("PUT", f"resource/Work Order/{order_id}",
                          {"status": status})
            return True
        except Exception:
            return False
