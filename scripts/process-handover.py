#!/usr/bin/env python3
"""
process-handover.py — Process a pending handover.

Reviews, progresses gates, creates project, and moves to completed.

Usage:
    python3 process-handover.py --review "deals/acme-foo"
    python3 process-handover.py --gate 1 "deals/acme-foo"
    python3 process-handover.py --complete "deals/acme-foo"

Configure via env vars:
  BRAIN_DIR — brain root directory (default: ~/brain)
  HANDOVER_GATES — comma-separated gate definitions (default: G0:Deal Scoped,...)
"""
import os, sys, json, re, argparse
from pathlib import Path
from datetime import datetime, timezone

BRAIN_DIR = Path(os.environ.get("BRAIN_DIR", str(Path.home() / "brain")))
HANDOVERS_DIR = BRAIN_DIR / "handovers"
PENDING_DIR = HANDOVERS_DIR / "pending"
COMPLETED_DIR = HANDOVERS_DIR / "completed"
PROJECTS_DIR = BRAIN_DIR / "projects" / "active_projects"

DEFAULT_GATES_STR = os.environ.get(
    "HANDOVER_GATES",
    "G0:Deal Scoped,G1:Charter Signed,G2:Kick-off Complete,G3:Funding Cleared"
)


def parse_gates(gates_str: str) -> list[dict]:
    """Parse gate definitions from env var string."""
    gates = []
    for g in gates_str.split(","):
        g = g.strip()
        if ":" in g:
            key, name = g.split(":", 1)
            gates.append({"key": key.strip(), "name": name.strip()})
    return gates


GATES = parse_gates(DEFAULT_GATES_STR)


def find_handover(slug_or_file: str) -> Path | None:
    """Find a handover file by slug or filename."""
    slug_or_file = slug_or_file.replace(".md", "")
    # Try exact match in pending
    for f in PENDING_DIR.glob("*.md"):
        if slug_or_file in f.stem:
            return f
    # Try in completed
    for f in COMPLETED_DIR.glob("*.md"):
        if slug_or_file in f.stem:
            return f
    return None


def parse_frontmatter(text: str) -> dict:
    """Simple YAML frontmatter parser."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    fm = text[3:end]
    result = {}
    for line in fm.split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def update_frontmatter(text: str, updates: dict) -> str:
    """Update specific frontmatter fields."""
    for key, value in updates.items():
        pattern = rf"^({key}:).*$"
        replacement = f"\\1 {value}"
        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
    return text


def review_handover(filepath: Path) -> dict:
    """Review a handover and return its details."""
    content = filepath.read_text(encoding="utf-8")
    fm = parse_frontmatter(content)

    # Extract customer from title
    title = fm.get("title", "")
    customer = title.split("—")[0].strip() if "—" in title else title

    current_gate = int(fm.get("gate", "0"))
    gate_status = fm.get("gate_status", "gated")

    result = {
        "handover_file": str(filepath),
        "customer": customer,
        "deal": fm.get("source_deal", ""),
        "source": fm.get("source", ""),
        "created": fm.get("created", ""),
        "current_gate": current_gate,
        "gate_status": gate_status,
        "status": fm.get("status", "pending"),
        "gates": [],
    }

    for i, gate in enumerate(GATES):
        gate_key = f"gate_{i}_status"
        gate_status_field = "done" if current_gate > i else ("gated" if current_gate == i else "locked")
        result["gates"].append({
            "key": gate["key"],
            "name": gate["name"],
            "status": gate_status_field,
        })

    return result


def progress_gate(filepath: Path, target_gate: int) -> dict:
    """Progress a handover to the next gate."""
    content = filepath.read_text(encoding="utf-8")
    fm = parse_frontmatter(content)

    current_gate = int(fm.get("gate", "0"))
    current_status = fm.get("gate_status", "gated")

    if target_gate <= current_gate:
        return {"success": False, "error": f"Gate {target_gate} is already at or past current gate {current_gate}"}

    if target_gate > len(GATES):
        return {"success": False, "error": f"Gate {target_gate} exceeds max gate {len(GATES) - 1}"}

    updates = {
        "gate": str(target_gate),
        "gate_status": "gated",
    }
    new_content = update_frontmatter(content, updates)
    filepath.write_text(new_content, encoding="utf-8")

    gate_name = GATES[target_gate]["name"] if target_gate < len(GATES) else "Complete"
    return {
        "success": True,
        "handover": str(filepath),
        "previous_gate": current_gate,
        "new_gate": target_gate,
        "gate_name": gate_name,
        "message": f"✅ Gate {target_gate} ({gate_name}) approved.",
    }


def complete_handover(filepath: Path) -> dict:
    """Complete a handover — move to completed, create project."""
    # Move to completed
    COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
    dest = COMPLETED_DIR / filepath.name

    content = filepath.read_text(encoding="utf-8")
    new_content = update_frontmatter(content, {
        "status": "completed",
        "gate": str(len(GATES)),
        "gate_status": "passed",
    })
    dest.write_text(new_content, encoding="utf-8")
    os.chmod(dest, 0o664)

    # Remove from pending
    filepath.unlink()

    # Create project stub
    fm = parse_frontmatter(content)
    title = fm.get("title", "Project")
    project_slug = "PRJ-" + re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:30]

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    project_file = PROJECTS_DIR / f"{project_slug}.md"
    if not project_file.exists():
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        project_content = f"""---
title: "{title}"
type: project
status: active
created: {today}
source: handover
handover: "{fm.get('source_deal', '')}"
---

# {title}

> Project created from handover: {fm.get('source_deal', '')}

## Overview

{title}

## Timeline

| Date | Event |
|------|-------|
| {today} | Project created from handover |
"""
        project_file.write_text(project_content, encoding="utf-8")
        os.chmod(project_file, 0o664)

    return {
        "success": True,
        "handover_completed": str(dest),
        "project_created": str(project_file),
        "message": f"✅ Handover completed. Project created at {project_file}.",
    }


def main():
    parser = argparse.ArgumentParser(description="Process a handover")
    parser.add_argument("slug", help="Deal slug or handover filename")
    parser.add_argument("--review", action="store_true", help="Review handover details")
    parser.add_argument("--gate", type=int, default=None, help="Progress to gate number")
    parser.add_argument("--complete", action="store_true", help="Complete handover (move to completed, create project)")

    args = parser.parse_args()

    if not any([args.review, args.gate is not None, args.complete]):
        parser.print_help()
        sys.exit(1)

    filepath = find_handover(args.slug)
    if not filepath:
        print(f"❌ Handover not found: {args.slug}", file=sys.stderr)
        print(f"   Looked in: {PENDING_DIR} and {COMPLETED_DIR}", file=sys.stderr)
        sys.exit(1)

    if args.review:
        result = review_handover(filepath)
        print(json.dumps(result, indent=2))
        print(f"\n{'='*60}")
        print(f"📋 Handover Review: {result['customer']}")
        print(f"{'='*60}")
        print(f"  Status:     {result['status']}")
        print(f"  Gate:       {result['current_gate']}/{len(GATES)} ({result['gate_status']})")
        print(f"  Deal:       {result['deal']}")
        print(f"  Created:    {result['created']}")
        print(f"  File:       {result['handover_file']}")
        print(f"\n  Gates:")
        for g in result['gates']:
            icon = "✅" if g['status'] == 'done' else ("🔴" if g['status'] == 'gated' else "⏳")
            print(f"    {icon} {g['key']}: {g['name']} ({g['status']})")

    elif args.gate is not None:
        result = progress_gate(filepath, args.gate)
        if result["success"]:
            print(result["message"])
        else:
            print(f"❌ {result['error']}", file=sys.stderr)
            sys.exit(1)

    elif args.complete:
        result = complete_handover(filepath)
        print(result["message"])
        if result.get("project_created"):
            print(f"  📁 Project: {result['project_created']}")


if __name__ == "__main__":
    main()