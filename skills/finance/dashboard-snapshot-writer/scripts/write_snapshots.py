#!/usr/bin/env python3
"""
write_snapshots.py — Finance dashboard snapshot writer.

Computes the 5-tab dashboard payload from the live finance brain and writes
JSON-body gbrain pages to finance/snapshots/*.json (see
recipes/DASHBOARD_SNAPSHOT_CONTRACT.md). Idempotent and empty-brain-safe.

Usage:
    python write_snapshots.py [--dry-run] [--brain-root DIR]

Standalone: reads ~/brain/finance directly via the same glob+frontmatter
pattern the acct_* MCP tools use. When the finance agent gateway is up, running
this script (or the cron / /refresh-finance-dashboard slash trigger) keeps the
dashboard on live data instead of the examples/finance-budget.json fallback.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

BRAIN_ROOT = Path(os.environ.get("GBRAIN_ROOT", Path.home() / "brain"))
FINANCE_ROOT = BRAIN_ROOT / "finance"
BANK_PATH = FINANCE_ROOT / "bank-accounts"
INVOICES_PATH = FINANCE_ROOT / "sales-invoices"
BILLS_PATH = FINANCE_ROOT / "purchase-bills"
CONTACTS_PATH = FINANCE_ROOT / "contacts"
REPORTS_PATH = FINANCE_ROOT / "reports"
SNAPSHOTS_ROOT = FINANCE_ROOT / "snapshots"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


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


def _iso(v: Any) -> str:
    if hasattr(v, "isoformat"):
        return v.isoformat()[:10]
    return str(v)[:10]


def _build_cash_snapshot(banks: list[dict[str, Any]]) -> dict[str, Any]:
    bank_accounts = []
    total = 0.0
    for fm in banks:
        name = str(fm.get("name") or fm.get("bank", ""))
        bal = _safe_float(fm.get("balance"))
        currency = str(fm.get("currency", "MYR"))
        total += bal if currency == "MYR" else _safe_float(fm.get("myr_value", bal))
        bank_accounts.append({"name": name, "balance": bal, "currency": currency})
    return {
        "total_liquid_cash": total,
        "net_monthly_burn": 0.0,
        "cash_runway_months": 0.0,
        "fixed_opex": 0.0,
        "variable_opex": 0.0,
        "bank_accounts": bank_accounts,
        "fx_positions": [],
        "forecast_13w": {"conservative": [], "expected": [], "optimistic": []},
        "cash_flow_trend": [],
    }


def _build_pl_snapshot(invoices: list[dict[str, Any]], bills: list[dict[str, Any]]) -> dict[str, Any]:
    revenue_mtd = 0.0
    revenue_ytd = 0.0
    today = date.today()
    for fm in invoices:
        amt = _safe_float(fm.get("amount") or fm.get("total"))
        inv_date = _iso(fm.get("invoice_date") or fm.get("date"))
        if inv_date[:7] == today.isoformat()[:7]:
            revenue_mtd += amt
        if inv_date[:4] == str(today.year):
            revenue_ytd += amt
    opex = sum(_safe_float(b.get("amount")) for b in bills)
    gross_margin_pct = ((revenue_ytd - opex) / revenue_ytd * 100.0) if revenue_ytd else 0.0
    return {
        "revenue_mtd": revenue_mtd,
        "revenue_ytd": revenue_ytd,
        "gross_margin_pct": gross_margin_pct,
        "ebitda_margin_pct": gross_margin_pct,
        "unpaid_statutory": 0.0,
        "revenue_opex_trend": [],
    }


def _build_concentration_snapshot(contacts: list[dict[str, Any]], invoices: list[dict[str, Any]]) -> dict[str, Any]:
    spend_by_client: dict[str, float] = {}
    ytd: dict[str, float] = {}
    total = 0.0
    for fm in invoices:
        client = str(fm.get("client") or fm.get("customer", ""))
        amt = _safe_float(fm.get("amount") or fm.get("total"))
        spend_by_client[client] = spend_by_client.get(client, 0.0) + amt
        total += amt
    clients = []
    for name, rev in spend_by_client.items():
        pct = (rev / total * 100.0) if total else 0.0
        clients.append({"name": name, "revenue_pct": pct, "ytd_revenue": rev})
    clients.sort(key=lambda c: c["ytd_revenue"], reverse=True)
    return {"clients": clients}


def _build_bva_snapshot(budget: dict[str, Any], bills: list[dict[str, Any]]) -> dict[str, Any]:
    spend_by_dept: dict[str, float] = {}
    for fm in bills:
        dept = str(fm.get("department") or fm.get("dept", "Operations"))
        spend_by_dept[dept] = spend_by_dept.get(dept, 0.0) + _safe_float(fm.get("amount"))
    budget_depts = budget.get("departments", []) if isinstance(budget, dict) else []
    departments = []
    for b in budget_depts:
        dept = str(b.get("department", ""))
        budget_amt = _safe_float(b.get("budget") or b.get("amount"))
        actual = spend_by_dept.get(dept, 0.0)
        variance = actual - budget_amt
        variance_pct = (variance / budget_amt * 100.0) if budget_amt else 0.0
        departments.append({"department": dept, "variance_pct": variance_pct})
    return {
        "departments": departments,
        "unit_economics": {"gross_margin_pct": 0.0, "contribution_margin_pct": 0.0, "cac": 0.0, "ltv": 0.0, "ltv_cac_ratio": 0.0},
    }


def _build_ar_snapshot(invoices: list[dict[str, Any]]) -> dict[str, Any]:
    today = date.today()
    buckets = {"0_30": 0.0, "31_60": 0.0, "61_90": 0.0, "90_plus": 0.0}
    total_ar = 0.0
    dunning: list[dict[str, Any]] = []
    for fm in invoices:
        if str(fm.get("status", "")).lower() in ("paid", "settled"):
            continue
        amt = _safe_float(fm.get("amount") or fm.get("outstanding"))
        inv_date_str = _iso(fm.get("invoice_date") or fm.get("date"))
        try:
            inv_date = date.fromisoformat(inv_date_str)
        except ValueError:
            continue
        days = (today - inv_date).days
        total_ar += amt
        if days <= 30:
            buckets["0_30"] += amt
        elif days <= 60:
            buckets["31_60"] += amt
        elif days <= 90:
            buckets["61_90"] += amt
        else:
            buckets["90_plus"] += amt
            dunning.append({
                "invoice": str(fm.get("invoice_number") or fm.get("id", "")),
                "client": str(fm.get("client") or fm.get("customer", "")),
                "amount": amt, "days_overdue": days,
            })
    return {
        "total_ar": total_ar,
        "bucket_0_30": buckets["0_30"],
        "bucket_31_60": buckets["31_60"],
        "bucket_61_90": buckets["61_90"],
        "bucket_90_plus": buckets["90_plus"],
        "dso": 0.0,
        "dunning_queue": dunning,
    }


def _build_ap_snapshot(bills: list[dict[str, Any]]) -> dict[str, Any]:
    today = date.today()
    total_ap = 0.0
    overdue = 0.0
    out: list[dict[str, Any]] = []
    for fm in bills:
        amt = _safe_float(fm.get("amount"))
        total_ap += amt
        due = _iso(fm.get("due_date") or fm.get("date"))
        try:
            due_date = date.fromisoformat(due)
            if due_date < today:
                overdue += amt
        except ValueError:
            pass
        out.append({
            "bill": str(fm.get("bill_number") or fm.get("id", "")),
            "vendor": str(fm.get("vendor") or fm.get("supplier", "")),
            "amount": amt, "due_date": due,
        })
    return {"total_ap": total_ap, "ap_overdue": overdue, "dpo": 0.0, "bills": out}


def _build_compliance_snapshot() -> dict[str, Any]:
    return {
        "close_checklist": [],
        "statutory_schedule": [],
        "sst_readiness": {"draft_status": "pending", "taxable_sales": 0.0, "sst_liability": 0.0},
        "cp58_register": [],
        "wht_queue": [],
        "expense_claim_audit": [],
    }


def _load_budget() -> dict[str, Any]:
    budget_path = FINANCE_ROOT / "budget.json"
    if budget_path.exists():
        try:
            return json.loads(budget_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_snapshot(path: Path, payload: dict[str, Any], dry_run: bool) -> None:
    body = json.dumps(payload, indent=2, ensure_ascii=False)
    if dry_run:
        print(f"=== {path} ===\n{body}\n")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(body)} bytes)")


def main() -> int:
    global BRAIN_ROOT, FINANCE_ROOT, BANK_PATH, INVOICES_PATH, BILLS_PATH, CONTACTS_PATH, REPORTS_PATH, SNAPSHOTS_ROOT  # noqa: PLW0603
    parser = argparse.ArgumentParser(description="Finance dashboard snapshot writer")
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without writing")
    parser.add_argument("--brain-root", default=None, help="Override brain root")
    args = parser.parse_args()

    brain_root = Path(args.brain_root) if args.brain_root else BRAIN_ROOT
    FINANCE_ROOT = brain_root / "finance"
    BANK_PATH = FINANCE_ROOT / "bank-accounts"
    INVOICES_PATH = FINANCE_ROOT / "sales-invoices"
    BILLS_PATH = FINANCE_ROOT / "purchase-bills"
    CONTACTS_PATH = FINANCE_ROOT / "contacts"
    REPORTS_PATH = FINANCE_ROOT / "reports"
    SNAPSHOTS_ROOT = FINANCE_ROOT / "snapshots"

    banks = _glob_fm(BANK_PATH)
    invoices = _glob_fm(INVOICES_PATH)
    bills = _glob_fm(BILLS_PATH)
    contacts = _glob_fm(CONTACTS_PATH)
    budget = _load_budget()

    write_snapshot(SNAPSHOTS_ROOT / "cash.json", _build_cash_snapshot(banks), args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "pl.json", _build_pl_snapshot(invoices, bills), args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "concentration.json", _build_concentration_snapshot(contacts, invoices), args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "bva.json", _build_bva_snapshot(budget, bills), args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "ar.json", _build_ar_snapshot(invoices), args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "ap.json", _build_ap_snapshot(bills), args.dry_run)
    write_snapshot(SNAPSHOTS_ROOT / "compliance.json", _build_compliance_snapshot(), args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())