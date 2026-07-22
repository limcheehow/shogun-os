#!/usr/bin/env python3
"""
Shogun OS — Cron Backup
────────────────────────
Exports all cron jobs from ~/.hermes/cron/jobs.json to a portable JSON file
that can be restored on a fresh Hermes install.

Usage:
  python3 scripts/backup-crons.py [output_file]

Examples:
  python3 scripts/backup-crons.py                         # default: ./cron-backup.json
  python3 scripts/backup-crons.py ~/cron-export-2026.json
  python3 scripts/backup-crons.py --profile hr-manager    # export profile-specific only
  python3 scripts/backup-crons.py --dry-run               # preview without writing
"""
import argparse
import json
import os
import sys
from datetime import datetime

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
JOBS_FILE = os.path.join(HERMES_HOME, "cron", "jobs.json")

EXPORTED_FIELDS = [
    "name",
    "schedule_display",
    "schedule",
    "prompt",
    "script",
    "no_agent",
    "skills",
    "enabled_toolsets",
    "deliver",
    "workdir",
    "model",
    "provider",
    "base_url",
    "context_from",
    "repeat",
]


def color(text, code):
    codes = {"green": "32", "cyan": "36", "yellow": "33", "red": "31"}
    c = codes.get(code, "0")
    return f"\033[{c}m{text}\033[0m"


def main():
    parser = argparse.ArgumentParser(
        description="Shogun OS — Cron Backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("output", nargs="?", default="cron-backup.json",
                        help="Output file path (default: ./cron-backup.json)")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview jobs that would be exported")
    args = parser.parse_args()

    if not os.path.exists(JOBS_FILE):
        print(f"{color('✗', 'red')} Cron jobs file not found: {JOBS_FILE}")
        sys.exit(1)

    with open(JOBS_FILE) as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    if not jobs:
        print(f"{color('⚠', 'yellow')} No cron jobs found in {JOBS_FILE}")
        sys.exit(0)

    # Extract portable subset
    exported = []
    skipped = 0
    for job in jobs:
        if not job.get("enabled", False) and not job.get("prompt") and not job.get("script"):
            skipped += 1
            continue

        entry = {}
        for field in EXPORTED_FIELDS:
            if field in job and job[field] is not None:
                entry[field] = job[field]

        # Add schedule_display as the primary schedule string
        if "schedule_display" in job and job["schedule_display"]:
            entry["schedule"] = job["schedule_display"]
        elif "schedule" in job:
            sched = job["schedule"]
            if isinstance(sched, dict) and "display" in sched:
                entry["schedule"] = sched["display"]
            elif isinstance(sched, dict) and "cron_expression" in sched:
                entry["schedule"] = sched["cron_expression"]

        exported.append(entry)

    if args.dry_run:
        print(f"\n{color('Cron Backup — Dry Run', 'cyan')}")
        print(f"  Source: {JOBS_FILE}")
        print(f"  Total jobs found: {len(jobs)}")
        print(f"  Jobs to export:   {len(exported)}")
        print(f"  Skipped (disabled): {skipped}")
        print()
        for i, entry in enumerate(exported, 1):
            name = entry.get("name", "(unnamed)")
            sched = entry.get("schedule", "?")
            is_script = bool(entry.get("script"))
            ptype = "no_agent" if is_script else "agent"
            print(f"  [{i:2d}] {name:<45} {sched:<25} {ptype}")
        print(f"\n  Would write to: {args.output}")
        return

    # Write export
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "source": JOBS_FILE,
        "total_jobs": len(jobs),
        "exported_count": len(exported),
        "skipped": skipped,
        "jobs": exported,
    }

    output_path = args.output
    with open(output_path, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"{color('✓', 'green')} Exported {len(exported)} cron jobs to {output_path}")
    print(f"  Source: {JOBS_FILE} ({len(jobs)} total, {skipped} skipped)")
    print(f"\n{color('→', 'cyan')} To restore: python3 scripts/restore-crons.py {output_path}")


if __name__ == "__main__":
    main()