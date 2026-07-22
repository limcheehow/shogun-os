#!/usr/bin/env python3
"""
ERP Connector Interface — abstract base for all ERP adapters.
Each adapter (Odoo, ERPNext, SAP, etc.) implements this interface.

Usage:
    from erp_interface import get_adapter
    erp = get_adapter("odoo", url="https://mycompany.odoo.com", db="company",
                      user="admin", password="xxx")
    orders = erp.read_work_orders(status="in_progress")
    inventory = erp.read_inventory(category="raw_materials")
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class ERPAdapter(ABC):
    """Abstract interface for ERP system connectors."""

    @abstractmethod
    def connect(self) -> bool:
        """Authenticate and test connection. Returns True on success."""
        ...

    @abstractmethod
    def read_work_orders(self, status: Optional[str] = None,
                         limit: int = 50, since: Optional[str] = None) -> list[dict]:
        """
        Read manufacturing/work orders.
        Returns list of: {id, name, product, qty, state, date_planned_start,
                         date_planned_finished, priority, assigned_to}
        """
        ...

    @abstractmethod
    def read_boms(self, product_id: Optional[str] = None) -> list[dict]:
        """
        Read Bills of Materials.
        Returns list of: {id, product, qty, components: [{product, qty}], routing}
        """
        ...

    @abstractmethod
    def read_inventory(self, category: Optional[str] = None,
                       location: Optional[str] = None) -> list[dict]:
        """
        Read inventory/stock levels.
        Returns list of: {product_id, product_name, qty, uom, location,
                         category, value}
        """
        ...

    @abstractmethod
    def read_production_orders(self, status: Optional[str] = None,
                               limit: int = 50) -> list[dict]:
        """
        Read production orders.
        Returns list of: {id, name, product, qty_produced, qty_to_produce,
                         state, routing, workcenter}
        """
        ...

    @abstractmethod
    def read_workcenters(self) -> list[dict]:
        """
        Read work centers / machines.
        Returns list of: {id, name, code, capacity, efficiency, status}
        """
        ...

    @abstractmethod
    def update_work_order_status(self, order_id: str, new_state: str) -> bool:
        """Update a work order's state (draft/confirmed/in_progress/done/cancel)."""
        ...

    @abstractmethod
    def read_products(self, category: Optional[str] = None) -> list[dict]:
        """
        Read product catalog.
        Returns list of: {id, name, code, category, uom, list_price, cost}
        """
        ...

    def test_connection(self) -> dict:
        """Test ERP connection and return diagnostics."""
        try:
            ok = self.connect()
            if ok:
                orders = self.read_work_orders(limit=1)
                return {"status": "ok", "message": f"Connected. Sample: {len(orders)} orders"}
            return {"status": "error", "message": "Connection failed"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


def get_adapter(system: str, **kwargs) -> ERPAdapter:
    """Factory: returns the appropriate ERP adapter."""
    if system == "odoo":
        from odoo_connector import OdooAdapter
        return OdooAdapter(**kwargs)
    elif system == "erpnext":
        from erpnext_connector import ERPNextAdapter
        return ERPNextAdapter(**kwargs)
    elif system == "sap_b1":
        from sap_connector import SAPB1Adapter
        return SAPB1Adapter(**kwargs)
    else:
        raise ValueError(f"Unknown ERP system: {system}. Supported: odoo, erpnext, sap_b1")
