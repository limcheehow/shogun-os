#!/usr/bin/env python3
"""
Odoo ERP Adapter — connects to Odoo via XML-RPC API.

Odoo is the most popular open-source ERP in Malaysia (SME to mid-market).
This adapter reads manufacturing orders, BOMs, inventory, and work centers.

Configure via env vars:
  ODOO_URL      — Odoo server URL (e.g. https://mycompany.odoo.com)
  ODOO_DB       — Odoo database name
  ODOO_USER     — Odoo username/email
  ODOO_PASSWORD — Odoo password or API key
  ODOO_TIMEOUT  — Request timeout in seconds (default: 30)

Usage:
    from erp_interface import get_adapter
    erp = get_adapter("odoo")
    erp.connect()
    orders = erp.read_work_orders()
"""
import os
import xmlrpc.client
from datetime import datetime
from typing import Optional
from erp_interface import ERPAdapter


class OdooAdapter(ERPAdapter):
    """Odoo XML-RPC adapter for manufacturing operations."""

    def __init__(self, url: str = "", db: str = "", user: str = "",
                 password: str = "", timeout: int = 30):
        self.url = url or os.environ.get("ODOO_URL", "")
        self.db = db or os.environ.get("ODOO_DB", "")
        self.user = user or os.environ.get("ODOO_USER", "")
        self.password = password or os.environ.get("ODOO_PASSWORD", "")
        self.timeout = int(os.environ.get("ODOO_TIMEOUT", str(timeout)))
        self.uid = None
        self._common = None
        self._object = None

    def _get_common(self):
        if not self._common:
            self._common = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/common", verbose=False,
                transport=xmlrpc.client.Transport(timeout=self.timeout)
            )
        return self._common

    def _get_object(self):
        if not self._object:
            self._object = xmlrpc.client.ServerProxy(
                f"{self.url}/xmlrpc/2/object", verbose=False,
                transport=xmlrpc.client.Transport(timeout=self.timeout)
            )
        return self._object

    def connect(self) -> bool:
        """Authenticate via XML-RPC common endpoint."""
        common = self._get_common()
        self.uid = common.authenticate(self.db, self.user, self.password, {})
        if not self.uid:
            raise ConnectionError(
                f"Odoo authentication failed for {self.user} on {self.db}"
            )
        return True

    def _search_read(self, model: str, domain: list, fields: list[str],
                     limit: int = 0, order: str = "") -> list[dict]:
        """Search and read records from an Odoo model."""
        obj = self._get_object()
        return obj.execute_kw(
            self.db, self.uid, self.password,
            model, 'search_read',
            [domain], {'fields': fields, 'limit': limit, 'order': order}
        )

    def read_work_orders(self, status: Optional[str] = None,
                         limit: int = 50, since: Optional[str] = None) -> list[dict]:
        """Read manufacturing orders from mrp.production."""
        domain = []
        if status:
            domain.append(("state", "=", status))
        if since:
            domain.append(("date_planned_start", ">=", since))

        records = self._search_read(
            "mrp.production", domain,
            ["name", "product_id", "product_qty", "state",
             "date_planned_start", "date_planned_finished",
             "priority", "user_id", "bom_id", "product_uom_id",
             "qty_produced", "qty_producing"],
            limit=limit, order="date_planned_start DESC"
        )
        return [self._format_work_order(r) for r in records]

    def _format_work_order(self, rec: dict) -> dict:
        return {
            "id": rec.get("id"),
            "name": rec.get("name", ""),
            "product": self._name(rec.get("product_id")),
            "product_id": rec.get("product_id") and rec["product_id"][0],
            "qty": rec.get("product_qty", 0),
            "qty_produced": rec.get("qty_produced", 0),
            "uom": self._name(rec.get("product_uom_id")),
            "state": rec.get("state", ""),
            "date_planned_start": rec.get("date_planned_start", ""),
            "date_planned_finished": rec.get("date_planned_finished", ""),
            "priority": rec.get("priority", "0"),
            "assigned_to": self._name(rec.get("user_id")),
        }

    def read_boms(self, product_id: Optional[str] = None) -> list[dict]:
        """Read Bills of Materials from mrp.bom."""
        domain = [("type", "=", "normal")]
        if product_id:
            domain.append(("product_id", "=", int(product_id)))

        records = self._search_read(
            "mrp.bom", domain,
            ["product_id", "product_qty", "product_uom_id",
             "bom_line_ids", "type", "routing_id", "code"],
            limit=50
        )
        result = []
        for rec in records:
            lines = self._search_read(
                "mrp.bom.line", [("bom_id", "=", rec["id"])],
                ["product_id", "product_qty", "product_uom_id"]
            )
            result.append({
                "id": rec.get("id"),
                "product": self._name(rec.get("product_id")),
                "qty": rec.get("product_qty", 0),
                "components": [
                    {"product": self._name(l.get("product_id")),
                     "qty": l.get("product_qty", 0),
                     "uom": self._name(l.get("product_uom_id"))}
                    for l in lines
                ],
            })
        return result

    def read_inventory(self, category: Optional[str] = None,
                       location: Optional[str] = None) -> list[dict]:
        """Read inventory levels from stock.quant."""
        domain = [("quantity", ">", 0)]
        if location:
            domain.append(("location_id", "=", int(location)))

        records = self._search_read(
            "stock.quant", domain,
            ["product_id", "quantity", "location_id",
             "product_uom_id", "in_date"],
            limit=200
        )
        return [self._format_inventory(r) for r in records]

    def _format_inventory(self, rec: dict) -> dict:
        return {
            "product_id": str(rec.get("product_id") and rec["product_id"][0] or ""),
            "product_name": self._name(rec.get("product_id")),
            "qty": rec.get("quantity", 0),
            "uom": self._name(rec.get("product_uom_id")),
            "location": self._name(rec.get("location_id")),
            "category": "",
            "value": 0,
        }

    def read_production_orders(self, status: Optional[str] = None,
                               limit: int = 50) -> list[dict]:
        """Read production orders."""
        domain = []
        if status:
            domain.append(("state", "=", status))

        records = self._search_read(
            "mrp.production", domain,
            ["name", "product_id", "product_qty", "state",
             "qty_produced", "routing_id", "workcenter_id",
             "date_planned_start", "priority"],
            limit=limit
        )
        return [{
            "id": r.get("id"),
            "name": r.get("name", ""),
            "product": self._name(r.get("product_id")),
            "qty_to_produce": r.get("product_qty", 0),
            "qty_produced": r.get("qty_produced", 0),
            "state": r.get("state", ""),
            "workcenter": self._name(r.get("workcenter_id")),
            "date_planned": r.get("date_planned_start", ""),
            "priority": r.get("priority", "0"),
        } for r in records]

    def read_workcenters(self) -> list[dict]:
        """Read work centers from mrp.workcenter."""
        records = self._search_read(
            "mrp.workcenter", [],
            ["name", "code", "capacity", "time_efficiency",
             "costs_hour", "active"],
            limit=100
        )
        return [{
            "id": r.get("id"),
            "name": r.get("name", ""),
            "code": r.get("code", ""),
            "capacity": r.get("capacity", 1),
            "efficiency": r.get("time_efficiency", 1),
            "cost_per_hour": r.get("costs_hour", 0),
            "active": r.get("active", True),
        } for r in records]

    def read_products(self, category: Optional[str] = None) -> list[dict]:
        """Read product catalog from product.product."""
        domain = [("sale_ok", "=", True)]
        if category:
            domain.append(("categ_id", "=", int(category)))

        records = self._search_read(
            "product.product", domain,
            ["name", "default_code", "categ_id", "uom_id",
             "list_price", "standard_price", "type"],
            limit=200
        )
        return [{
            "id": r.get("id"),
            "name": r.get("name", ""),
            "code": r.get("default_code", ""),
            "category": self._name(r.get("categ_id")),
            "uom": self._name(r.get("uom_id")),
            "list_price": r.get("list_price", 0),
            "cost": r.get("standard_price", 0),
            "type": r.get("type", ""),
        } for r in records]

    def update_work_order_status(self, order_id: str, new_state: str) -> bool:
        """Update a manufacturing order's state."""
        valid_states = ["draft", "confirmed", "in_progress", "done", "cancel"]
        if new_state not in valid_states:
            raise ValueError(f"Invalid state: {new_state}. Use: {valid_states}")

        obj = self._get_object()
        result = obj.execute_kw(
            self.db, self.uid, self.password,
            "mrp.production", "write",
            [[int(order_id)], {"state": new_state}]
        )
        return result

    @staticmethod
    def _name(tuple_val) -> str:
        """Extract name from Odoo tuple (id, name) or return empty string."""
        if isinstance(tuple_val, (list, tuple)) and len(tuple_val) >= 2:
            return str(tuple_val[1])
        return str(tuple_val) if tuple_val else ""
