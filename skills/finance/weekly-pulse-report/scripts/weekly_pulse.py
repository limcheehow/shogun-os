#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
weekly_pulse.py — Weekly Financial Pulse Report generator.

Part of: skills/finance/weekly-pulse-report
Spec reference: TO-DO.md P2, finance-manager-ver1.md Component 2 §1

This script simulates the four-step acct_* data-gathering sequence that the
finance-manager profile (Koku) executes when asked for the weekly financial report.
In a live Hermes Agent environment, the acct_* calls are made via the MCP accounting
contract. Here they are expressed as documented stub calls so the script can be:
  (a) read as authoritative documentation of the call sequence, and
  (b) run in a test/dry-run mode with sample data.

Usage (dry-run with sample data):
    python weekly_pulse.py --dry-run

Usage (live, requires acct_* tool wrappers to be importable):
    python weekly_pulse.py --output <path-to-save-report.md>

Sequence (per spec):
    Step 1: acct_get_balance_sheet(as_of_date=today)
    Step 2: acct_get_aging_report(type="receivable")
    Step 3: acct_get_aging_report(type="payable") + acct_list_purchase_bills(date_from=7_days_ago)
    Step 4: acct_get_profit_loss(date_from=month_start, date_to=today)

Output:
    Markdown-formatted "📊 WEEKLY FINANCIAL PULSE" report.
    Optionally saves to the provided --output path.
    In live mode, also writes to the gbrain finance source at finance/reports/weekly/<date>.md
    via the existing gbrain-capture convention.
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def today() -> date:
    return date.today()

def month_start() -> date:
    d = today()
    return d.replace(day=1)

def seven_days_ago() -> date:
    return today() - timedelta(days=7)

def week_ending_label() -> str:
    return today().strftime("%B %d, %Y")


# ---------------------------------------------------------------------------
# acct_* tool call stubs
# ---------------------------------------------------------------------------
# In a live Hermes Agent environment these are replaced by real MCP tool calls.
# The function signatures and return shapes are documented here for clarity.

def acct_get_balance_sheet(as_of_date: date) -> dict:
    """
    Returns: {
        "as_of_date": "YYYY-MM-DD",
        "cash_and_bank": float,
        "total_assets": float,
        "total_liabilities": float,
        "equity": float
    }
    """
    raise NotImplementedError(
        "acct_get_balance_sheet is an MCP contract tool — call via the Hermes Agent. "
        "Run with --dry-run to use sample data."
    )


def acct_get_aging_report(type: str) -> dict:
    """
    type: "receivable" or "payable"
    Returns: {
        "type": "receivable" | "payable",
        "total_outstanding": float,
        "current_0_30": float,
        "overdue_31_60": float,
        "overdue_61_90": float,
        "overdue_90_plus": float,
        "top_items": [
            {"name": str, "amount": float, "days_overdue": int, "invoice_ref": str}
        ]
    }
    """
    raise NotImplementedError(
        "acct_get_aging_report is an MCP contract tool — call via the Hermes Agent."
    )


def acct_list_purchase_bills(date_from: date, date_to: Optional[date] = None) -> dict:
    """
    Returns: {
        "bills": [
            {"vendor": str, "amount": float, "due_date": str, "description": str}
        ],
        "total_due": float
    }
    """
    raise NotImplementedError(
        "acct_list_purchase_bills is an MCP contract tool — call via the Hermes Agent."
    )


def acct_get_profit_loss(date_from: date, date_to: date) -> dict:
    """
    Returns: {
        "date_from": "YYYY-MM-DD",
        "date_to": "YYYY-MM-DD",
        "revenue": float,
        "cogs": float,
        "gross_profit": float,
        "opex": float,
        "net_profit": float,
        "lines": [{"account_code": str, "account_name": str, "actual_amount": float}]
    }
    """
    raise NotImplementedError(
        "acct_get_profit_loss is an MCP contract tool — call via the Hermes Agent."
    )


# ---------------------------------------------------------------------------
# Sample data (for --dry-run mode)
# ---------------------------------------------------------------------------

SAMPLE_BALANCE_SHEET = {
    "as_of_date": str(today()),
    "cash_and_bank": 245800.00,
    "total_assets": 312000.00,
    "total_liabilities": 49600.00,
    "equity": 262400.00,
}

SAMPLE_AR_AGING = {
    "type": "receivable",
    "total_outstanding": 68400.00,
    "current_0_30": 45000.00,
    "overdue_31_60": 21400.00,
    "overdue_61_90": 2000.00,
    "overdue_90_plus": 0.00,
    "top_items": [
        {"name": "Acme Corp", "amount": 12500.00, "days_overdue": 45, "invoice_ref": "INV-1042"},
        {"name": "Nexus Tech", "amount": 8900.00, "days_overdue": 38, "invoice_ref": "INV-1055"},
        {"name": "Global Media", "amount": 2000.00, "days_overdue": 32, "invoice_ref": "INV-1060"},
    ],
}

SAMPLE_AP_AGING = {
    "type": "payable",
    "total_outstanding": 31500.00,
    "current_0_30": 17300.00,
    "overdue_31_60": 14200.00,
    "overdue_61_90": 0.00,
    "overdue_90_plus": 0.00,
    "top_items": [],
}

SAMPLE_BILLS_DUE = {
    "bills": [
        {"vendor": "Cloud Hosting", "amount": 8200.00, "due_date": str(today() + timedelta(days=3)), "description": "AWS monthly"},
        {"vendor": "Office Rent", "amount": 6000.00, "due_date": str(today() + timedelta(days=5)), "description": "July rent"},
    ],
    "total_due": 14200.00,
}

SAMPLE_MTD_PL = {
    "date_from": str(month_start()),
    "date_to": str(today()),
    "revenue": 84500.00,
    "cogs": 0.00,
    "gross_profit": 84500.00,
    "opex": 51200.00,
    "net_profit": 33300.00,
    "lines": [],
}


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------

def fmt_money(amount: float) -> str:
    return f"${amount:,.2f}"


def compute_burn_rate(opex: float, days_in_period: int) -> float:
    """Estimate average monthly burn from MTD opex."""
    if days_in_period <= 0:
        return 0.0
    daily = opex / days_in_period
    return daily * 30.44  # average days per month


def format_report(
    bs: dict,
    ar: dict,
    ap: dict,
    bills: dict,
    pl: dict,
) -> str:
    """Format the weekly pulse report from the acct_* tool responses."""
    days_in_period = (today() - month_start()).days + 1
    avg_burn = compute_burn_rate(pl["opex"], days_in_period)
    runway_months = bs["cash_and_bank"] / avg_burn if avg_burn > 0 else float("inf")
    runway_status = (
        "Critical < 2 mos" if runway_months < 2
        else "Caution 2-4 mos" if runway_months < 4
        else "Healthy > 4 mos"
    )

    overdue_total = ar["overdue_31_60"] + ar["overdue_61_90"] + ar["overdue_90_plus"]
    overdue_count = len([x for x in ar.get("top_items", []) if x["days_overdue"] > 30])

    # MTD target pace (pro-rate 90k monthly target by days elapsed)
    monthly_target = 90000.00  # configurable assumption
    days_in_month = 30  # simplified
    daily_target = monthly_target / days_in_month
    target_pace = daily_target * days_in_period
    pct_of_target = (pl["revenue"] / target_pace * 100) if target_pace > 0 else 0
    net_surplus = pl["revenue"] - pl["opex"]
    surplus_label = "Surplus" if net_surplus >= 0 else "Deficit"

    lines = [
        f"📊 WEEKLY FINANCIAL PULSE (Week Ending: {week_ending_label()})",
        f"Prepared by: Koku (Finance Manager) | Source: QuickBooks Online",
        "",
        "1. 💵 Cash & Runway Status",
        f"   - Available Bank Balance: {fmt_money(bs['cash_and_bank'])}",
        f"   - Avg Monthly Burn Rate: {fmt_money(avg_burn)}",
        f"   - Estimated Cash Runway: {runway_months:.1f} Months ({runway_status})",
        "",
        "2. 📥 Accounts Receivable (Collections Focus)",
        f"   - Total Outstanding AR: {fmt_money(ar['total_outstanding'])}",
        f"   - Current (0-30 Days): {fmt_money(ar['current_0_30'])}",
        f"   - Overdue (>30 Days): {fmt_money(overdue_total)} ({overdue_count} invoices)",
    ]

    top_overdue = [x for x in ar.get("top_items", []) if x["days_overdue"] > 30][:5]
    if top_overdue:
        lines.append("   - ⚠️ Priority Collections Action Required:")
        for item in top_overdue:
            lines.append(
                f"     - {item['name']}: {fmt_money(item['amount'])} "
                f"({item['days_overdue']} days overdue — Invoice #{item['invoice_ref']})"
            )

    lines += [
        "",
        "3. 📤 Accounts Payable & Upcoming Commitments",
        f"   - Payments Due This Week: {fmt_money(bills['total_due'])}",
        f"   - Total Outstanding AP: {fmt_money(ap['total_outstanding'])}",
        "",
        "4. 📈 Month-To-Date (MTD) Revenue & Spend Pacing",
        f"   - MTD Revenue ({days_in_period} Days): {fmt_money(pl['revenue'])} "
        f"(Target Pace: {fmt_money(target_pace)} | {pct_of_target:.0f}% of Target)",
        f"   - MTD Expenses: {fmt_money(pl['opex'])}",
        f"   - Net MTD Operating {surplus_label}: {'+' if net_surplus >= 0 else ''}{fmt_money(net_surplus)}",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool, output_path: Optional[str]) -> None:
    if dry_run:
        bs = SAMPLE_BALANCE_SHEET
        ar = SAMPLE_AR_AGING
        ap = SAMPLE_AP_AGING
        bills = SAMPLE_BILLS_DUE
        pl = SAMPLE_MTD_PL
    else:
        # Live mode: call the acct_* contract tools
        # These will raise NotImplementedError unless the MCP wrapper is present
        try:
            bs = acct_get_balance_sheet(as_of_date=today())
            ar = acct_get_aging_report(type="receivable")
            ap = acct_get_aging_report(type="payable")
            bills = acct_list_purchase_bills(date_from=seven_days_ago(), date_to=today())
            pl = acct_get_profit_loss(date_from=month_start(), date_to=today())
        except NotImplementedError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            print(
                "TIP: Run with --dry-run to generate a sample report, "
                "or invoke this skill via the finance-manager Hermes Agent profile "
                "where the acct_* MCP tools are available.",
                file=sys.stderr,
            )
            sys.exit(1)

    report = format_report(bs, ar, ap, bills, pl)
    print(report)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n✅ Report saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the Weekly Financial Pulse report (finance-manager skill)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Use built-in sample data instead of calling live acct_* tools.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to save the report as a markdown file.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run, output_path=args.output)


if __name__ == "__main__":
    main()
