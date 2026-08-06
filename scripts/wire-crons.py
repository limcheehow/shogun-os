#!/usr/bin/env python3
"""
Shogun OS — Cron Wirer
────────────────────────
Generates and recommends cron jobs for a profile based on its type.

Usage:
  python scripts/wire-crons.py project-manager --type project-manager
  python scripts/wire-crons.py hr-manager --type hr --deliver telegram:-1001234567890
  python scripts/wire-crons.py finance --type finance --list
  python scripts/wire-crons.py project-manager --apply       # (requires hermes CLI)


Each profile type maps to a set of recommended cron jobs (scrum standups,
pipeline tasks, etc.). The wirer outputs YAML-ready cron specs or directly
creates them via the hermes CLI.

Profile types:
  base              Basic — scrum 9am/11am/5pm + holiday gate only
  hr                HR — scrum + daily leave summary
  finance           Finance — scrum + budget/reimbursement reminders
  project-manager   Project Manager — scrum + daily status check
  crm               CRM — scrum + pipeline check
  engineering       Engineering — scrum + deployment watch
  compliance        Compliance — scrum + audit reminders
  marketing         Marketing — scrum + campaign tasks
  procurement       Procurement — scrum + PO reminders
  product           Product — scrum + sprint reminders
  coding            Coding — scrum + PR reviews
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

# Resolve Hermes home (Windows Hermes uses AppData/Local/hermes, not ~/.hermes)
HERMES_HOME = os.environ.get("HERMES_HOME")
if not HERMES_HOME:
    default = os.path.expanduser("~/.hermes")
    if os.path.isdir(default):
        HERMES_HOME = default
    elif os.path.isdir(os.path.expanduser("~/AppData/Local/hermes")):
        HERMES_HOME = os.path.expanduser("~/AppData/Local/hermes")
    else:
        HERMES_HOME = default

# ── Cron job definitions per profile type ───────────────────────────────

SCRUM_CRONS = [
    {
        "name": "{profile}-scrum-morning",
        "schedule": "0 9 * * 1-5",
        "prompt": (
            "Run the morning scrum standup for the {profile} team. "
            "Load the department-scrum skill, read the scrum config at "
            "~/.hermes/profiles/{profile}/scrum.yaml, and send DMs "
            "requesting daily updates to each team member listed in the config. "
            "Collect any replies and summarise to the team channel."
        ),
        "skills": ["department-scrum"],
        "deliver": "local",
    },
    {
        "name": "{profile}-scrum-midday",
        "schedule": "0 11 * * 1-5",
        "prompt": (
            "Run the midday scrum check-in for the {profile} team. "
            "Load the department-scrum skill, check for outstanding replies "
            "from the morning standup, and send reminders to anyone who "
            "hasn't responded. Summarise blockers to the team channel."
        ),
        "skills": ["department-scrum"],
        "deliver": "local",
    },
    {
        "name": "{profile}-scrum-eod",
        "schedule": "0 17 * * 1-5",
        "prompt": (
            "Run the end-of-day scrum wrap-up for the {profile} team. "
            "Load the department-scrum skill, collect all responses from "
            "today's scrum, and post a summary to the team channel with "
            "completed tasks, blockers, and tomorrow's plan."
        ),
        "skills": ["department-scrum"],
        "deliver": "local",
    },
]

HOLIDAY_GATE = {
    "name": "{profile}-holiday-gate",
    "schedule": "0 6 * * 1-5",
    "prompt": (
        "Check if today is a public holiday. Load the department-scrum skill, "
        "read the holiday config, and skip today's scrum reminders if it's a "
        "holiday. Post a brief notification to the team channel if scrum is "
        "skipped."
    ),
    "skills": ["department-scrum"],
    "deliver": "local",
}

PROFILE_EXTRA_CRONS = {
    "hr": [
        {
            "name": "{profile}-leave-summary",
            "schedule": "0 8 * * 1-5",
            "prompt": (
                "Generate a daily leave summary for the HR team. "
                "Load the hr-leave-management skill, check leave balances "
                "and upcoming leave for all staff, and post a report to "
                "the HR channel with who's on leave today, who returns today, "
                "and any pending MC applications that need attention."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
    "finance": [
        {
            "name": "{profile}-daily-burn-rate",
            "schedule": "0 8 * * *",
            "prompt": (
                "Run daily burn rate and cash runway check for the Finance team. "
                "Load the cash-runway-forecasting skill, compute net monthly burn rate, "
                "cash runway months, and flag any liquidity risks."
            ),
            "skills": ["cash-runway-forecasting"],
            "deliver": "local",
        },
        {
            "name": "{profile}-invoice-aging",
            "schedule": "0 8 * * 1",
            "prompt": (
                "Run weekly Accounts Receivable invoice aging sweep. "
                "Load the ar-credit-control skill, audit 0-30/31-60/61-90/90+ buckets, "
                "build the dunning queue, and list priority collections."
            ),
            "skills": ["ar-credit-control"],
            "deliver": "local",
        },
        {
            "name": "{profile}-weekly-budget",
            "schedule": "0 8 * * 1",
            "prompt": (
                "Generate the Weekly Financial Pulse report. "
                "Load the weekly-pulse-report skill, gather cash balance, AR aging, "
                "AP commitments due, and MTD revenue & spend pacing, format executive report, "
                "and save to gbrain."
            ),
            "skills": ["weekly-pulse-report"],
            "deliver": "local",
        },
        {
            "name": "{profile}-monthly-pnl",
            "schedule": "0 8 1 * *",
            "prompt": (
                "Generate the Monthly Financial Performance & Board Report. "
                "Load the monthly-board-report skill, pull P&L breakdown, balance sheet ratios, "
                "run Budget vs. Actual (BvA) variance analysis, and customer concentration audit."
            ),
            "skills": ["monthly-board-report"],
            "deliver": "local",
        },
        {
            "name": "{profile}-dashboard-snapshot",
            "schedule": "0 7 * * *",
            "prompt": (
                "Run the dashboard-snapshot-writer skill to refresh the Finance dashboard with live system data. "
                "Compute the 5-tab payload from acct_* MCP tools and write JSON snapshots to "
                "finance/snapshots/*.json so the portal dashboard shows real data instead of mock. "
                "Idempotent and empty-brain-safe."
            ),
            "skills": ["dashboard-snapshot-writer"],
            "deliver": "local",
            "slash_trigger": "refresh-finance-dashboard",
        },
    ],
    "project-manager": [
        {
            "name": "{profile}-daily-status",
            "schedule": "30 9 * * 1-5",
            "prompt": (
                "Generate the daily project status report. "
                "Load the project-task-management skill, check active project "
                "tasks, flag overdue items and approaching deadlines, and "
                "post a concise status to the PM channel."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
    "crm": [
        {
            "name": "{profile}-pipeline-check",
            "schedule": "0 9 * * 1-5",
            "prompt": (
                "Run the daily CRM pipeline check. "
                "Load the crm-assistant skill, review open deals, flag "
                "stale opportunities and upcoming follow-ups, and post "
                "a pipeline health summary to the CRM channel."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
    "engineering": [
        {
            "name": "{profile}-deployment-check",
            "schedule": "0 9 * * 1-5",
            "prompt": (
                "Run the daily deployment status check. "
                "Check recent deployments, flag any failed or pending "
                "deployments, and post a summary to the engineering channel."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
    "compliance": [
        {
            "name": "{profile}-audit-reminder",
            "schedule": "0 10 * * 1",
            "prompt": (
                "Run the weekly compliance audit reminder. "
                "Check upcoming audit deadlines, outstanding compliance "
                "tasks, and post a summary to the compliance channel."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
    "marketing": [
        {
            "name": "{profile}-campaign-check",
            "schedule": "0 9 * * 1",
            "prompt": (
                "Run the weekly marketing campaign check. "
                "Review active campaigns, flag upcoming deadlines, "
                "and post a summary to the marketing channel."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
    "procurement": [
        {
            "name": "{profile}-reorder-watchdog",
            "schedule": "0 8 * * 1-5",
            "prompt": (
                "Run proc_check_reorder_alerts to scan all inventory items. "
                "Draft POs for items below reorder point grouped by preferred vendor. "
                "Post a prioritised reorder alert summary to #procurement."
            ),
            "skills": ["reorder-alert-watchdog"],
            "deliver": "local",
        },
        {
            "name": "{profile}-inventory-valuation",
            "schedule": "0 17 * * 5",
            "prompt": (
                "Compute total stock valuation (sum of current_stock x unit_cost for all active SKUs). "
                "If ENABLE_ACCOUNTING_SYNC is true, compare to the GL inventory asset balance "
                "and write a discrepancy report to procurement/reports/."
            ),
            "skills": ["procurement-provider", "accounting-bridge-sync"],
            "deliver": "local",
        },
        {
            "name": "{profile}-dashboard-snapshot",
            "schedule": "0 7 * * *",
            "prompt": (
                "Run the dashboard-snapshot-writer skill to refresh the Procurement dashboard with live system data. "
                "Compute the 5-tab payload from proc_* MCP tools and write JSON snapshots to "
                "procurement/snapshots/*.json so the portal dashboard shows real data instead of mock. "
                "Idempotent and empty-brain-safe."
            ),
            "skills": ["dashboard-snapshot-writer"],
            "deliver": "local",
            "slash_trigger": "refresh-procurement-dashboard",
        },
    ],
    "product": [
        {
            "name": "{profile}-sprint-reminder",
            "schedule": "0 9 * * 1",
            "prompt": (
                "Run the weekly sprint reminder. "
                "Check sprint progress, remaining tasks, and "
                "post a summary to the product channel."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
    "coding": [
        {
            "name": "{profile}-pr-review-reminder",
            "schedule": "0 10 * * 1-5",
            "prompt": (
                "Run the daily PR review reminder. "
                "Check open pull requests, flag any waiting for "
                "review, and post a summary to the engineering channel."
            ),
            "skills": [],
            "deliver": "local",
        },
    ],
}


def get_crons(profile_type, profile_name):
    """Get cron job list for a given profile type and name."""
    crons = []

    # Add scrum crons (all profiles get them)
    for cron in SCRUM_CRONS:
        entry = {k: (v.format(profile=profile_name) if isinstance(v, str) else v)
                 for k, v in cron.items()}
        crons.append(entry)

    # Add holiday gate
    entry = {k: (v.format(profile=profile_name) if isinstance(v, str) else v)
             for k, v in HOLIDAY_GATE.items()}
    crons.append(entry)

    # Add profile-specific extra crons
    extras = PROFILE_EXTRA_CRONS.get(profile_type, [])
    for cron in extras:
        entry = {k: (v.format(profile=profile_name) if isinstance(v, str) else v)
                 for k, v in cron.items()}
        crons.append(entry)

    # Substitute the resolved Hermes home (handles Windows AppData path)
    for cron in crons:
        if isinstance(cron.get("prompt"), str):
            cron["prompt"] = cron["prompt"].replace("~/.hermes", HERMES_HOME)

    return crons


def format_cron_commands(crons, deliver, profile_name):
    """Format cron jobs as hermes CLI commands (profile-scoped)."""
    commands = []
    for cron in crons:
        cmd_parts = [
            f"hermes -p {profile_name} cron create",
            f"--name \"{cron['name']}\"",
        ]
        if cron["skills"]:
            for s in cron["skills"]:
                cmd_parts.append(f"--skill \"{s}\"")
        if deliver:
            cmd_parts.append(f"--deliver \"{deliver}\"")
        # schedule and prompt are positional, at the end
        cmd = " \\\n  ".join(cmd_parts) + f" \\\n  \"{cron['schedule']}\" \\\n  \"{cron['prompt']}\""
        commands.append(cmd)
    return commands


def apply_crons(crons, deliver, profile_name, dry_run=False):
    """Apply cron jobs by running `hermes -p <profile> cron create`.

    Cron jobs are created in the named profile's cron database, not the
    active/default profile, so each department's jobs run with the right
    config, skills, GBrain source, and tokens.
    """
    applied = 0
    failed = 0
    for cron in crons:
        cmd = ["hermes", "-p", profile_name, "cron", "create", "--name", cron["name"]]
        if cron["skills"]:
            for s in cron["skills"]:
                cmd.extend(["--skill", s])
        if deliver:
            cmd.extend(["--deliver", deliver])
        # schedule is positional
        cmd.append(cron["schedule"])
        cmd.append(cron["prompt"])

        if dry_run:
            print(f"[DRY-RUN] {' '.join(cmd)}")
            applied += 1
            continue

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"  ✅ Created: {cron['name']}")
                applied += 1
            else:
                print(f"  ❌ Failed: {cron['name']}")
                # Capture both streams so real errors aren't hidden
                err_text = (result.stderr or result.stdout or "").strip()
                print(f"     {err_text}")
                failed += 1
        except subprocess.TimeoutExpired:
            print(f"  ⏱️  Timeout: {cron['name']}")
            failed += 1
        except FileNotFoundError:
            print("  ❌ 'hermes' CLI not found — cannot apply")
            return 0, len(crons)

    return applied, failed


def main():
    parser = argparse.ArgumentParser(
        description="Shogun OS — Cron Wirer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(__doc__ or "").split("═══════════════════════════════")[-1].strip(),
    )
    parser.add_argument("profile_name", help="Name of the Hermes profile")
    parser.add_argument("--type", "-t", default="base",
                        choices=list(PROFILE_EXTRA_CRONS.keys()) + ["base"],
                        help="Profile type (default: base)")
    parser.add_argument("--deliver", "-d", default="origin",
                        help="Cron delivery target (default: origin)")
    parser.add_argument("--list", action="store_true",
                        help="List recommended crons as hermes CLI commands")
    parser.add_argument("--apply", action="store_true",
                        help="Apply crons via hermes CLI (requires hermes installed)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview cron creation (implies --apply)")
    parser.add_argument("--output", "-o",
                        help="Write cron YAML specs to a file")

    args = parser.parse_args()

    crons = get_crons(args.type, args.profile_name)

    if args.list:
        print(f"\nRecommended cron jobs for \"{args.profile_name}\" ({args.type}):\n")
        commands = format_cron_commands(crons, args.deliver, args.profile_name)
        for i, cmd in enumerate(commands, 1):
            print(f"  [{i}] {cmd}")
            print()
        print(f"Total: {len(crons)} cron jobs")
        return

    if args.output:
        import yaml  # lazy import
        output = {
            "profile": args.profile_name,
            "type": args.type,
            "crons": crons,
        }
        with open(args.output, "w") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False)
        print(f"Wrote {len(crons)} cron specs to {args.output}")
        return

    if args.apply or args.dry_run:
        print(f"\nApplying {len(crons)} cron jobs for \"{args.profile_name}\" ({args.type})")
        if args.dry_run:
            print("[DRY RUN MODE — no changes will be made]\n")
        else:
            print()
        applied, failed = apply_crons(
            crons, args.deliver, args.profile_name, dry_run=args.dry_run
        )
        print(f"\nResult: {applied} applied, {failed} failed")
        if failed > 0:
            sys.exit(1)
        return

    # Default: show summary
    print(f"\nProfile: {args.profile_name} ({args.type})")
    print(f"Cron jobs: {len(crons)}")
    print()
    for i, cron in enumerate(crons, 1):
        print(f"  [{i}] {cron['name']}")
        print(f"       Schedule: {cron['schedule']}")
        print(f"       Skills:   {', '.join(cron['skills']) if cron['skills'] else 'none'}")
        print(f"       Deliver:  {args.deliver}")
        print(f"       Prompt:   {cron['prompt'][:80]}...")
        print()
    print(f"Run with --list to see CLI commands, --apply to create them")


if __name__ == "__main__":
    main()