#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
monthly_board.py — Monthly Financial Performance & Board Report generator.

Part of: skills/finance/monthly-board-report
Spec reference: TO-DO.md P2, finance-manager-ver1.md Component 2 §2

This script simulates the five-step acct_* data-gathering sequence that the
finance-manager profile (Koku) executes when asked for the monthly board report.
Step 4 calls the local variance.py script from bva-variance-analysis for the BvA
section — not a contract tool.

Usage (dry-run with sample data):
    python monthly_board.py --dry-run

Usage (live, requires acct_* tool wrappers to be importable):
    python monthly_board.py --month 2026-06 --output <path-to-save-report.md>

Sequence (per spec):
    Step 1: acct_get_profit_loss(last_month_start, last_month_end) → P&L
    Step 2: acct_get_balance_sheet(last_month_end) → Balance Sheet
    Step 3: acct_get_profit_loss(prior_month_start, prior_month_end) → MoM comparison
    Step 4: variance.py --budget finance/budget.json --actuals <Step1 PL JSON> → BvA
    Step 5: acct_list_contacts + acct_list_sales_invoices → concentration %

Output:
    Markdown-formatted "🏛️ MONTHLY FINANCIAL PERFORMANCE REPORT" board report.
    Optionally saves to the provided --output path.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from calendar import monthrange
from datetime import date
from typing import Optional


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def last_month_bounds(reference: Optional[date] = None) -> tuple[date, date]:
    """Return (start, end) of the month preceding reference (or today)."""
    ref = reference or date.today()
    first_of_ref = ref.replace(day=1)
    last_month_end = first_of_ref - __import__("datetime").timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    return last_month_start, last_month_end


def prior_month_bounds(reference: Optional[date] = None) -> tuple[date, date]:
    """Return (start, end) of two months before reference."""
    ref = reference or date.today()
    first_of_ref = ref.replace(day=1)
    last_month_end = first_of_ref - __import__("datetime").timedelta(days=1)
    prior_month_end = last_month_end.replace(day=1) - __import__("datetime").timedelta(days=1)
    prior_month_start = prior_month_end.replace(day=1)
    return prior_month_start, prior_month_end


# ---------------------------------------------------------------------------
# acct_* tool call stubs
# ---------------------------------------------------------------------------

def acct_get_profit_loss(date_from: date, date_to: date) -> dict:
    raise NotImplementedError(
        "acct_get_profit_loss is an MCP contract tool. "
        "Run with --dry-run for sample data."
    )


def acct_get_balance_sheet(as_of_date: date) -> dict:
    raise NotImplementedError(
        "acct_get_balance_sheet is an MCP contract tool. "
        "Run with --dry-run for sample data."
    )


def acct_list_contacts() -> dict:
    raise NotImplementedError(
        "acct_list_contacts is an MCP contract tool. "
        "Run with --dry-run for sample data."
    )


def acct_list_sales_invoices(date_from: date, date_to: date) -> dict:
    raise NotImplementedError(
        "acct_list_sales_invoices is an MCP contract tool. "
        "Run with --dry-run for sample data."
    )


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_PL_LAST = {
    "date_from": "2026-06-01",
    "date_to": "2026-06-30",
    "revenue": 124500.00,
    "cogs": 34860.00,
    "gross_profit": 89640.00,
    "opex": 54300.00,
    "net_profit": 35340.00,
    "ebitda": 38200.00,
    "lines": [
        {"account_code": "4000", "account_name": "SaaS Subscriptions", "actual_amount": 86000.00},
        {"account_code": "4001", "account_name": "Professional Services", "actual_amount": 38500.00},
        {"account_code": "5100", "account_name": "Payroll & Benefits", "actual_amount": 34000.00},
        {"account_code": "5200", "account_name": "SaaS & Cloud Infrastructure", "actual_amount": 11200.00},
        {"account_code": "5300", "account_name": "Marketing & Customer Acquisition", "actual_amount": 6500.00},
        {"account_code": "5400", "account_name": "Facilities & Admin", "actual_amount": 2600.00},
    ],
}

SAMPLE_PL_PRIOR = {
    "date_from": "2026-05-01",
    "date_to": "2026-05-31",
    "revenue": 115060.00,
    "cogs": 32200.00,
    "gross_profit": 82860.00,
    "opex": 51000.00,
    "net_profit": 31860.00,
    "ebitda": 34500.00,
    "lines": [],
}

SAMPLE_BS = {
    "as_of_date": "2026-06-30",
    "cash_and_bank": 262400.00,
    "accounts_receivable": 54100.00,
    "accounts_payable": 24800.00,
    "total_current_assets": 320000.00,
    "total_current_liabilities": 83300.00,
    "total_assets": 340000.00,
    "total_liabilities": 77600.00,
    "equity": 262400.00,
}

SAMPLE_INVOICES = {
    "invoices": [
        {"customer_id": "C001", "customer_name": "Customer A", "amount": 27900.00},
        {"customer_id": "C002", "customer_name": "Customer B", "amount": 31000.00},
        {"customer_id": "C003", "customer_name": "Customer C", "amount": 22000.00},
        {"customer_id": "C004", "customer_name": "Customer D", "amount": 43600.00},
    ],
    "total_revenue": 124500.00,
}

# Sample budget for BvA (mirrors finance/budget.json schema)
SAMPLE_BUDGET = {
    "period": "2026-06",
    "year": 2026,
    "lines": [
        {"account_code": "5100", "account_name": "Payroll & Benefits", "budget_amount": 34000.00},
        {"account_code": "5200", "account_name": "SaaS & Cloud Infrastructure", "budget_amount": 8500.00},
        {"account_code": "5300", "account_name": "Marketing & Customer Acquisition", "budget_amount": 8000.00},
        {"account_code": "5400", "account_name": "Facilities & Admin", "budget_amount": 2600.00},
    ],
}


# ---------------------------------------------------------------------------
# BvA section via variance.py
# ---------------------------------------------------------------------------

def compute_bva_section(pl_data: dict, budget_json_path: str, dry_run: bool) -> str:
    """
    Call variance.py to compute the BvA section.
    Returns the formatted BvA output string.
    Degrades gracefully if budget.json is absent.
    """
    variance_script = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "bva-variance-analysis",
        "scripts",
        "variance.py",
    )
    variance_script = os.path.normpath(variance_script)

    if dry_run:
        # Write sample budget and actuals to temp files
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as budget_tmp:
            json.dump(SAMPLE_BUDGET, budget_tmp)
            budget_path = budget_tmp.name

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as actuals_tmp:
            json.dump(pl_data, actuals_tmp)
            actuals_path = actuals_tmp.name
    else:
        budget_path = budget_json_path
        # Write Step 1 P&L to a temp file for variance.py
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as actuals_tmp:
            json.dump(pl_data, actuals_tmp)
            actuals_path = actuals_tmp.name


    try:
        import os as _os
        _env = _os.environ.copy()
        _env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, variance_script, "--budget", budget_path, "--actuals", actuals_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=_env,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            stderr = result.stderr.strip()
            return f"⚠️  BvA computation error: {stderr}"
        return output

    finally:
        if dry_run and os.path.exists(budget_path):
            os.unlink(budget_path)
        if os.path.exists(actuals_path):
            os.unlink(actuals_path)


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------

def fmt_money(amount: float) -> str:
    return f"${amount:,.2f}"


def fmt_pct(val: float, sign: bool = True) -> str:
    s = "+" if (sign and val >= 0) else ""
    return f"{s}{val:.1f}%"


def compute_concentration(invoices: dict) -> list[dict]:
    total = invoices.get("total_revenue", 1.0) or 1.0
    by_customer: dict[str, float] = {}
    for inv in invoices.get("invoices", []):
        cid = inv["customer_name"]
        by_customer[cid] = by_customer.get(cid, 0.0) + inv["amount"]
    rows = [
        {"name": name, "amount": amt, "pct": amt / total * 100}
        for name, amt in by_customer.items()
    ]
    rows.sort(key=lambda r: r["pct"], reverse=True)
    return rows


def compute_mom(current: float, prior: float) -> float:
    if prior == 0:
        return 0.0
    return (current - prior) / prior * 100


def compute_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compute_dso(ar: float, revenue: float, days: int) -> float:
    return (ar / revenue) * days if revenue else 0.0


def compute_dpo(ap: float, opex: float, days: int) -> float:
    return (ap / opex) * days if opex else 0.0


def format_report(
    pl_last: dict,
    bs: dict,
    pl_prior: dict,
    bva_section: str,
    invoices: dict,
    month_label: str,
) -> str:
    mom_revenue = compute_mom(pl_last["revenue"], pl_prior["revenue"])
    gross_margin_pct = (pl_last["gross_profit"] / pl_last["revenue"] * 100) if pl_last["revenue"] else 0
    net_margin_pct = (pl_last["net_profit"] / pl_last["revenue"] * 100) if pl_last["revenue"] else 0

    current_ratio = compute_ratio(bs["total_current_assets"], bs["total_current_liabilities"])
    quick_ratio = compute_ratio(bs["total_current_assets"] - 5000, bs["total_current_liabilities"])  # simplified: assume $5k inventory

    days_in_month = 30
    dso = compute_dso(bs["accounts_receivable"], pl_last["revenue"], days_in_month)
    dpo = compute_dpo(bs["accounts_payable"], pl_last["opex"], days_in_month)

    concentration = compute_concentration(invoices)

    lines = [
        f"🏛️ MONTHLY FINANCIAL PERFORMANCE REPORT — {month_label}",
        f"Prepared by: Koku (Finance Manager) | Source: QuickBooks Online & gbrain",
        "",
        "1. 🎯 Executive Summary & KPI Scorecard",
        f"   - Total Revenue: {fmt_money(pl_last['revenue'])} (MoM: {fmt_pct(mom_revenue)} {'📈' if mom_revenue >= 0 else '📉'})",
        f"   - Gross Profit: {fmt_money(pl_last['gross_profit'])} (Gross Margin: {gross_margin_pct:.1f}%)",
        f"   - Operating Expenses (OPEX): {fmt_money(pl_last['opex'])}",
        f"   - Net Profit: {fmt_money(pl_last['net_profit'])} (Net Margin: {net_margin_pct:.1f}%)",
        f"   - EBITDA: {fmt_money(pl_last.get('ebitda', pl_last['net_profit']))}",
        "",
        "2. 📑 Profit & Loss (P&L) Account Breakdown",
    ]

    revenue_lines = [l for l in pl_last.get("lines", []) if l["actual_amount"] > 0 and l["account_code"].startswith("4")]
    opex_lines = [l for l in pl_last.get("lines", []) if l["actual_amount"] > 0 and l["account_code"].startswith("5")]
    total_rev = pl_last["revenue"] or 1

    if revenue_lines:
        lines.append("   - Revenue Breakdown:")
        for l in revenue_lines:
            pct = l["actual_amount"] / total_rev * 100
            lines.append(f"     - {l['account_name']}: {fmt_money(l['actual_amount'])} ({pct:.1f}%)")
    if opex_lines:
        lines.append("   - OPEX Breakdown:")
        for l in opex_lines:
            lines.append(f"     - {l['account_name']}: {fmt_money(l['actual_amount'])}")

    lines += [
        "",
        "3. ⚖️ Balance Sheet & Financial Health Ratios",
        f"   - Cash Balance: {fmt_money(bs['cash_and_bank'])}",
        f"   - Accounts Receivable (AR): {fmt_money(bs['accounts_receivable'])}",
        f"   - Accounts Payable (AP): {fmt_money(bs['accounts_payable'])}",
        f"   - Current Ratio: {current_ratio:.2f}x ({'Healthy >1.5x' if current_ratio >= 1.5 else '⚠️ Below 1.5x'})",
        f"   - Quick Ratio: {quick_ratio:.2f}x ({'Healthy >1.0x' if quick_ratio >= 1.0 else '⚠️ Below 1.0x'})",
        "",
        "4. 📉 Budget vs. Actual (BvA) Variance Analysis",
        bva_section,
        "",
        "5. 🔍 Concentration Risk & Efficiency",
    ]

    top = concentration[0] if concentration else None
    if top:
        flag = " (⚠️ Above 20% risk threshold)" if top["pct"] > 20 else " (Within threshold)"
        lines.append(
            f"   - Top Client Concentration: {top['name']} accounts for "
            f"{top['pct']:.1f}% of {month_label} Revenue{flag}"
        )

    lines += [
        f"   - Days Sales Outstanding (DSO): {dso:.0f} Days",
        f"   - Days Payable Outstanding (DPO): {dpo:.0f} Days",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool, month_str: Optional[str], output_path: Optional[str], budget_path: str) -> None:
    if month_str:
        year, month = (int(x) for x in month_str.split("-"))
        ref_date = date(year, month, 1)
    else:
        ref_date = None

    lm_start, lm_end = last_month_bounds(ref_date)
    pm_start, pm_end = prior_month_bounds(ref_date)
    month_label = lm_end.strftime("%B %Y")

    if dry_run:
        pl_last = SAMPLE_PL_LAST
        pl_prior = SAMPLE_PL_PRIOR
        bs = SAMPLE_BS
        invoices = SAMPLE_INVOICES
    else:
        try:
            pl_last = acct_get_profit_loss(date_from=lm_start, date_to=lm_end)
            bs = acct_get_balance_sheet(as_of_date=lm_end)
            pl_prior = acct_get_profit_loss(date_from=pm_start, date_to=pm_end)
            contacts = acct_list_contacts()
            invoices = acct_list_sales_invoices(date_from=lm_start, date_to=lm_end)
        except NotImplementedError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print(
                "TIP: Run with --dry-run, or invoke via the finance-manager Hermes Agent profile.",
                file=sys.stderr,
            )
            sys.exit(1)

    bva_section = compute_bva_section(pl_last, budget_path, dry_run)
    report = format_report(pl_last, bs, pl_prior, bva_section, invoices, month_label)
    print(report)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n✅ Report saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the Monthly Financial Performance & Board Report (finance-manager skill)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use built-in sample data instead of calling live acct_* tools.",
    )
    parser.add_argument(
        "--month",
        default=None,
        help="Target month in YYYY-MM format (default: last completed calendar month).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the report as a markdown file.",
    )
    parser.add_argument(
        "--budget",
        default="finance/budget.json",
        help="Path to finance/budget.json from the gbrain finance source (default: finance/budget.json).",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run, month_str=args.month, output_path=args.output, budget_path=args.budget)


if __name__ == "__main__":
    main()
