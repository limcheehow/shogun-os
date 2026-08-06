#!/usr/bin/env python3
"""
accounting_bridge.py — Procurement ↔ Accounting Integration Bridge

Part of: recipes/procurement/bridges/
Owning profile: procurement-manager

Links procurement events to finance-manager acct_* tools. All flows are
gated on ENABLE_ACCOUNTING_SYNC=true. When disabled, every function is a
no-op that returns a clear skip-reason message.

Trigger flows:
  1. PO-received → Purchase Bill (acct_create_purchase_bill)
  2. Inventory cost sync → GL valuation comparison (acct_get_balance_sheet)
  3. GL variance flag → alert posted to #procurement and #finance

Note: acct_* calls require the finance-manager MCP server to be reachable
from the procurement profile (GBRAIN_FEDERATED_READ=true).
"""
from __future__ import annotations

import os
from datetime import date
from typing import Any

# ── Configuration ────────────────────────────────────────────────────────────────
ENABLE_ACCOUNTING_SYNC: bool = os.environ.get("ENABLE_ACCOUNTING_SYNC", "false").lower() == "true"
VARIANCE_TOLERANCE_MYR: float = float(os.environ.get("VALUATION_TOLERANCE_MYR", "500"))
VARIANCE_TOLERANCE_PCT: float = float(os.environ.get("VALUATION_TOLERANCE_PCT", "0.01"))
BRIDGE_VERSION = "1.0.0"

_SKIP = {"status": "skipped", "reason": "ENABLE_ACCOUNTING_SYNC=false — accounting bridge is disabled"}


# ── Stub helpers (replaced by live MCP calls in agent context) ────────────────────
def _acct_list_purchase_bills(reference: str) -> dict[str, Any]:
    """Check if a bill for the given reference already exists."""
    # Replace with: mcp_tool_call("acct_list_purchase_bills", {"reference": reference})
    return {"bills": [], "total": 0}


def _acct_create_purchase_bill(
    vendor_id: str,
    bill_date: str,
    line_items: list[dict[str, Any]],
    reference: str,
) -> dict[str, Any]:
    """Create a supplier bill in the accounting system."""
    # Replace with: mcp_tool_call("acct_create_purchase_bill", {...})
    return {"id": "STUB-BILL", "status": "draft", "total": 0, "reference": reference}


def _acct_get_balance_sheet(as_of_date: str) -> dict[str, Any]:
    """Retrieve the GL balance sheet."""
    # Replace with: mcp_tool_call("acct_get_balance_sheet", {"as_of_date": as_of_date})
    return {"inventory_asset_balance": 0.0}


def _post_to_channels(message: str, channels: list[str]) -> None:
    """Post a message to one or more Slack channels."""
    # Replace with: department-scrum comm layer delivery
    for channel in channels:
        print(f"[BRIDGE] Post to {channel}: {message[:120]}...")


# ── Flow 1: PO-Received → Purchase Bill ─────────────────────────────────────────────────
def on_po_received(
    po_number: str,
    vendor_id: str,
    line_items: list[dict[str, Any]],
    received_date: str | None = None,
) -> dict[str, Any]:
    """
    Trigger: GRN recorded against a PO.
    Creates a Purchase Bill in the accounting system if ENABLE_ACCOUNTING_SYNC=true.

    Args:
        po_number: Reference PO number (used for duplicate-bill check).
        vendor_id: Vendor/supplier ID.
        line_items: List of {sku, description, quantity, unit_price}.
        received_date: ISO date of receipt. Defaults to today.

    Returns:
        Bill creation result or skip notice.
    """
    if not ENABLE_ACCOUNTING_SYNC:
        return _SKIP

    bill_date = received_date or date.today().isoformat()

    # Duplicate-bill guard
    existing = _acct_list_purchase_bills(reference=po_number)
    if existing.get("total", 0) > 0:
        return {
            "status": "skipped",
            "reason": f"Bill for PO {po_number} already exists",
            "existing_bill_id": existing["bills"][0].get("id"),
        }

    result = _acct_create_purchase_bill(
        vendor_id=vendor_id,
        bill_date=bill_date,
        line_items=line_items,
        reference=po_number,
    )
    return {"status": "created", "bill": result}


# ── Flow 2 & 3: Inventory cost sync + GL variance flag ──────────────────────────────
def sync_inventory_to_gl(
    stock_valuation: float,
    report_date: str | None = None,
) -> dict[str, Any]:
    """
    Trigger: Weekly inventory valuation run (Fri 5PM cron).
    Compares stock valuation to GL Inventory Asset balance.
    Posts a variance alert if the difference exceeds the tolerance threshold.

    Args:
        stock_valuation: Total stock value (sum of current_stock x unit_cost).
        report_date: ISO date for the GL snapshot. Defaults to today.

    Returns:
        Sync result including variance and pass/fail status.
    """
    if not ENABLE_ACCOUNTING_SYNC:
        return _SKIP

    as_of = report_date or date.today().isoformat()
    gl_data = _acct_get_balance_sheet(as_of_date=as_of)
    gl_balance = float(gl_data.get("inventory_asset_balance", 0.0))

    variance = gl_balance - stock_valuation
    tol_abs = max(VARIANCE_TOLERANCE_MYR, stock_valuation * VARIANCE_TOLERANCE_PCT)
    within_tolerance = abs(variance) <= tol_abs

    if not within_tolerance:
        _flag_gl_variance(stock_valuation, gl_balance, variance, as_of)

    return {
        "status": "passed" if within_tolerance else "variance_flagged",
        "stock_valuation": stock_valuation,
        "gl_balance": gl_balance,
        "variance": variance,
        "tolerance": tol_abs,
        "within_tolerance": within_tolerance,
        "report_date": as_of,
    }


# ── Flow 3: GL Variance Flag ───────────────────────────────────────────────────────────
def _flag_gl_variance(
    stock_val: float,
    gl_bal: float,
    variance: float,
    report_date: str,
) -> None:
    """Post a GL inventory variance alert to #procurement and #finance."""
    pct = (abs(variance) / max(stock_val, 1)) * 100
    message = (
        f"⚠️ GL INVENTORY VARIANCE DETECTED — {report_date}\n"
        f"Stock Valuation:  MYR {stock_val:,.2f}\n"
        f"GL Inventory GL:  MYR {gl_bal:,.2f}\n"
        f"Variance:         MYR {variance:+,.2f} ({pct:.1f}%)\n"
        f"Action: Review stock adjustments or GL journal for the period."
    )
    _post_to_channels(message, channels=["#procurement", "#finance"])
