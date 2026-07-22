#!/usr/bin/env python3
"""
Shogun OS — Cron Restore
──────────────────────────
Restores cron jobs from a backup file created by backup-crons.py.
Creates jobs via hermes cron create.

Usage:
  python3 scripts/restore-crons.py <backup-file> [options]

Examples:
  python3 scripts/restore-crons.py cron-backup.json
  python3 scripts/restore-crons.py cron-backup.json --dry-run
  python3 scripts/restore-crons.py cron-backup.json --profile default
  python3 scripts/restore-crons.py cron-backup.json --overwrite-existing
"""
import argparse
import json
import os
import subprocess
import sys

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))


def color(text, code):
    codes = {"green": "32", "cyan": "36", "yellow": "33", "red": "31"}
    c = codes.get(code, "0")
    return f"\033[{c}m{text}\033[0m"


def run_hermes_cron_create(job, dry_run=False):
    """Build and run hermes cron create command for a single job."""
    name = job.get("name", "(unnamed)")
    schedule = job.get("schedule", "")
    prompt = job.get("prompt", "")
    script = job.get("script")
    skills = job.get("skills", [])
    deliver = job.get("deliver")
    workdir = job.get("workdir")
    model = job.get("model")
    provider = job.get("provider")
    enabled_toolsets = job.get("enabled_toolsets", [])
    repeat = job.get("repeat")
    context_from = job.get("context_from")

    if not schedule:
        print(f"  {color('⚠', 'yellow')} No schedule for job '{name}' — skipping")
        return False

    cmd = ["hermes", "cron", "create",
           "--name", name,
           "--schedule", schedule]

    if script:
        # no_agent job
        cmd.extend(["--script", script])
        cmd.append("--no-agent")
    elif prompt:
        # agent job
        cmd.append(f"--prompt")
        cmd.append(prompt)

    if skills:
        cmd.extend(["--skills", ",".join(skills)])

    if enabled_toolsets:
        cmd.extend(["--enabled-toolsets", ",".join(enabled_toolsets)])

    if deliver:
        cmd.extend(["--deliver", deliver])

    if workdir:
        cmd.extend(["--workdir", workdir])

    if model or provider:
        model_obj = {}
        if model:
            model_obj["model"] = model
        if provider:
            model_obj["provider"] = provider
        cmd.extend(["--model", json.dumps(model_obj)])

    if repeat:
        if isinstance(repeat, dict):
            times = repeat.get("times")
            if times:
                cmd.extend(["--repeat", str(times)])
        elif isinstance(repeat, str):
            cmd.extend(["--repeat", str(repeat)])

    if context_from:
        if isinstance(context_from, list):
            cmd.extend(["--context-from", ",".join(context_from)])
        else:
            cmd.extend(["--context-from", str(context_from)])

    if dry_run:
        print(f"  {color('→', 'cyan')} [DRY-RUN] {' '.join(cmd[:6])} ...")
        return True

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"  {color('✓', 'green')} Created: {name}")
            return True
        else:
            error = result.stderr.strip() or result.stdout.strip()
            print(f"  {color('✗', 'red')} Failed: {name}")
            print(f"     {error[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  {color('⚠', 'yellow')} Timeout: {name}")
        return False
    except FileNotFoundError:
        print(f"  {color('✗', 'red')} 'hermes' CLI not found — cannot create jobs")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Shogun OS — Cron Restore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("backup_file", help="Path to cron backup JSON file")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview jobs that would be created")
    parser.add_argument("--profile", "-p",
                        help="Only restore jobs matching this profile name in their delivery")
    args = parser.parse_args()

    if not os.path.exists(args.backup_file):
        print(f"{color('✗', 'red')} Backup file not found: {args.backup_file}")
        sys.exit(1)

    with open(args.backup_file) as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    if not jobs:
        print(f"{color('⚠', 'yellow')} No jobs found in backup file")
        sys.exit(0)

    print(f"\n{color('Cron Restore', 'cyan')}")
    print(f"  Backup:   {args.backup_file}")
    print(f"  Jobs:     {len(jobs)}")
    if args.dry_run:
        print(f"  Mode:     {color('DRY RUN — no changes', 'yellow')}")
    if args.profile:
        print(f"  Filter:   profile={args.profile}")
    print()

    # Filter by profile if specified
    if args.profile:
        filtered = []
        for job in jobs:
            deliver = job.get("deliver", "") or ""
            name = job.get("name", "")
            if args.profile.lower() in deliver.lower() or args.profile.lower() in name.lower():
                filtered.append(job)
        print(f"  Matching profile '{args.profile}': {len(filtered)} jobs")
        jobs = filtered

    # Confirm
    if not args.dry_run:
        print(f"{color('This will create or update {len(jobs)} cron jobs.', 'yellow')}")
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            print("Aborted.")
            sys.exit(0)

    # Restore
    success = 0
    failed = 0
    for job in jobs:
        if run_hermes_cron_create(job, dry_run=args.dry_run):
            success += 1
        else:
            failed += 1

    print()
    print(f"{color('═' * 50, 'cyan')}")
    print(f"  {color('Result:', 'green')} {success} created, {failed} failed")
    if args.dry_run:
        print(f"  {color('DRY RUN — No changes made', 'yellow')}")
    print(f"{color('═' * 50, 'cyan')}")

    return failed


if __name__ == "__main__":
    sys.exit(main())