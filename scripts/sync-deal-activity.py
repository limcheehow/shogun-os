#!/usr/bin/env python3
"""
sync-deal-activity.py — Bridge email activity into deal/project pages.

After email collection + classification, matches senders to person profiles
linked to deals or projects, adds timeline entries, detects risks, and creates tasks.

Configure via env vars:
  BRAIN_DIR — brain root directory (default: ~/brain)
  LOOKBACK_HOURS — how many hours of emails to scan (default: 3)
  STALL_DAYS — deal inactivity threshold (default: 7)
  COLD_DAYS — qualified deal inactivity threshold (default: 14)
  OVERDUE_DAYS — project past target threshold (default: 7)
  OWNER_SLACK_MAP — path to JSON file mapping owner names to Slack IDs
  INTERNAL_EMAIL_DOMAINS — comma-separated list of internal domains to skip

Usage:
    python3 sync-deal-activity.py --dry-run
    python3 sync-deal-activity.py
    python3 sync-deal-activity.py --dm
"""
import json, os, re, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

BRAIN = Path(os.environ.get("BRAIN_DIR", str(Path.home() / "brain")))
PERSONS = BRAIN / "persons"
DEALS = BRAIN / "deals"
PROJECTS = BRAIN / "projects" / "active_projects"
EMAIL_DIR = BRAIN / "data" / "email"
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "3"))
STALL_DAYS = int(os.environ.get("STALL_DAYS", "7"))
COLD_DAYS = int(os.environ.get("COLD_DAYS", "14"))
OVERDUE_DAYS = int(os.environ.get("OVERDUE_DAYS", "7"))

# Internal domains — emails from these addresses are skipped
_raw_internal = os.environ.get("INTERNAL_EMAIL_DOMAINS", "example.com")
INTERNAL_DOMAINS = set(d.strip().lower() for d in _raw_internal.split(",") if d.strip())

# Owner → Slack ID mapping (loaded from JSON file)
OWNER_SLACK_MAP_PATH = os.environ.get("OWNER_SLACK_MAP", "")
OWNER_SLACK = {}
if OWNER_SLACK_MAP_PATH and os.path.exists(OWNER_SLACK_MAP_PATH):
    with open(OWNER_SLACK_MAP_PATH) as f:
        OWNER_SLACK = json.load(f)


def parse_frontmatter(text: str) -> dict:
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


def extract_sender_email(filepath: Path) -> str | None:
    try:
        text = filepath.read_text()
    except Exception:
        return None
    fm = parse_frontmatter(text)
    email = fm.get("from", "")
    m = re.search(r'<([^>]+)>', email)
    if m:
        return m.group(1).lower()
    return email.lower() if "@" in email else None


def find_person_by_email(email: str) -> Path | None:
    email_lower = email.lower()
    for pfile in PERSONS.glob("*.md"):
        try:
            content = pfile.read_text()
        except Exception:
            continue
        fm = parse_frontmatter(content)
        if fm.get("email", "").lower() == email_lower:
            return pfile
    return None


def find_deals_linked_to_person(person_slug: str) -> list[Path]:
    linked = []
    slug_ref = f"persons/{person_slug}"
    for dfile in DEALS.glob("*.md"):
        if dfile.name.startswith("_"):
            continue
        try:
            content = dfile.read_text()
        except Exception:
            continue
        if slug_ref in content or f"[[{slug_ref}]]" in content:
            linked.append(dfile)
    return linked


def find_projects_linked_to_person(person_slug: str) -> list[Path]:
    linked = []
    for pfile in PROJECTS.glob("*.md"):
        try:
            content = pfile.read_text()
        except Exception:
            continue
        fm = parse_frontmatter(content)
        owner = fm.get("owner", "")
        if person_slug in content.lower() or owner.lower().replace(" ", "") in person_slug:
            linked.append(pfile)
    return linked


def extract_deal_stage(content: str) -> str:
    fm = parse_frontmatter(content)
    return fm.get("stage", "Unknown")


def extract_deal_owner(content: str) -> str:
    fm = parse_frontmatter(content)
    return fm.get("owner", "")


def extract_last_activity_date(content: str) -> str | None:
    dates = re.findall(r'-\s*(\d{4}-\d{2}-\d{2})\s*\|', content)
    if dates:
        return max(dates)
    tl = re.search(r'## Timeline\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if tl:
        dates = re.findall(r'(\d{4}-\d{2}-\d{2})', tl.group(1))
        if dates:
            return max(dates)
    return None


def extract_project_status(content: str) -> str:
    m = re.search(r'\*\*Status\*\*\s*\|?\s*(.*?)(?:\||$)', content)
    return m.group(1).strip() if m else "Unknown"


def extract_project_target_date(content: str) -> str | None:
    m = re.search(r'\*\*Target Date\*\*\s*\|?\s*(.*?)(?:\||$)', content)
    if m:
        val = m.group(1).strip()
        if val and val != "—":
            return val
    return None


def extract_project_owner(content: str) -> str:
    m = re.search(r'\*\*Owner\*\*\s*\|?\s*(.*?)(?:\||$)', content)
    return m.group(1).strip() if m else ""


def detect_risks(page_type: str, content: str, page_path: Path) -> list[dict]:
    risks = []
    today = datetime.now(timezone.utc).date()

    if page_type == "deal":
        stage = extract_deal_stage(content)
        last_act = extract_last_activity_date(content)

        if last_act:
            last_date = datetime.strptime(last_act, "%Y-%m-%d").date()
            days_since = (today - last_date).days
            if days_since > STALL_DAYS:
                risks.append({"level": "🟡", "reason": f"No activity for {days_since}d (last: {last_act})",
                              "suggestion": "Send follow-up or schedule check-in"})
            if stage in ("Qualified", "Prospecting") and days_since > COLD_DAYS:
                risks.append({"level": "🔴", "reason": f"Deal cold — {stage} silent {days_since}d",
                              "suggestion": "Re-engage or move to On Hold / Closed Lost"})
        if stage == "On Hold":
            risks.append({"level": "🟡", "reason": "Deal is On Hold — needs unblocking decision",
                          "suggestion": "Review hold reason and decide next step"})

    elif page_type == "project":
        status = extract_project_status(content)
        target = extract_project_target_date(content)
        if target:
            try:
                target_date = datetime.strptime(target, "%Y-%m-%d").date()
                if target_date < today and status not in ("Completed", "✅ Completed"):
                    days_overdue = (today - target_date).days
                    risks.append({"level": "🔴", "reason": f"Target {target} — {days_overdue}d overdue",
                                  "suggestion": "Update target date or escalate blockers"})
            except ValueError:
                pass
        if not target:
            risks.append({"level": "⚪", "reason": "No target date set",
                          "suggestion": "Set a target completion date"})

    return risks


def slack_dm_owner(owner_name: str, page_name: str, risks: list[dict], page_type: str) -> str | None:
    slack_id = OWNER_SLACK.get(owner_name)
    if not slack_id:
        for key, val in OWNER_SLACK.items():
            if owner_name.lower() in key.lower() or key.lower() in owner_name.lower():
                slack_id = val
                break
    if not slack_id:
        return None

    emoji = "🔴" if any(r["level"] == "🔴" for r in risks) else "🟡"
    risk_lines = "\n".join(f"  {r['level']} {r['reason']}" for r in risks)
    return f"{emoji} *Deal/Project Activity Alert*\n\n*{page_name}* ({page_type})\nRisks detected:\n{risk_lines}\n\n_Auto-flagged by sync-deal-activity_"


def main(dry_run: bool = False, dm_owners: bool = False):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    recent_emails = [f for f in EMAIL_DIR.glob("*.md")
                     if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) > cutoff]

    if not recent_emails:
        print("No recent emails to process.")
        return []

    print(f"Processing {len(recent_emails)} recent email(s)...")

    person_deals = defaultdict(set)
    person_projects = defaultdict(set)
    person_emails = defaultdict(list)

    for email_file in recent_emails:
        sender_email = extract_sender_email(email_file)
        if not sender_email:
            continue
        sender_domain = sender_email.split("@")[-1] if "@" in sender_email else ""
        if sender_domain in INTERNAL_DOMAINS:
            continue

        person_path = find_person_by_email(sender_email)
        if not person_path:
            continue

        person_slug = person_path.stem
        deals = find_deals_linked_to_person(person_slug)
        projects = find_projects_linked_to_person(person_slug)

        if not deals and not projects:
            continue

        for d in deals:
            person_deals[person_slug].add(d)
        for p in projects:
            person_projects[person_slug].add(p)

        try:
            content = email_file.read_text()
        except Exception:
            continue
        fm = parse_frontmatter(content)
        person_emails[person_slug].append({
            "subject": fm.get("title", email_file.stem[:60]),
            "from": fm.get("from", sender_email),
            "date": fm.get("date", datetime.now().strftime("%Y-%m-%d")),
        })

    for person_slug, deals in person_deals.items():
        for deal_path in deals:
            try:
                content = deal_path.read_text()
            except Exception:
                continue

            timeline_entries = []
            for em in person_emails.get(person_slug, []):
                entry = f"- {em['date']} | Email from {em['from']}: {em['subject'][:80]}. [Source: email]"
                timeline_entries.append(entry)

            new_content = content
            if "## Timeline" in content:
                timeline_end = content.find("\n## ", content.index("## Timeline") + 1)
                if timeline_end == -1:
                    timeline_end = len(content)
                new_entries = [e for e in timeline_entries if e not in content[content.index("## Timeline"):timeline_end]]
                if new_entries:
                    new_content = content[:timeline_end] + "\n" + "\n".join(new_entries) + content[timeline_end:]
            else:
                new_content = content.rstrip() + "\n\n## Timeline\n" + "\n".join(timeline_entries) + "\n"

            risks = detect_risks("deal", content, deal_path)
            if risks:
                for risk in risks:
                    if risk["level"] in ("🔴", "🟡"):
                        task = f"- [ ] {risk['reason']} — {risk['suggestion']} (auto-flagged {datetime.now().strftime('%Y-%m-%d')})"
                        if "## Tasks" not in new_content:
                            new_content += "\n## Tasks\n" + task + "\n"
                        elif task not in new_content:
                            tasks_start = new_content.find("## Tasks")
                            insert_pos = new_content.find("\n", tasks_start) + 1
                            new_content = new_content[:insert_pos] + task + "\n" + new_content[insert_pos:]

            if new_content != content:
                if dry_run:
                    print(f"  [DRY RUN] Would update {deal_path.name}")
                else:
                    deal_path.write_text(new_content)
                    print(f"  ✅ Updated {deal_path.name}")

            if dm_owners and risks:
                owner = extract_deal_owner(content)
                if owner:
                    msg = slack_dm_owner(owner, deal_path.stem.replace("-", " ").title(), risks, "deal")
                    if msg and OWNER_SLACK.get(owner):
                        print(f"  📨 DM to {owner}: {risks[0]['reason']}")

    all_deals = set().union(*person_deals.values()) if person_deals else set()
    all_proj = set().union(*person_projects.values()) if person_projects else set()
    print(f"\n📊 Summary: {len(recent_emails)} emails → {len(person_deals)} contacts → {len(all_deals)} deals, {len(all_proj)} projects")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    dm = "--dm" in sys.argv
    main(dry_run=dry, dm_owners=dm)