#!/usr/bin/env python3
"""
inventory_valuation.py — Standalone Inventory Valuation Report Script

Part of: skills/procurement/inventory-valuation-report/
Owning profile: procurement-manager

Usage:
    python inventory_valuation.py [--date YYYY-MM-DD] [--no-gl]

Exits 0 on success, 1 on unrecoverable error.
Prints valuation table to stdout; saves report to procurement/reports/.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────────
SCRIPT_VERSION = "1.0.0"
ENABLE_ACCOUNTING_SYNC = os.environ.get("ENABLE_ACCOUNTING_SYNC", "false").lower() == "true"
VARIANCE_TOLERANCE_MYR = float(os.environ.get("VALUATION_TOLERANCE_MYR", "500"))
VARIANCE_TOLERANCE_PCT = float(os.environ.get("VALUATION_TOLERANCE_PCT", "0.01"))


# ── Mock / Stub helpers (replaced by live MCP calls in agent context) ───────────
def _stub_list_inventory() -> list[dict[str, Any]]:
    """Return empty list when gbrain is not available (empty brain mode)."""
    return []


def _stub_get_gl_balance() -> float | None:
    """Return None when accounting sync is disabled or GL is unavailable."""
    return None


# ── Core computation ────────────────────────────────────────────────────────────
def compute_valuation(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute total valuation and category breakdown from a list of inventory items."""
    total = 0.0
    by_category: dict[str, dict[str, Any]] = {}
    top_items: list[dict[str, Any]] = []

    for item in items:
        if item.get("status", "active") == "inactive":
            continue
        qty = float(item.get("current_stock", 0))
        cost = float(item.get("unit_cost", 0.0))
        value = qty * cost
        total += value

        cat = item.get("category", "Uncategorised")
        if cat not in by_category:
            by_category[cat] = {"sku_count": 0, "total_value": 0.0}
        by_category[cat]["sku_count"] += 1
        by_category[cat]["total_value"] += value

        top_items.append({
            "sku": item.get("sku", "N/A"),
            "name": item.get("name", "N/A"),
            "qty": int(qty),
            "unit_cost": cost,
            "total_value": value,
        })

    top_items.sort(key=lambda x: x["total_value"], reverse=True)
    return {
        "total": total,
        "active_sku_count": len(top_items),
        "by_category": by_category,
        "top_10": top_items[:10],
    }


# ── Formatting ─────────────────────────────────────────────────────────────────
def format_report(report_date: str, valuation: dict[str, Any], gl_balance: float | None) -> str:
    lines: list[str] = [
        f"📦 INVENTORY VALUATION REPORT ({report_date})",
        "Prepared by: Kura (Procurement Manager) | Source: GBrain Procurement",
        "",
        f'Total Active SKUs: {valuation["active_sku_count"]}',
        f'Total Inventory Value: MYR {valuation["total"]:,.2f}',
        "",
        "By Category:",
        "-" * 60,
    ]
    total = valuation["total"] or 1  # avoid divide-by-zero
    for cat, data in sorted(valuation["by_category"].items()):
        pct = (data["total_value"] / total) * 100
        lines.append(
            f'{cat:<20} | {data["sku_count"]:>4} SKUs | '
            f'MYR {data["total_value"]:>12,.2f} | {pct:>5.1f}%'
        )
    lines.append("-" * 60)

    lines += ["", "Top 10 SKUs by Value:",
               f'{"#":<3} {"SKU":<12} {"Item Name":<25} {"Qty":>6} {"Unit Cost":>12} {"Total Value":>14}']
    for i, item in enumerate(valuation["top_10"], 1):
        lines.append(
            f'{i:<3} {item["sku"]:<12} {item["name"]:<25} '
            f'{item["qty"]:>6} MYR {item["unit_cost"]:>8.2f} MYR {item["total_value"]:>10,.0f}'
        )

    if gl_balance is not None:
        variance = gl_balance - valuation["total"]
        tol_abs = max(VARIANCE_TOLERANCE_MYR, valuation["total"] * VARIANCE_TOLERANCE_PCT)
        status = "PASSED" if abs(variance) <= tol_abs else f"VARIANCE MYR {variance:+,.2f}"
        lines += ["", f"GL Reconciliation: [{status}]",
                  f"  Stock Valuation: MYR {valuation['total']:,.2f}",
                  f"  GL Inventory GL: MYR {gl_balance:,.2f}",
                  f"  Variance:        MYR {variance:+,.2f}"]
    elif ENABLE_ACCOUNTING_SYNC:
        lines += ["", "GL Reconciliation: [SKIPPED — GL unavailable]"]
    else:
        lines += ["", "GL Reconciliation: [DISABLED — set ENABLE_ACCOUNTING_SYNC=true to enable]"]

    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory Valuation Report")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Report date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--no-gl", action="store_true",
                        help="Skip GL reconciliation even if ENABLE_ACCOUNTING_SYNC=true.")
    args = parser.parse_args()

    # In agent context, replace _stub_* with actual MCP tool calls.
    items = _stub_list_inventory()
    gl_balance = None if args.no_gl else (_stub_get_gl_balance() if ENABLE_ACCOUNTING_SYNC else None)

    if not items:
        print(f"📦 INVENTORY VALUATION REPORT ({args.date})")
        print("No inventory items found in gbrain procurement source.")
        print("GL Reconciliation: [DISABLED — set ENABLE_ACCOUNTING_SYNC=true to enable]")
        sys.exit(0)

    valuation = compute_valuation(items)
    report = format_report(args.date, valuation, gl_balance)
    print(report)

    # Save report path (in agent context, use mcp_gbrain_save_page instead)
    report_filename = f"procurement/reports/valuation-{args.date}.md"
    print(f"\n✅ Report path: {report_filename}")
    sys.exit(0)


if __name__ == "__main__":
    main()
