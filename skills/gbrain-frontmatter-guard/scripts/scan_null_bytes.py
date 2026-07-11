#!/usr/bin/env python3
"""
Batch null-byte scanner for markdown files.

Scans a directory tree for markdown files (.md) containing null bytes (\x00),
which can corrupt git diffs, break YAML parsers, and silently truncate content.

Usage:
    python3 scan_null_bytes.py [--path <dir>] [--fix] [--git-only]

Options:
    --path <dir>    Directory to scan (default: current working directory)
    --fix           Strip null bytes in-place (backup via git first)
    --git-only      Only scan files tracked by git (skips untracked/ignored files)
    --json          Output as JSON for programmatic consumption

Exit code: 0 if clean, 1 if null bytes found (and --fix not used)
"""

import os
import sys
import subprocess
import json
import argparse


def get_git_tracked_files(root_dir):
    """Return set of tracked file paths relative to root_dir."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return set(result.stdout.strip().split("\n"))
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def scan(path, git_only=False, fix=False):
    """Scan for null bytes in markdown files. Return list of (path, count, before, after)."""
    results = []
    git_tracked = get_git_tracked_files(path) if git_only else None

    if git_tracked is not None:
        # Git mode: iterate tracked files
        candidates = []
        for rel_path in git_tracked:
            if not rel_path.endswith(".md") and not rel_path.endswith(".md"):
                continue
            full = os.path.join(path, rel_path)
            if os.path.isfile(full):
                candidates.append((rel_path, full))
    else:
        # Walk mode
        candidates = []
        for root, dirs, files in os.walk(path):
            if ".git" in dirs:
                dirs.remove(".git")
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                full = os.path.join(root, fname)
                rel = os.path.relpath(full, path)
                candidates.append((rel, full))

    for rel, full in candidates:
        try:
            with open(full, "rb") as fh:
                raw = fh.read()
        except OSError as e:
            print(f"  [ERROR] {rel}: {e}", file=sys.stderr)
            continue

        count = raw.count(b"\x00")
        if count == 0:
            continue

        before = len(raw)
        after = before - count

        if fix:
            cleaned = raw.replace(b"\x00", b"")
            try:
                with open(full, "wb") as fh:
                    fh.write(cleaned)
            except OSError as e:
                print(f"  [ERROR] Could not fix {rel}: {e}", file=sys.stderr)
                continue

        results.append((rel, count, before, after))

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Scan markdown files for null bytes that can corrupt git and YAML."
    )
    parser.add_argument("--path", default=".", help="Directory to scan (default: cwd)")
    parser.add_argument("--fix", action="store_true", help="Strip null bytes in-place")
    parser.add_argument(
        "--git-only", action="store_true", help="Only scan git-tracked files"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = scan(args.path, git_only=args.git_only, fix=args.fix)

    if args.json:
        print(json.dumps(results, indent=2))
        sys.exit(0 if not results else 1)

    if not results:
        print("No null bytes found.")
        sys.exit(0)

    total_bytes = sum(count for _, count, _, _ in results)
    print(f"Found null bytes in {len(results)} files ({total_bytes} total null bytes).")
    print()
    for rel, count, before, after in results:
        fix_mark = " --> FIXED" if args.fix else ""
        print(f"  {rel}: {count} null bytes ({before} -> {after} bytes){fix_mark}")

    if not args.fix:
        print()
        print("Run with --fix to strip null bytes in-place (recommended).")

    sys.exit(1 if not args.fix else 0)


if __name__ == "__main__":
    main()