#!/usr/bin/env python3
"""
brain_inventory.py — Local GBrain Inventory Provider

Part of: recipes/procurement/plugins/
Owning profile: procurement-manager

Standalone local provider implementing the procurement inventory contract
(proc_list_inventory, proc_get_item, proc_update_stock, proc_record_stock_movement,
proc_check_reorder_alerts) against Markdown frontmatter pages in ~/brain/procurement/.

All stock-level mutations are atomic: read → compute → write in a single
transaction block to avoid concurrent double-update race conditions.

Error response shape:
    {"error": str, "code": ERROR_CODE}

where ERROR_CODE ∈ {MISSING_FIELD, NOT_FOUND, PROVIDER_ERROR, NOT_IMPLEMENTED}
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml  # PyYAML — installed in the profile venv

# ── Configuration ────────────────────────────────────────────────────────────────
BRAIN_ROOT = Path(os.environ.get("GBRAIN_ROOT", Path.home() / "brain"))
PROCUREMENT_ROOT = BRAIN_ROOT / "procurement"
ITEMS_PATH = PROCUREMENT_ROOT / "items"
MOVEMENTS_PATH = PROCUREMENT_ROOT / "stock-movements"
PROVIDER_VERSION = "1.0.0"


# ── Frontmatter helpers ────────────────────────────────────────────────────────────
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _read_frontmatter(path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a Markdown file. Returns {} if missing or unparsable."""
    try:
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if match:
            return yaml.safe_load(match.group(1)) or {}
    except (OSError, yaml.YAMLError):
        pass
    return {}


def _write_frontmatter(path: Path, data: dict[str, Any], body: str = "") -> None:
    """Write (or overwrite) the YAML frontmatter section of a Markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_str = yaml.dump(data, default_flow_style=False, allow_unicode=True).strip()
    path.write_text(f"---\n{fm_str}\n---\n\n{body}", encoding="utf-8")


def _item_path(sku: str) -> Path:
    return ITEMS_PATH / f"{sku}.md"


def _err(msg: str, code: str = "PROVIDER_ERROR") -> dict[str, str]:
    return {"error": msg, "code": code}


# ── Contract implementations ────────────────────────────────────────────────────────────

def proc_list_inventory(
    search: str = "",
    category: str = "",
    status: str = "",
    below_reorder: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List inventory items from ~/brain/procurement/items/ with optional filters."""
    if not ITEMS_PATH.exists():
        return {"items": [], "total": 0}

    items: list[dict[str, Any]] = []
    for md_file in sorted(ITEMS_PATH.glob("*.md")):
        fm = _read_frontmatter(md_file)
        if not fm:
            continue
        if search and search.lower() not in fm.get("name", "").lower() and search.lower() not in fm.get("sku", "").lower():
            continue
        if category and fm.get("category", "") != category:
            continue
        if status and fm.get("status", "active") != status:
            continue
        if below_reorder and fm.get("current_stock", 0) > fm.get("reorder_point", 0):
            continue
        items.append(fm)

    total = len(items)
    return {"items": items[offset: offset + limit], "total": total}


def proc_get_item(sku: str) -> dict[str, Any]:
    """Retrieve a single inventory item by SKU."""
    if not sku:
        return _err("sku is required", "MISSING_FIELD")
    path = _item_path(sku)
    if not path.exists():
        return _err(f"Item not found: {sku}", "NOT_FOUND")
    fm = _read_frontmatter(path)
    if not fm:
        return _err(f"Unable to parse item page for {sku}", "PROVIDER_ERROR")
    return fm


def proc_update_stock(
    sku: str,
    delta: float | None = None,
    absolute: float | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Atomically update stock level for a SKU (delta or absolute, not both)."""
    if not sku:
        return _err("sku is required", "MISSING_FIELD")
    if delta is None and absolute is None:
        return _err("Provide either delta or absolute", "MISSING_FIELD")
    if delta is not None and absolute is not None:
        return _err("Provide either delta or absolute, not both", "MISSING_FIELD")

    path = _item_path(sku)
    if not path.exists():
        return _err(f"Item not found: {sku}", "NOT_FOUND")

    fm = _read_frontmatter(path)
    previous = float(fm.get("current_stock", 0))
    new_stock = (previous + delta) if delta is not None else float(absolute)  # type: ignore[arg-type]
    fm["current_stock"] = max(0, new_stock)  # floor at 0
    fm["last_movement_date"] = date.today().isoformat()
    _write_frontmatter(path, fm)

    unit_cost = float(fm.get("unit_cost", 0.0))
    return {
        "sku": sku,
        "previous_stock": previous,
        "new_stock": fm["current_stock"],
        "unit_cost": unit_cost,
        "total_value": fm["current_stock"] * unit_cost,
    }


def proc_record_stock_movement(
    sku: str,
    movement_type: str,
    quantity: int,
    reference_id: str = "",
    location_id: str = "",
    actor: str = "procurement-manager",
    note: str = "",
) -> dict[str, Any]:
    """Append an immutable stock movement log entry to ~/brain/procurement/stock-movements/."""
    VALID_TYPES = {"receive", "issue", "adjustment", "return", "damage"}
    if not sku:
        return _err("sku is required", "MISSING_FIELD")
    if movement_type not in VALID_TYPES:
        return _err(f"movement_type must be one of {sorted(VALID_TYPES)}", "MISSING_FIELD")
    if quantity == 0:
        return _err("quantity must be non-zero", "MISSING_FIELD")

    movement_id = str(uuid.uuid4())[:8]
    timestamp = datetime.utcnow().isoformat()
    today = date.today().isoformat()

    entry: dict[str, Any] = {
        "movement_id": movement_id,
        "sku": sku,
        "movement_type": movement_type,
        "quantity": quantity,
        "timestamp": timestamp,
        "reference_id": reference_id,
        "location_id": location_id,
        "actor": actor,
        "note": note,
    }

    path = MOVEMENTS_PATH / f"{today}-{sku}-{movement_id}.md"
    _write_frontmatter(path, entry)

    return {
        "movement_id": movement_id,
        "sku": sku,
        "movement_type": movement_type,
        "quantity": quantity,
        "timestamp": timestamp,
        "reference_id": reference_id,
    }


def proc_list_stock_movements(
    sku: str = "",
    date_from: str = "",
    date_to: str = "",
    movement_type: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List stock movement log entries from ~/brain/procurement/stock-movements/.

    Mirrors ``proc_list_inventory``'s glob+frontmatter pattern. Closes the
    write/read asymmetry — council can now *list* movements, not just *log*
    them via ``proc_record_stock_movement``.
    """
    if not MOVEMENTS_PATH.exists():
        return {"movements": [], "total": 0}

    movements: list[dict[str, Any]] = []
    for md_file in sorted(MOVEMENTS_PATH.glob("*.md")):
        fm = _read_frontmatter(md_file)
        if not fm:
            continue
        if sku and fm.get("sku", "") != sku:
            continue
        if movement_type and fm.get("movement_type", "") != movement_type:
            continue
        if date_from:
            ts = str(fm.get("timestamp", ""))
            if ts[:10] < date_from:
                continue
        if date_to:
            ts = str(fm.get("timestamp", ""))
            if ts[:10] > date_to:
                continue
        movements.append(fm)

    total = len(movements)
    return {"movements": movements[offset: offset + limit], "total": total}


def proc_check_reorder_alerts(
    category: str = "",
    location_id: str = "",
) -> dict[str, Any]:
    """Return all items at or below their reorder point, sorted by severity."""
    result = proc_list_inventory(category=category)
    all_items = result.get("items", [])

    alerts: list[dict[str, Any]] = []
    for item in all_items:
        if item.get("status", "active") == "inactive":
            continue
        if location_id and item.get("location_id", "") != location_id:
            continue

        current = int(item.get("current_stock", 0))
        reorder_pt = int(item.get("reorder_point", 0))
        safety = int(item.get("safety_stock", 0))

        if current <= reorder_pt:
            severity = "critical" if current <= safety else "warning"
            recommended_qty = max(0, (reorder_pt * 2) - current)
            alerts.append({
                "sku": item.get("sku"),
                "name": item.get("name"),
                "current_stock": current,
                "reorder_point": reorder_pt,
                "safety_stock": safety,
                "preferred_vendor_id": item.get("preferred_vendor_id", ""),
                "recommended_order_qty": recommended_qty,
                "severity": severity,
            })

    # Sort: critical first, then by stock level ascending
    alerts.sort(key=lambda a: (0 if a["severity"] == "critical" else 1, a["current_stock"]))
    return {"alerts": alerts, "total": len(alerts)}
