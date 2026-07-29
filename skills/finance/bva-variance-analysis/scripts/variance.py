#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
variance.py — BvA (Budget vs. Actual) variance computation script.

Part of: skills/finance/bva-variance-analysis
Spec reference: TO-DO.md P3-extra

Usage:
    python variance.py --budget <path-to-budget.json> --actuals <path-to-acct-pl.json>

Inputs:
    --budget   Path to finance/budget.json from the gbrain finance source.
               Expected schema:
               {
                 "period": "YYYY",
                 "year": 2026,
                 "lines": [
                   {
                     "account_code": "5000",
                     "account_name": "Payroll & Benefits",
                     "budget_amount": 34000.00,
                     "driver": "headcount × salary",
                     "notes": ""
                   },
                   ...
                 ]
               }

    --actuals  Path to the acct_get_profit_loss JSON output file.
               Expected schema (QuickBooks-style):
               {
                 "date_from": "YYYY-MM-DD",
                 "date_to": "YYYY-MM-DD",
                 "lines": [
                   {
                     "account_code": "5000",
                     "account_name": "Payroll & Benefits",
                     "actual_amount": 34000.00
                   },
                   ...
                 ]
               }

Output:
    Prints a markdown BvA table to stdout:
    | Account | Budget | Actual | Variance | Variance % | Flag |
    And exits with code 0.

    If budget.json is absent: prints a warning and exits 0 (graceful degradation).
    If actuals file is absent or malformed: prints an error and exits 1.

Constraints (from TO-DO.md):
    - No import of recipes.accounting.* — pure local computation.
    - Flags lines where abs(variance_pct) > 10 with "⚠️ >10% Variance".
    - Graceful degradation if budget.json is missing (exit 0, warning message).
"""

import argparse
import json
import os
import sys


VARIANCE_THRESHOLD_PCT = 10.0  # Spec-defined threshold: flag lines > 10% variance


def load_json(path: str, label: str) -> dict | None:
    """Load a JSON file. Returns None if file does not exist."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Could not read {label} at '{path}': {exc}", file=sys.stderr)
        sys.exit(1)


def build_actuals_index(actuals_data: dict) -> dict:
    """Build a dict keyed by account_code → actual_amount from the actuals payload."""
    index = {}
    for line in actuals_data.get("lines", []):
        code = str(line.get("account_code", "")).strip()
        amount = float(line.get("actual_amount", 0.0))
        if code:
            index[code] = {"actual_amount": amount, "account_name": line.get("account_name", code)}
    return index


def compute_variance(budget_amount: float, actual_amount: float) -> tuple[float, float]:
    """Return (variance_abs, variance_pct). variance = actual - budget."""
    variance_abs = actual_amount - budget_amount
    if budget_amount == 0.0:
        variance_pct = float("inf") if actual_amount != 0.0 else 0.0
    else:
        variance_pct = (variance_abs / budget_amount) * 100.0
    return variance_abs, variance_pct


def format_money(amount: float) -> str:
    return f"${amount:,.2f}"


def format_pct(pct: float) -> str:
    if pct == float("inf"):
        return "∞%"
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"


def run(budget_path: str, actuals_path: str) -> None:
    # --- Load budget (graceful degradation if missing) ---
    budget_data = load_json(budget_path, "budget.json")
    if budget_data is None:
        print(
            f"⚠️  BvA section unavailable — budget.json not found at '{budget_path}'.\n"
            "Author a budget via the budget-financial-modeling skill to enable BvA reporting."
        )
        sys.exit(0)

    # --- Load actuals (required) ---
    actuals_data = load_json(actuals_path, "actuals P&L JSON")
    if actuals_data is None:
        print(f"ERROR: Actuals file not found at '{actuals_path}'.", file=sys.stderr)
        sys.exit(1)

    actuals_index = build_actuals_index(actuals_data)
    budget_lines = budget_data.get("lines", [])

    if not budget_lines:
        print("⚠️  budget.json contains no budget lines. Nothing to compute.")
        sys.exit(0)

    # --- Compute variance per line ---
    period_label = budget_data.get("period", "Period")
    print(f"\n📉 Budget vs. Actual (BvA) Variance Analysis — {period_label}\n")
    print(f"{'Account':<40} {'Budget':>12} {'Actual':>12} {'Variance':>12} {'Var %':>10}  Flag")
    print("-" * 100)

    flagged_lines = []

    for line in budget_lines:
        code = str(line.get("account_code", "")).strip()
        name = line.get("account_name", code)
        budget_amt = float(line.get("budget_amount", 0.0))

        actual_entry = actuals_index.get(code)
        if actual_entry is None:
            # Account in budget not found in actuals — treat actual as 0
            actual_amt = 0.0
        else:
            actual_amt = actual_entry["actual_amount"]

        variance_abs, variance_pct = compute_variance(budget_amt, actual_amt)
        flag = ""
        if abs(variance_pct) > VARIANCE_THRESHOLD_PCT:
            flag = "⚠️ >10% Variance"
            flagged_lines.append(
                (name, budget_amt, actual_amt, variance_abs, variance_pct)
            )

        display_name = (name[:37] + "...") if len(name) > 40 else name
        print(
            f"{display_name:<40} {format_money(budget_amt):>12} {format_money(actual_amt):>12} "
            f"{format_money(variance_abs):>12} {format_pct(variance_pct):>10}  {flag}"
        )

    print("-" * 100)

    # --- Summary of flagged lines ---
    if flagged_lines:
        print(f"\n⚠️  Key Variances Exceeding {VARIANCE_THRESHOLD_PCT:.0f}% Threshold:\n")
        for name, budget_amt, actual_amt, variance_abs, variance_pct in flagged_lines:
            direction = "Unfavorable" if variance_abs > 0 else "Favorable"
            print(
                f"  • {name}: {format_money(actual_amt)} Actual vs "
                f"{format_money(budget_amt)} Budget "
                f"({format_pct(variance_pct)} Variance — {direction})"
            )
    else:
        print(f"\n✅  No lines exceed the {VARIANCE_THRESHOLD_PCT:.0f}% variance threshold.")

    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BvA variance computation script for the bva-variance-analysis skill."
    )
    parser.add_argument(
        "--budget",
        required=True,
        help="Path to finance/budget.json from the gbrain finance source.",
    )
    parser.add_argument(
        "--actuals",
        required=True,
        help="Path to the acct_get_profit_loss JSON output file.",
    )
    args = parser.parse_args()
    run(args.budget, args.actuals)


if __name__ == "__main__":
    main()
