#!/usr/bin/env python3
"""
check-scrum-replies.py — Generic cross-department scrum reply checker.

Usage:
  # 11am: check replies, warn non-responders
  python3 check-scrum-replies.py warn --profile project-manager

  # 5pm: full compliance report + brain cross-ref + gbrain log
  python3 check-scrum-replies.py report --profile project-manager

Reads ~/.hermes/profiles/<profile>/scrum.yaml for team roster and brain cross-ref rules.
Loads state from ~/.hermes/scrum-states/<profile>/{date}.json.
"""

import argparse
import json
import os
import re
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
NOW_UTC = datetime.now(timezone.utc)

# ── Arg parsing ────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Check scrum replies, warn or report")
parser.add_argument("mode", choices=["warn", "report"], help="warn (11am) or report (5pm)")
parser.add_argument("--profile", required=True, help="Profile name (e.g. project-manager)")
args = parser.parse_args()

PROFILE = args.profile
MODE = args.mode
PROFILE_DIR = HERMES_HOME / "profiles" / PROFILE
CONFIG_PATH = PROFILE_DIR / "scrum.yaml"

if not CONFIG_PATH.exists():
    print(f"ERROR: Config not found at {CONFIG_PATH}")
    sys.exit(1)

# ── Load config ────────────────────────────────────────────────────────
config = yaml.safe_load(CONFIG_PATH.read_text())

app_name = config.get("app_name", PROFILE)
channel_updates = config.get("channel_updates", "")
channel_leadership = config.get("channel_leadership", channel_updates)
brain_cfg = config.get("brain", {})
brain_source = brain_cfg.get("source", PROFILE)
task_id_patterns = brain_cfg.get("task_id_patterns", [])
domain_terms = brain_cfg.get("domain_terms", [])
custom_ref = brain_cfg.get("custom_ref", {})
project_dir = os.path.expanduser(custom_ref.get("project_dir", "")) if custom_ref else ""
ticket_index = os.path.expanduser(custom_ref.get("ticket_index", "")) if custom_ref else ""

# ── Slack token ────────────────────────────────────────────────────────
token = os.environ.get("SLACK_BOT_TOKEN")
if not token:
    env_path = PROFILE_DIR / ".env"
    if not env_path.exists():
        env_path = HERMES_HOME / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("SLACK_BOT_TOKEN=") and not line.startswith("#"):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not token:
    print("ERROR: SLACK_BOT_TOKEN not found")
    sys.exit(1)

from slack_sdk import WebClient
client = WebClient(token=token)

# ── Date & state ────────────────────────────────────────────────────────
TODAY = date.today()
DATE_STR = TODAY.isoformat()
state_dir_raw = config.get("state_dir", f"~/.hermes/scrum-states/{PROFILE}")
state_dir = Path(os.path.expanduser(state_dir_raw))
state_file = state_dir / f"{DATE_STR}.json"

if not state_file.exists():
    print(f"ERROR: No state file at {state_file}")
    print(f"  Has 9am send been run today?")
    sys.exit(1)

state = json.loads(state_file.read_text())
team = state.get("team", [])

# ── Helper: extract mentioned items from text ──────────────────────────

def extract_task_ids(text, patterns):
    """Extract all matching task IDs from text given a list of pattern dicts."""
    matches = []
    for pdef in patterns:
        pattern = pdef["pattern"]
        label = pdef.get("label", "Task")
        found = set(re.findall(pattern, text))
        for f in found:
            if isinstance(f, tuple):
                f = "".join(f)
            matches.append({"id": f, "label": label, "pattern_idx": patterns.index(pdef)})
    return matches


def extract_domain_terms(text, terms):
    """Extract domain terms found in text (case-insensitive)."""
    lower_text = text.lower()
    found = []
    for term in terms:
        if term.lower() in lower_text:
            found.append(term)
    return found


def cross_ref_task(tid, label, brain_source):
    """Check if a task ID exists in gbrain. Returns True/False."""
    try:
        # Try gbrain search by slug or keyword
        proc = subprocess.run(
            [GBRAIN, "query", "--source", brain_source, tid],
            capture_output=True, text=True, timeout=10,
        )
        return proc.returncode == 0 and len(proc.stdout.strip()) > 0
    except Exception:
        return False


def check_project_file(name, project_dir):
    """Check if a project file exists in active_projects/."""
    if not project_dir:
        return None
    pdir = Path(project_dir)
    if not pdir.exists():
        return None
    for f in pdir.iterdir():
        if name.lower() in f.stem.lower():
            return f.name
    return None


def check_ticket_index(tid, ticket_index):
    """Check if a ticket ID exists in the INDEX.md."""
    if not ticket_index or not os.path.exists(ticket_index):
        return None
    try:
        content = Path(ticket_index).read_text()
        if tid in content:
            return True
    except Exception:
        pass
    return None


def assess_quality(text, domain_terms):
    """SMART-adapted quality assessment. Returns (confidence, issues)."""
    issues = []
    text_lower = text.lower().strip()

    if len(text_lower) < 20:
        issues.append("too_short")

    if any(phrase in text_lower for phrase in ["no update", "same as before", "nothing new"]):
        issues.append("question_not_update")
    if text_lower.strip() in ("none", "n/a", "na", "no", "nothing", "same"):
        issues.append("question_not_update")

    found_terms = extract_domain_terms(text, domain_terms)
    if not found_terms:
        issues.append("no_project_match")

    # Check for blocker keyword density
    blocker_indicators = ["blocker", "blocked", "stuck", "delay", "waiting", "pending", "issue", "problem"]
    blocker_count = sum(1 for w in blocker_indicators if w in text_lower)

    if blocker_count >= 2:
        confidence = "medium"
    elif found_terms and len(text_lower) >= 40:
        confidence = "high"
    elif found_terms:
        confidence = "medium"
    else:
        confidence = "low"
        if "no_project_match" not in issues:
            issues.append("no_project_match")

    compliant = confidence in ("high", "medium") and "question_not_update" not in issues

    return confidence, issues, compliant, found_terms


def post_to_slack(channel, text, thread_ts=None):
    """Post a message to Slack channel."""
    try:
        kwargs = {"channel": channel, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        resp = client.chat_postMessage(**kwargs)
        return resp.get("ts")
    except Exception as e:
        print(f"  [ERR] Slack post failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════

print(f"=== Scrum {MODE.upper()}: {PROFILE} — {DATE_STR}")

# ── Check for new replies ──────────────────────────────────────────────
new_replies = 0
for member in team:
    if member.get("replied"):
        continue
    slack_id = member["slack_id"]
    dm_channel = member.get("dm_channel")
    question_ts = member.get("question_ts")
    if not dm_channel or not question_ts:
        continue
    try:
        replies = client.conversations_replies(channel=dm_channel, ts=question_ts, limit=5)
        messages = replies.get("messages", [])
        bot_reply_count = 0
        for msg in messages:
            if msg.get("ts") == question_ts:
                continue  # skip the bot's own question
            user = msg.get("user", "")
            if user == slack_id:
                reply_text = msg.get("text", "")
                member["reply_text"] = reply_text
                member["replied_at"] = msg["ts"]
                member["replied"] = True
                new_replies += 1

                # Quality assessment
                confidence, issues, compliant, found_terms = assess_quality(reply_text, domain_terms)
                member["confidence"] = confidence
                member["issues"] = issues
                member["compliant"] = compliant
                member["domain_terms_matched"] = found_terms

                # Extract task IDs
                task_matches = extract_task_ids(reply_text, task_id_patterns)
                member["tasks_matched_raw"] = [m["id"] for m in task_matches]

                # Brain cross-ref task IDs
                brain_missing = []
                for tm in task_matches:
                    exists = cross_ref_task(tm["id"], tm["label"], brain_source)
                    if not exists:
                        brain_missing.append(tm["id"])
                member["tasks_matched"] = [m["id"] for m in task_matches if m["id"] not in brain_missing]
                member["brain_missing"] = brain_missing

                # Cross-ref domain terms against project files
                project_dirs_found = []
                for term in found_terms:
                    pf = check_project_file(term, project_dir)
                    if pf:
                        project_dirs_found.append({"term": term, "file": pf})
                member["projects_found"] = project_dirs_found

                # Cross-ref ticket IDs against INDEX
                ticket_checks = []
                for tm in task_matches:
                    if "Ticket" in tm["label"] or "ticket" in tm["label"]:
                        tc = check_ticket_index(tm["id"], ticket_index)
                        ticket_checks.append({"id": tm["id"], "found_in_index": tc is not None if tc is not None else None})
                member["ticket_checks"] = ticket_checks

                # Set compliance status
                if compliant:
                    member["compliance"] = "on_time"
                else:
                    member["compliance"] = "late"
                bot_reply_count += 1
    except Exception as e:
        print(f"  [ERR] Checking replies for {member['name']}: {e}")

# ── Save updated state ─────────────────────────────────────────────────
state["team"] = team
state["last_checked_at"] = NOW_UTC.isoformat()
state_file.write_text(json.dumps(state, indent=2, default=str))
print(f" State updated: {new_replies} new replies, {sum(1 for m in team if m.get('replied'))} total")

# ── Compile stats ──────────────────────────────────────────────────────
total = len(team)
replied = [m for m in team if m.get("replied")]
not_replied = [m for m in team if not m.get("replied")]
on_time = [m for m in replied if m.get("compliance") == "on_time"]
late = [m for m in replied if m.get("compliance") == "late"]
all_tasks_matched = []
all_brain_missing = []
for m in replied:
    all_tasks_matched.extend(m.get("tasks_matched", []))
    all_brain_missing.extend(m.get("brain_missing", []))

compliance_pct = round((len(on_time) / total * 100)) if total else 0

# ═══════════════════════════════════════════════════════════════════════
#  WARN MODE (11am)
# ═══════════════════════════════════════════════════════════════════════
if MODE == "warn":
    warnings_sent = 0
    for member in not_replied:
        if member.get("warned_11am"):
            continue
        try:
            dm_channel = member.get("dm_channel")
            if dm_channel:
                warn_msg = (
                    f"⏰ Friendly reminder — your {app_name} scrum update hasn't been submitted yet today.\n\n"
                    f"Please reply to this morning's thread with:\n"
                    f"1. What you completed yesterday\n"
                    f"2. What you're working on today\n"
                    f"3. Any blockers\n"
                    f"4. Help needed"
                )
                client.chat_postMessage(channel=dm_channel, text=warn_msg)
                member["warned_11am"] = True
                warnings_sent += 1
                print(f"  [WARN] {member['name']:25s} -> warned")
        except Exception as e:
            print(f"  [ERR] Warning {member['name']}: {e}")

    # Save again after warnings
    state["team"] = team
    state_file.write_text(json.dumps(state, indent=2, default=str))

    # Summary
    print(f"\n📊 *{app_name} Scrum — 11am Check*")
    print(f" Members: {total} total")
    print(f" Replied: {len(replied)} | Non-responders: {len(not_replied)}")
    print(f" Warnings sent: {warnings_sent}")
    if all_tasks_matched:
        print(f" Tasks matched: {len(set(all_tasks_matched))}")
    if all_brain_missing:
        print(f" Brain missing: {len(set(all_brain_missing))} — {', '.join(set(all_brain_missing))}")

    # Post to channel_updates
    summary_text = (
        f"📋 *{app_name} Scrum — 11am Check*\n"
        f"• {len(replied)}/{total} submitted\n"
        f"• {len(not_replied)} still pending — warned via DM\n"
    )
    if all_tasks_matched:
        summary_text += f"• {len(set(all_tasks_matched))} tasks matched in brain\n"
    if all_brain_missing:
        summary_text += f"• ⚠️ {len(set(all_brain_missing))} IDs not in brain: {', '.join(set(all_brain_missing)[:5])}\n"

    if channel_updates:
        post_to_slack(channel_updates, summary_text)
        print(f" Posted to channel {channel_updates}")


# ═══════════════════════════════════════════════════════════════════════
#  REPORT MODE (5pm)
# ═══════════════════════════════════════════════════════════════════════
elif MODE == "report":
    # One last check for late replies
    late_replies_found = 0
    for member in not_replied:
        dm_channel = member.get("dm_channel")
        question_ts = member.get("question_ts")
        if not dm_channel or not question_ts:
            continue
        try:
            replies = client.conversations_replies(channel=dm_channel, ts=question_ts, limit=5)
            for msg in replies.get("messages", []):
                if msg.get("ts") == question_ts:
                    continue
                if msg.get("user") == member["slack_id"]:
                    reply_text = msg.get("text", "")
                    member["reply_text"] = reply_text
                    member["replied_at"] = msg["ts"]
                    member["replied"] = True
                    late_replies_found += 1

                    confidence, issues, compliant, found_terms = assess_quality(reply_text, domain_terms)
                    member["confidence"] = confidence
                    member["issues"] = issues
                    member["compliant"] = compliant
                    member["domain_terms_matched"] = found_terms

                    task_matches = extract_task_ids(reply_text, task_id_patterns)
                    brain_missing = []
                    for tm in task_matches:
                        exists = cross_ref_task(tm["id"], tm["label"], brain_source)
                        if not exists:
                            brain_missing.append(tm["id"])
                    member["tasks_matched"] = [m["id"] for m in task_matches if m["id"] not in brain_missing]
                    member["brain_missing"] = brain_missing
                    member["compliance"] = "on_time" if compliant else "late"
        except Exception as e:
            print(f"  [ERR] Late check {member['name']}: {e}")

    # Recompute stats
    replied = [m for m in team if m.get("replied")]
    not_replied = [m for m in team if not m.get("replied")]
    on_time = [m for m in replied if m.get("compliance") == "on_time"]
    late = [m for m in replied if m.get("compliance") == "late"]
    all_tasks_matched = []
    all_brain_missing = []
    for m in replied:
        all_tasks_matched.extend(m.get("tasks_matched", []))
        all_brain_missing.extend(m.get("brain_missing", []))
    compliance_pct = round((len(on_time) / total * 100)) if total else 0

    # Save final state
    state["team"] = team
    state["report_generated_at"] = NOW_UTC.isoformat()
    state_file.write_text(json.dumps(state, indent=2, default=str))

    # ── Per-member breakdown ──
    person_lines = []
    for m in team:
        name = m["name"]
        status = m.get("compliance", "missed")
        icon = {"on_time": "✅", "late": "⚠️", "missed": "❌"}.get(status, "❓")
        tasks = m.get("tasks_matched", [])
        missing = m.get("brain_missing", [])
        issues = m.get("issues", [])
        extra = []
        if tasks:
            extra.append(f"{len(tasks)} tasks")
        if missing:
            extra.append(f"{len(missing)} missing")
        if issues:
            extra.append(f"issues: {', '.join(issues)}")
        extra_str = f" ({', '.join(extra)})" if extra else ""
        person_lines.append(f"  {icon} {name:25s} | {status:8s}{extra_str}")

    # ── Print summary ──
    print(f"\n📊 *{app_name} Scrum — 5pm Report*")
    print(f" Date: {DATE_STR}")
    print(f" Total members: {total}")
    print(f" Submitted: {len(replied)}")
    print(f"   On time: {len(on_time)} ({compliance_pct}%)")
    print(f"   Late: {len(late)}")
    print(f" Missed: {len(not_replied)}")
    print(f" Late replies caught: {late_replies_found}")
    if all_tasks_matched:
        print(f" Tasks matched in brain: {len(set(all_tasks_matched))}")
    if all_brain_missing:
        print(f" ⚠️ Brain missing: {len(set(all_brain_missing))} — {', '.join(set(all_brain_missing))}")
    print()
    print("*Per-member breakdown:*")
    for line in person_lines:
        print(line)

    # ── Report to Slack ──
    lines = [
        f"📊 *{app_name} Scrum — EOD Report*",
        f"*{DATE_STR}*",
        "",
        f"**{len(replied)}/{total} submitted** — {compliance_pct}% compliance",
        f"  ✅ On time: {len(on_time)}",
        f"  ⚠️ Late: {len(late)}",
        f"  ❌ Missed: {len(not_replied)}",
    ]
    if all_tasks_matched:
        lines.append(f"  📎 Brain matched: {len(set(all_tasks_matched))} tasks")
    if all_brain_missing:
        lines.append(f"  ⚠️ Brain missing: {len(set(all_brain_missing))} IDs")
    lines.append("")
    lines.append("*Per-member:*")
    lines.extend(person_lines)

    report_text = "\n".join(lines)

    # Post to leadership channel (primary)
    target_channel = channel_leadership or channel_updates
    if target_channel:
        post_to_slack(target_channel, report_text)
        print(f"\n Posted report to {target_channel}")

    # Also post brief summary to updates channel
    if channel_updates and channel_updates != target_channel:
        brief = (
            f"📋 *{app_name} Scrum — 5pm Summary*\n"
            f"• {len(replied)}/{total} submitted ({compliance_pct}% compliance)\n"
            f"• {len(not_replied)} missed\n"
            f"• Detailed report posted to leadership channel"
        )
        post_to_slack(channel_updates, brief)

    # ── Log to gbrain ──
    gbrain_slug = f"_scrum/{PROFILE}/{DATE_STR}"
    try:
        gbrain_lines = [
            "---",
            f"type: scrum-report",
            f"title: \"{app_name} Scrum Report — {DATE_STR}\"",
            f"profile: {PROFILE}",
            f"date: {DATE_STR}",
            f"total: {total}",
            f"submitted: {len(replied)}",
            f"on_time: {len(on_time)}",
            f"late: {len(late)}",
            f"missed: {len(not_replied)}",
            f"compliance_pct: {compliance_pct}",
            f"tasks_matched: {len(set(all_tasks_matched))}",
            f"brain_missing: {len(set(all_brain_missing))}",
            "---",
            "",
            f"# {app_name} Scrum — {DATE_STR}",
            "",
            f"**{len(replied)}/{total} submitted** ({compliance_pct}% compliance)",
            "",
        ]
        gbrain_lines.append("## Per Member")
        for m in team:
            status = m.get("compliance", "missed")
            tasks = ", ".join(m.get("tasks_matched", [])) or "-"
            missing = ", ".join(m.get("brain_missing", [])) or "-"
            gbrain_lines.append(f"- **{m['name']}** ({status})")
            gbrain_lines.append(f"  - Tasks matched: {tasks}")
            gbrain_lines.append(f"  - Brain missing: {missing}")
        gbrain_lines.append("")

        proc = subprocess.run(
            [GBRAIN, "put", gbrain_slug],
            input="\n".join(gbrain_lines),
            capture_output=True, text=True, timeout=15,
        )
        if proc.returncode == 0:
            print(f" Logged to gbrain {gbrain_slug}")
        else:
            print(f" gbrain error: {proc.stderr.strip()}")
    except Exception as e:
        print(f" gbrain exception: {e}")

# ── Final ──
print(f"\nDone! {MODE.upper()} — {PROFILE}")