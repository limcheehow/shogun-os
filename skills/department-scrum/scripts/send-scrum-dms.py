#!/usr/bin/env python3
"""
send-scrum-dms.py — Generic cross-department scrum DM sender.

Usage:
  python3 send-scrum-dms.py --profile project-manager
  python3 send-scrum-dms.py --profile hr-manager
  python3 send-scrum-dms.py --profile product-manager

Reads ~/.hermes/profiles/<profile>/scrum.yaml for team roster and config.
Sends DM to each team member with the 4 standard scrum questions.
Saves state to ~/.hermes/scrum-states/<profile>/{date}.json.
Logs to gbrain at _scrum/<profile>/{date}.
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

# ── Paths ──────────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
GBRAIN = os.path.expanduser("~/.local/bin/gbrain")

# ── Arg parsing ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Send scrum DMs to a department team")
parser.add_argument("--profile", required=True, help="Profile name (e.g. project-manager)")
args = parser.parse_args()

PROFILE = args.profile
PROFILE_DIR = HERMES_HOME / "profiles" / PROFILE
CONFIG_PATH = PROFILE_DIR / "scrum.yaml"

if not CONFIG_PATH.exists():
    print(f"ERROR: Config not found at {CONFIG_PATH}")
    print(f"  Create it with the department-scrum schema: see skill references.")
    sys.exit(1)

# ── Load config ────────────────────────────────────────────────────────
config = yaml.safe_load(CONFIG_PATH.read_text())

app_name = config.get("app_name", PROFILE)
channel_updates = config.get("channel_updates", "")
team = config.get("team", [])
brain_source = config.get("brain", {}).get("source", PROFILE)
comm_provider = config.get("comm_provider", "slack")

if not team:
    print(f"ERROR: No team defined in {CONFIG_PATH}")
    sys.exit(1)

# ── Load comm provider ──────────────────────────────────────────────────
os.environ.setdefault("HERMES_PROFILE", PROFILE)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from comm.provider import get_provider

provider = get_provider(comm_provider)

# ── Date & questions ───────────────────────────────────────────────────
TODAY = date.today()
DATE_STR = TODAY.isoformat()
DAY_NAME = TODAY.strftime("%A")

# Domain-specific question wording from config (or default)
domain_terms = config.get("brain", {}).get("domain_terms", [])
domain_hint = domain_terms[0] if domain_terms else "tasks"

QUESTIONS = (
    f"Good morning! Here's your {DAY_NAME} {DATE_STR} {app_name} scrum:\n\n"
    f"1. What {domain_hint} did you complete yesterday?\n"
    f"2. What {domain_hint} are you working on today?\n"
    f"3. Any blockers? (client delays, dependencies, approvals, etc.)\n"
    f"4. Do you need help from anyone?\n\n"
    f"Reply in this thread with your update!"
)

# ── State dir ──────────────────────────────────────────────────────────
state_dir_raw = config.get("state_dir", f"~/.hermes/scrum-states/{PROFILE}")
state_dir = Path(os.path.expanduser(state_dir_raw))
state_dir.mkdir(parents=True, exist_ok=True)
state_file = state_dir / f"{DATE_STR}.json"

# ── Send DMs ───────────────────────────────────────────────────────────
results = []
errors = []

print(f"=== Scrum Send: {PROFILE} — {DATE_STR}")
print(f" Team size: {len(team)}")
print()

for member in team:
    name = member["name"]
    user_id = member.get("user_id", member.get("slack_id", ""))
    role = member.get("role", "")
    try:
        result = provider.send_dm(user_id, QUESTIONS)
        results.append({
            "name": name,
            "user_id": user_id,
            "role": role,
            "thread_id": result["thread_id"],
            "conversation_id": result["conversation_id"],
            "replied": False,
            "reply_text": None,
            "replied_at": None,
            "compliance": "missed",
            "confidence": None,
            "issues": [],
            "tasks_matched": [],
            "brain_missing": [],
            "warned_11am": False,
        })
        print(f"  [OK] {name:25s} ({role:22s}) -> DM sent")
    except Exception as e:
        errors.append({"name": name, "user_id": user_id, "error": str(e)})
        print(f"  [ERR] {name:25s}: {e}")

# ── Save state ─────────────────────────────────────────────────────────
state = {
    "date": DATE_STR,
    "profile": PROFILE,
    "app_name": app_name,
    "channel_updates": channel_updates,
    "brain_source": brain_source,
    "questions_sent_at": datetime.now(timezone.utc).isoformat(),
    "team": results,
    "errors": errors,
}
state_file.write_text(json.dumps(state, indent=2, default=str))
print(f"\nState saved to {state_file}")

# ── Build summary (stdout → cron delivery) ──────────────────────────────
by_role = defaultdict(list)
for r in results:
    by_role[r["role"]].append(r["name"])

summary = [
    f"📋 *{app_name} Scrum — {DATE_STR}*",
    "",
    f"Questions sent to *{len(results)}* team members.",
    "",
    "*Team by role:*",
]
for role_name in sorted(by_role.keys()):
    names = by_role[role_name]
    summary.append(f"  • *{role_name}* ({len(names)}): {', '.join(names)}")

if errors:
    summary.append("")
    summary.append("⚠️ *Errors:*")
    for e in errors:
        summary.append(f"  • {e['name']}: {e['error']}")

summary.append("")
summary.append("_⏰ 11am reminder for non-responders. Real-time submissions via Slack DM. Full report at 5pm._")

print("\n" + "\n".join(summary))

# ── Log to gbrain ─────────────────────────────────────────────────────
gbrain_slug = f"_scrum/{PROFILE}/{DATE_STR}"
try:
    gbrain_lines = [
        "---",
        f"type: scrum-send",
        f"title: \"{app_name} Scrum — {DATE_STR}\"",
        f"date: {DATE_STR}",
        f"profile: {PROFILE}",
        f"team_size: {len(results)}",
        f"responded: 0",
        "---",
        "",
        f"# {app_name} Scrum - {DATE_STR}",
        "",
        f"Questions sent to {len(results)} team members.",
        "",
        "## By Role",
        "",
    ]
    for role_name in sorted(by_role.keys()):
        names = by_role[role_name]
        gbrain_lines.append(f"- **{role_name}** ({len(names)}): {', '.join(names)}")
    gbrain_lines.append("")
    if errors:
        gbrain_lines.append("## Errors")
        for e in errors:
            gbrain_lines.append(f"- {e['name']}: {e['error']}")
        gbrain_lines.append("")

    proc = subprocess.run(
        [GBRAIN, "put", gbrain_slug],
        input="\n".join(gbrain_lines),
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode == 0:
        print(f"\nLogged to gbrain {gbrain_slug}")
    else:
        print(f"\ngbrain error: {proc.stderr.strip()}")
except Exception as e:
    print(f"\ngbrain exception: {e}")

print("\nDone!")