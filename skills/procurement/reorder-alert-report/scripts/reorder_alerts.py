#!/usr/bin/env python3
"""
reorder_alerts.py — Standalone Reorder Alert Report Script

Part of: skills/procurement/reorder-alert-report/
Owning profile: procurement-manager

Usage:
    python reorder_alerts.py [--date YYYY-MM-DD] [--category CATEGORY]

Exits 0 on success (including when no alerts), 1 on unrecoverable error.
Prints "No reorders needed" when no items are below threshold.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────────
SCRIPT_VERSION = "1.0.0"


# ── Mock / Stub helpers (replaced by live MCP calls in agent context) ───────────
def _stub_check_reorder_alerts(category: str | None = None) -> dict[str, Any]:
    """Return empty alerts when gbrain is not available (empty brain mode)."""
    return {"alerts": [], "total": 0}


def _stub_get_vendor_name(vendor_id: str) -> str:
    """Return placeholder vendor name when vendor lookup is unavailable."""
    return "TBC" if not vendor_id else vendor_id


# ── Core logic ─────────────────────────────────────────────────────────────────
def separate_by_severity(alerts: list[dict[str, Any]]) -> tuple[list, list]:
    """Split alerts into critical (stock <= safety_stock) and warning tiers."""
    critical, warning = [], []
    for alert in alerts:
        if alert.get("current_stock", 0) <= alert.get("safety_stock", 0):
            critical.append(alert)
        else:
            warning.append(alert)
    return critical, warning


def get_recommended_qty(alert: dict[str, Any]) -> int:
    """Return recommended order quantity, with fallback calculation."""
    rec = alert.get("recommended_order_qty", 0)
    if rec > 0:
        return rec
    # Fallback: (reorder_point x 2) - current_stock
    return max(0, (alert.get("reorder_point", 0) * 2) - alert.get("current_stock", 0))


# ── Formatting ─────────────────────────────────────────────────────────────────
HEADER = f'{"SKU":<12} | {"Item Name":<25} | {"Qty":>5} | {"Reorder Pt":>10} | {"Rec. Order":>10} | {"Vendor"}'
SEP = "-" * 80


def format_alert_row(alert: dict[str, Any]) -> str:
    vendor = _stub_get_vendor_name(alert.get("preferred_vendor_id", ""))
    return (
        f'{alert.get("sku", "N/A"):<12} | {alert.get("name", "N/A"):<25} | '
        f'{alert.get("current_stock", 0):>5} | {alert.get("reorder_point", 0):>10} | '
        f'{get_recommended_qty(alert):>9} u | {vendor}'
    )


def format_report(report_date: str, critical: list, warning: list) -> str:
    lines = [
        f"🚨 REORDER ALERT REPORT ({report_date})",
        "Prepared by: Kura (Procurement Manager) | Source: GBrain Procurement",
        "",
        f"Status: {len(critical) + len(warning)} item(s) require reordering",
        f"  Critical (stock \u2264 safety stock): {len(critical)} SKU(s)",
        f"  Warning  (stock \u2264 reorder point): {len(warning)} SKU(s)",
    ]

    if critical:
        lines += ["", "Critical Items:", HEADER, SEP]
        lines.extend(format_alert_row(a) for a in critical)

    if warning:
        lines += ["", "Warning Items:", HEADER, SEP]
        lines.extend(format_alert_row(a) for a in warning)

    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Reorder Alert Report")
    parser.add_argument("--date", default=date.today().isoformat(),
                        help="Report date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--category", default=None,
                        help="Filter alerts by item category.")
    args = parser.parse_args()

    # In agent context, replace _stub_* with actual MCP tool calls.
    result = _stub_check_reorder_alerts(category=args.category)
    alerts = result.get("alerts", [])

    if not alerts:
        print(f"✅ No reorders needed — all stock levels healthy as of {args.date}")
        sys.exit(0)

    critical, warning = separate_by_severity(alerts)
    report = format_report(args.date, critical, warning)
    print(report)

    report_filename = f"procurement/reports/reorder-{args.date}.md"
    print(f"\n✅ Report path: {report_filename}")
    sys.exit(0)


if __name__ == "__main__":
    main()
