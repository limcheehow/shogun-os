#!/usr/bin/env python3
"""
write_snapshots.py — Procurement dashboard snapshot writer.

Computes the 5-tab dashboard payload from the live procurement brain and writes
JSON-body gbrain pages to procurement/snapshots/*.json (see
recipes/DASHBOARD_SNAPSHOT_CONTRACT.md). Idempotent and empty-brain-safe.

Usage:
    python write_snapshots.py [--dry-run] [--brain-root DIR]

Standalone: reads ~/brain/procurement directly via the same glob+frontmatter
pattern the proc_* MCP tools use (recipes/procurement/plugins/brain_inventory.py).
When the procurement agent gateway is up, running this script (or the cron /
/refresh-procurement-dashboard slash trigger) keeps the dashboard on live data
instead of the examples/procurement-mock.json fallback.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

BRAIN_ROOT = Path(os.environ.get("GBRAIN_ROOT", Path.home() / "brain"))
PROCUREMENT_ROOT = BRAIN_ROOT / "procurement"
ITEMS_PATH = PROCUREMENT_ROOT / "items"
MOVEMENTS_PATH = PROCUREMENT_ROOT / "stock-movements"
POS_PATH = PROCUREMENT_ROOT / "purchase-orders"
VENDORS_PATH = PROCUREMENT_ROOT / "vendors"
REPORTS_PATH = PROCUREMENT_ROOT / "reports"
SNAPSHOTS_ROOT = PROCUREMENT_ROOT / "snapshots"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
THRESHOLD_MYR = 10_000


def _read_frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if match and yaml is not None:
            return yaml.safe_load(match.group(1)) or {}
    except (OSError, Exception):
        pass
    return {}


def _glob_fm(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    out: list[dict[str, Any]] = []
    for md in sorted(directory.glob("*.md")):
        fm = _read_frontmatter(md)
        if fm:
            out.append(fm)
    return out


def _safe_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _status_from_qty(qty: float, reorder: float) -> str:
    if qty <= 0:
        return "Out of Stock"
    if qty <= reorder:
        return "Low Stock"
    if qty > reorder * 4:
        return "Overstocked"
    return "In Stock"


def _build_inventory_snapshot(items: list[dict[str, Any]]) -> dict[str, Any]:
    valuation_by_cat: dict[str, float] = {}
    sku_catalog: list[dict[str, Any]] = []
    total_valuation = 0.0
    total_active = 0
    low_stock_alerts = 0
    dead_slow: list[dict[str, Any]] = []
    dead_slow_capital = 0.0
    bins: dict[str, dict[str, float]] = {}

    today = date.today()
    for fm in items:
        sku = str(fm.get("sku", ""))
        if not sku:
            continue
        name = str(fm.get("name", ""))
        category = str(fm.get("category", "Uncategorized"))
        unit_cost = _safe_float(fm.get("unit_cost"))
        qty = _safe_float(fm.get("current_stock"))
        reorder = _safe_float(fm.get("reorder_point"))
        location = str(fm.get("location_id", "") or fm.get("location_bin", ""))
        status = _status_from_qty(qty, reorder)
        total_active += 1
        value = qty * unit_cost
        total_valuation += value
        valuation_by_cat[category] = valuation_by_cat.get(category, 0.0) + value
        if qty <= reorder:
            low_stock_alerts += 1
        sku_catalog.append({
            "sku": sku,
            "item_name": name,
            "category": category,
            "unit_cost": unit_cost,
            "current_qty": qty,
            "safety_reorder_point": reorder,
            "location_bin": location,
            "status": status,
        })
        if location:
            b = bins.setdefault(location, {"used": 0.0, "capacity": 0.0})
            b["used"] += qty
            b["capacity"] = max(b["capacity"], _safe_float(fm.get("bin_capacity")))
        last_mv_raw = fm.get("last_movement_date", "")
        last_mv = last_mv_raw.isoformat()[:10] if hasattr(last_mv_raw, "isoformat") else str(last_mv_raw)[:10]
        days_no = (today - date.fromisoformat(last_mv)).days if last_mv else 9999
        months_cover = (qty / 30.0) if qty else 0.0  # crude default; agents override
        if days_no > 180 or months_cover > 8:
            tied = qty * unit_cost
            dead_slow_capital += tied
            rec = "Bundle Promo with Top SKU" if days_no > 180 else "25% Promo Discount"
            if days_no > 365:
                rec = "Scrap / Write-off"
            dead_slow.append({
                "sku": sku, "item_name": name, "category": category,
                "current_qty": qty, "days_since_last_movement": days_no,
                "months_of_cover": months_cover, "total_tied_value": tied,
                "action_recommendation": rec,
            })

    warehouse_bin = []
    for loc, b in bins.items():
        cap = b["capacity"] or max(b["used"] * 1.5, 100)
        util = (b["used"] / cap * 100.0) if cap else 0.0
        warehouse_bin.append({"location": loc, "used": b["used"], "capacity": cap, "utilisation_pct": util})

    risk_alerts: list[dict[str, Any]] = []
    for fm in items:
        qty = _safe_float(fm.get("current_stock"))
        reorder = _safe_float(fm.get("reorder_point"))
        safety = _safe_float(fm.get("safety_stock"))
        if qty <= safety:
            risk_alerts.append({"type": "safety_breach", "level": "critical",
                                "message": f"{fm.get('sku','')}: {qty} units below safety stock {safety}"})
    for d in dead_slow:
        risk_alerts.append({"type": "dead_stock", "level": "warning",
                            "message": f"{d['sku']}: {d['days_since_last_movement']}d no movement, RM {d['total_tied_value']:.0f} tied up"})

    return {
        "total_inventory_valuation": total_valuation,
        "total_active_skus": total_active,
        "low_stock_alerts": low_stock_alerts,
        "dead_slow_stock_capital": dead_slow_capital,
        "procurement_spend_mtd": 0.0,
        "procurement_spend_budget_mtd": 0.0,
        "valuation_by_category": [{"category": k, "value": v} for k, v in valuation_by_cat.items()],
        "sku_catalog": sku_catalog,
        "dead_slow_stock": dead_slow,
        "warehouse_bin_capacity": warehouse_bin,
        "spend_vs_budget_trend": [],
        "risk_alerts": risk_alerts,
    }


def _build_po_snapshot(pos: list[dict[str, Any]]) -> dict[str, Any]:
    pipeline_stage_counts: dict[str, int] = {}
    pipeline_stage_value: dict[str, float] = {}
    active: list[dict[str, Any]] = []
    approval_queue: list[dict[str, Any]] = []
    open_count = 0
    open_value = 0.0
    stage_order = ["Draft", "Pending Approval", "Issued to Vendor", "Partially Received", "Fully Received & Billed"]
    for fm in pos:
        po_num = str(fm.get("po_number", "") or fm.get("id", ""))
        vendor = str(fm.get("vendor", ""))
        order_date = str(fm.get("order_date", "") or fm.get("created_at", "")[:10])
        exp = str(fm.get("expected_delivery", "") or fm.get("expected_date", ""))
        total = _safe_float(fm.get("total_amount") or fm.get("amount"))
        fulfillment = str(fm.get("fulfillment_status", "Draft"))
        approval = str(fm.get("approval_status", "Pending Approval"))
        requester = str(fm.get("requester_dept", "") or fm.get("department", ""))
        stage = fulfillment if fulfillment in stage_order else "Draft"
        pipeline_stage_counts[stage] = pipeline_stage_counts.get(stage, 0) + 1
        pipeline_stage_value[stage] = pipeline_stage_value.get(stage, 0.0) + total
        if approval not in ("Cancelled", "Fully Billed"):
            open_count += 1
            open_value += total
            active.append({
                "po_number": po_num, "vendor": vendor, "order_date": order_date[:10],
                "expected_delivery": exp[:10], "total_amount": total,
                "fulfillment_status": fulfillment, "approval_status": approval,
            })
        if total > THRESHOLD_MYR:
            queue_status = str(fm.get("executive_status", "Pending Executive Approval"))
            approval_queue.append({
                "po_number": po_num, "vendor": vendor, "order_date": order_date[:10],
                "total_amount": total, "requester_dept": requester,
                "threshold_myr": THRESHOLD_MYR, "approval_status": queue_status,
            })
    pipeline = [{"stage": s, "count": pipeline_stage_counts.get(s, 0), "value": pipeline_stage_value.get(s, 0.0)} for s in stage_order]
    return {
        "open_po_count": open_count,
        "open_po_value": open_value,
        "po_pipeline": pipeline,
        "active_purchase_orders": active,
        "executive_approval_queue": approval_queue,
    }


def _build_vendor_snapshot(vendors: list[dict[str, Any]]) -> dict[str, Any]:
    scorecard: list[dict[str, Any]] = []
    concentration: list[dict[str, Any]] = []
    total_spend = sum(_safe_float(v.get("ytd_spend")) for v in vendors)
    for fm in vendors:
        name = str(fm.get("vendor") or fm.get("name", ""))
        spend = _safe_float(fm.get("ytd_spend"))
        on_time = _safe_float(fm.get("on_time_delivery_rate"))
        quality = _safe_float(fm.get("quality_acceptance_rate"))
        sla = str(fm.get("sla_status", "Satisfactory"))
        scorecard.append({
            "vendor": name, "preferred_category": str(fm.get("preferred_category", "")),
            "ytd_spend": spend, "on_time_delivery_rate": on_time,
            "quality_acceptance_rate": quality, "sla_status": sla,
        })
        if spend > 0:
            concentration.append({"vendor": name, "spend": spend,
                                  "spend_pct": (spend / total_spend * 100.0) if total_spend else 0.0})
    return {"vendor_scorecard": scorecard, "vendor_spend_concentration": concentration}


def _build_movement_snapshot(movements: list[dict[str, Any]]) -> dict[str, Any]:
    type_map: dict[str, str] = {"receive": "+ Receive", "issue": "- Issue", "adjustment": "~ Adjustment",
                                "return": "↺ Return", "damage": "! Damage"}
    out: list[dict[str, Any]] = []
    dist: dict[str, dict[str, int]] = {}
    shrinkage: list[str] = []
    for fm in movements:
        sku = str(fm.get("sku", ""))
        mtype_raw = str(fm.get("movement_type", "adjustment"))
        mtype = type_map.get(mtype_raw, "~ Adjustment")
        qty = _safe_float(fm.get("quantity"))
        out.append({
            "timestamp": str(fm.get("timestamp", "")), "sku": sku,
            "item_name": str(fm.get("item_name", "")), "movement_type": mtype,
            "quantity": qty, "reference_id": str(fm.get("reference_id", "")),
            "location_id": str(fm.get("location_id", "")), "actor": str(fm.get("actor", "")),
        })
        d = dist.setdefault(mtype, {"count": 0, "quantity": 0.0})
        d["count"] += 1
        d["quantity"] += qty
        if mtype_raw == "damage" or "shrinkage" in str(fm.get("note", "")).lower():
            if sku and sku not in shrinkage:
                shrinkage.append(sku)
    distribution = [{"movement_type": k, "count": v["count"], "quantity": v["quantity"]} for k, v in dist.items()]
    return {"stock_movements": out, "movement_type_distribution": distribution, "shrinkage_flag_items": shrinkage}


def _build_bridge_snapshot() -> dict[str, Any]:
    enabled = os.environ.get("ENABLE_ACCOUNTING_SYNC", "").lower() in ("1", "true", "yes")
    provider = os.environ.get("ACCT_PROVIDER", "None") or "None"
    last_sync = ""
    if REPORTS_PATH.exists():
        gl_files = sorted(REPORTS_PATH.glob("gl-sync-*.md"), reverse=True)
        for gf in gl_files:
            fm = _read_frontmatter(gf)
            ts = str(fm.get("timestamp") or fm.get("date") or "")
            if ts:
                last_sync = ts
                break
    connected = False
    if enabled:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "recipes" / "procurement" / "plugins"))
            from brain_inventory import _read_frontmatter as _rf  # noqa: F401
        except Exception:
            pass
        # Probe presence of accounting provider credentials as a soft proxy.
        connected = bool(os.environ.get("ACCT_PROVIDER"))
    return {
        "bridge_status": {
            "enabled": enabled, "provider": provider,
            "connected": connected, "last_sync": last_sync or None,
        },
        "po_bill_conversion_queue": [],
        "gl_valuation_reconciliation": [],
    }


def write_snapshot(path: Path, payload: dict[str, Any], dry_run: bool) -> None:
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    if dry_run:
        print(f"=== {path} ===\n{body}\n")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(body)} bytes)")


def main() -> int:
    global BRAIN_ROOT, PROCUREMENT_ROOT, ITEMS_PATH, MOVEMENTS_PATH, POS_PATH, VENDORS_PATH, REPORTS_PATH, SNAPSHOTS_ROOT  # noqa: PLW0603
    parser = argparse.ArgumentParser(description="Procurement dashboard snapshot writer")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without writing")
    parser.add_argument("--brain-root", default=None, help="Override brain root")
    args = parser.parse_args()

    brain_root = Path(args.brain_root) if args.brain_root else BRAIN_ROOT
    PROCUREMENT_ROOT = brain_root / "procurement"
    ITEMS_PATH = PROCUREMENT_ROOT / "items"
    MOVEMENTS_PATH = PROCUREMENT_ROOT / "stock-movements"
    POS_PATH = PROCUREMENT_ROOT / "purchase-orders"
    VENDORS_PATH = PROCUREMENT_ROOT / "vendors"
    REPORTS_PATH = PROCUREMENT_ROOT / "reports"
    SNAPSHOTS_ROOT = PROCUREMENT_ROOT / "snapshots"

    items = _glob_fm(ITEMS_PATH)
    pos = _glob_fm(POS_PATH)
    vendors = _glob_fm(VENDORS_PATH)
    movements = _glob_fm(MOVEMENTS_PATH)

    inv = _build_inventory_snapshot(items)
    po = _build_po_snapshot(pos)
    ven = _build_vendor_snapshot(vendors)
    mv = _build_movement_snapshot(movements)
    bridge = _build_bridge_snapshot()

    write_snapshot(SNAPSHOTS_ROOT / "inventory.json", inv, args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "purchase-orders.json", po, args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "vendors.json", ven, args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "stock-movements.json", mv, args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "accounting-bridge.json", bridge, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())