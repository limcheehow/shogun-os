#!/usr/bin/env python3
"""
Company OS — Cron Wirer
────────────────────────
Generates and recommends cron jobs for a profile based on its type.

Usage:
  python3 scripts/wire-crons.py project-manager --type project-manager
  python3 scripts/wire-crons.py hr-manager --type hr --deliver telegram:-1001234567890
  python3 scripts/wire-crons.py finance --type finance --list
  python3 scripts/wire-crons.py project-manager --apply       # (requires hermes CLI)
══════════════════════════════════════════════════════════════════════════════

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

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))

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
            "name": "{profile}-budget-check",
            "schedule": "0 10 * * 1-5",
            "prompt": (
                "Run the daily budget check for the Finance team. "
                "Load the finance-budget-tracker skill, check department "
                "spending against budget, flag any departments approaching "
                "their limits, and summarise to the finance channel."
            ),
            "skills": [],
            "deliver": "local",
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
            "name": "{profile}-po-reminder",
            "schedule": "0 9 * * 1",
            "prompt": (
                "Run the weekly purchase order reminder. "
                "Check pending POs, flagged overdue orders, "
                "and post a summary to the procurement channel."
            ),
            "skills": [],
            "deliver": "local",
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

    return crons


def format_cron_commands(crons, deliver):
    """Format cron jobs as hermes CLI commands."""
    commands = []
    for cron in crons:
        cmd_parts = [
            "hermes cron create",
            f"--name \"{cron['name']}\"",
            f"--schedule \"{cron['schedule']}\"",
        ]
        if cron["skills"]:
            cmd_parts.append(f"--skills \"{','.join(cron['skills'])}\"")
        if deliver:
            cmd_parts.append(f"--deliver \"{deliver}\"")
        # Append the prompt as the positional argument
        cmd = " \\\n  ".join(cmd_parts) + f" \\\n  \"{cron['prompt']}\""
        commands.append(cmd)
    return commands


def apply_crons(crons, deliver, dry_run=False):
    """Apply cron jobs by running hermes cron create."""
    applied = 0
    failed = 0
    for cron in crons:
        cmd = ["hermes", "cron", "create",
               "--name", cron["name"],
               "--schedule", cron["schedule"]]
        if cron["skills"]:
            cmd.extend(["--skills", ",".join(cron["skills"])])
        if deliver:
            cmd.extend(["--deliver", deliver])
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
                print(f"     {result.stderr.strip()}")
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
        description="Company OS — Cron Wirer",
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
        commands = format_cron_commands(crons, args.deliver)
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
        applied, failed = apply_crons(crons, args.deliver, dry_run=args.dry_run)
        print(f"\nResult: {applied} applied, {failed} failed")
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