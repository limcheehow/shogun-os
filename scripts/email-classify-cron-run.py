#!/usr/bin/env python3
"""
Email Classification Pipeline — classifies new email batches into categories.
Tags via gbrain CLI, cross-links project/deal emails, sends high-risk alerts.

Configure via env vars:
  BRAIN_EMAIL_DIR    — path to email markdown files (default: ~/brain/data/email)
  GMAIL_USER         — the Gmail user being polled (for context)
  HERMES_SCRIPTS_DIR — path to Hermes scripts (for DM dispatch)
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

BRAIN_EMAIL_DIR = os.environ.get(
    "BRAIN_EMAIL_DIR",
    str(Path.home() / "brain/data/email")
)
GBRAIN_BIN = os.environ.get("GBRAIN_BIN", os.path.expanduser("~/.local/bin/gbrain"))
HERMES_SCRIPTS_DIR = os.environ.get(
    "HERMES_SCRIPTS_DIR",
    os.path.expanduser("~/.hermes/scripts")
)


def gbrain_tag(slug, tag):
    r = subprocess.run([GBRAIN_BIN, "tag", slug, tag], capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        print(f"  ⚠ tag '{tag}' failed: {r.stderr.strip()[:100]}")
    return r


def classify_email(filename, content):
    """Classify an email based on its frontmatter + subject.
    Returns (category, risk_level, risk_signal, slug, source_user, title)."""
    fm = {}
    in_fm = False
    fm_lines = []
    for line in content.split('\n'):
        if line.strip() == '---':
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm:
            fm_lines.append(line)

    for line in fm_lines:
        if ':' in line:
            key, val = line.split(':', 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")

    title = fm.get('title', '')
    from_addr = fm.get('from', '')
    to_addr = fm.get('to', '')
    source_user = fm.get('source_user', '')
    labels = fm.get('labels', '')
    slug = filename.replace('.md', '')
    risk_level = "low"
    risk_signal = ""
    category = "other"

    title_lower = title.lower()
    content_lower = content.lower()

    # ── HIGH RISK SCAN ──
    high_risk_patterns = [
        (r'\boverdue\b', 'Deadline missed - overdue'),
        (r'past deadline', 'Deadline missed'),
        (r'\bdelayed\b', 'Delayed'),
        (r'behind schedule', 'Behind schedule'),
        (r'escalation', 'Customer escalation'),
        (r'not happy', 'Customer dissatisfaction'),
        (r'disappointed', 'Customer dissatisfaction'),
        (r'urgent attention', 'Urgent issue'),
        (r'cancellation', 'Cancellation/termination'),
        (r'termination', 'Service termination'),
        (r'refund', 'Refund demand'),
        (r'legal action', 'Legal threat'),
        (r'lawyer', 'Legal involvement'),
        (r'server down', 'System down'),
        (r'system offline', 'System outage'),
        (r'outage', 'System outage'),
        (r'data loss', 'Data loss'),
        (r'breach', 'Security breach'),
        (r'hacked', 'Security breach'),
        (r'unpaid invoice', 'Payment dispute'),
        (r'demand letter', 'Payment dispute'),
    ]

    for pattern, signal in high_risk_patterns:
        if re.search(pattern, content_lower):
            risk_level = "high"
            risk_signal = signal
            break

    if 'termination' in title_lower:
        risk_level = "high"
        risk_signal = "Service termination"

    # ── MEDIUM RISK SCAN ──
    if risk_level == "low":
        medium_patterns = [
            (r'out of scope', 'Scope creep'),
            (r'change request', 'Scope creep'),
            (r'short staffed', 'Resource strain'),
            (r'no available', 'Resource constraint'),
            (r'overbooked', 'Resource strain'),
            (r'over budget', 'Budget concern'),
            (r'cost overrun', 'Budget concern'),
            (r'supplier delayed', 'Vendor delay'),
            (r'parts not arriv', 'Vendor delay'),
            (r'customs hold', 'Vendor delay'),
        ]
        for pattern, signal in medium_patterns:
            if re.search(pattern, content_lower):
                risk_level = "medium"
                risk_signal = signal
                break

    # ── CLASSIFICATION via signal words ──
    deal_signals = [
        'quotation', 'quote', 'proposal', 'pricing', 'demo request', 'rfp', 'rfq',
        'contract', 'mou', 'nda', 'purchase order', 'invoice', 'payment terms',
        'bid', 'tender', 'renewal', 'upsell', 'poc', 'proof of concept',
        'sales enquiry', 'new opportunity', 'deal registration',
    ]
    project_signals = [
        'po#', 'site visit', 'installation', 'uat', 'milestone', 'deployment',
        'hardware delivery', 'server', 'configuration', 'kickoff', 'go-live',
        'snag list', 'defect', 'warranty claim', 'support ticket',
        'project', 'floor plan', 'confirmation required',
        'vendor appointment', 'daily report', 'installation report',
    ]
    support_signals = [
        'support ticket', 'not working', 'broken', 'down',
        'error', 'bug', 'help', 'urgent fix',
        'lagging', 'stuttering',
    ]
    hr_signals = [
        'interview', 'cv', 'resume', 'job application', 'recruitment',
        'candidate', 'offer letter', 'onboarding', 'careers', 'applicant',
        'internship',
    ]

    # Check for explicit label prefixes
    if title.startswith('[Project]') or '[Project]' in title:
        category = "project"
    elif title.startswith('[Support]') or '[Support]' in title:
        category = "support"
    elif title.startswith('[Sales Enquiry]'):
        category = "deal"
    elif title.startswith('[Careers]'):
        category = "hr"
    elif title.startswith('[Admin]') or title.startswith('[HR]'):
        if 'mou' in title_lower or 'sign' in title_lower:
            category = "deal"
        else:
            category = "other"
    else:
        deal_score = sum(1 for s in deal_signals if s in title_lower)
        project_score = sum(1 for s in project_signals if s in title_lower)
        support_score = sum(1 for s in support_signals if s in title_lower)
        hr_score = sum(1 for s in hr_signals if s in title_lower)

        scores = {'deal': deal_score, 'project': project_score, 'support': support_score, 'hr': hr_score}
        max_cat = max(scores, key=lambda k: scores[k])
        if scores[max_cat] > 0:
            category = max_cat

    return category, risk_level, risk_signal, slug, source_user, title


def process_batch():
    """Find recently modified email files and classify them."""
    # Find recently modified email files (last 120 minutes)
    result = subprocess.run(
        f"find {BRAIN_EMAIL_DIR} -name '*.md' -mmin -120 | sort",
        shell=True, capture_output=True, text=True, timeout=30
    )
    files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]

    print(f"Found {len(files)} recently modified email files")

    # Deduplicate: group by gmail_id (same email forwarded to multiple users)
    gmail_groups = {}
    results = []

    for fpath in files:
        content = open(fpath).read()
        cat, risk, signal, slug, user, title = classify_email(os.path.basename(fpath), content)

        # Extract gmail_id from frontmatter
        fm_gmail = None
        in_fm = False
        for line in content.split('\n'):
            if line.strip() == '---':
                if in_fm:
                    break
                in_fm = True
                continue
            if in_fm and 'gmail_id:' in line:
                fm_gmail = line.split(':', 1)[1].strip()

        key = f"{cat}:{fm_gmail or slug}"
        if key not in gmail_groups:
            gmail_groups[key] = []
        gmail_groups[key].append((fpath, cat, risk, signal, slug, user, title))
        results.append((fpath, cat, risk, signal, slug, user, title))

    counts = {'project': 0, 'deal': 0, 'support': 0, 'hr': 0, 'other': 0}
    high_risks = []

    # Process each unique email group
    for key, group in gmail_groups.items():
        fpath, cat, risk, signal, slug, user, title = group[0]
        all_users = [g[5] for g in group]
        counts[cat] += 1

        if cat != 'other':
            gbrain_tag(slug, "classified")
            gbrain_tag(slug, cat)
        else:
            gbrain_tag(slug, "classified")

        if risk == "high":
            high_risks.append((slug, cat, signal, title, all_users, user))

        user_str = ','.join(all_users)
        risk_str = f" ⚠ {risk.upper()}: {signal}" if risk != "low" else ""
        print(f"  [{cat.upper():7}] {title[:70]:70} ({user_str}){risk_str}")

    print(f"\n{'='*60}")
    print(f"CLASSIFICATION SUMMARY")
    print(f"{'='*60}")
    print(f"  project: {counts['project']} | deal: {counts['deal']} | support: {counts['support']} | hr: {counts['hr']} | other: {counts['other']}")
    print(f"  Total unique threads: {len(gmail_groups)}")

    # HIGH RISK alerts
    if high_risks:
        print(f"\n{'='*60}")
        print(f"HIGH RISK ALERTS")
        print(f"{'='*60}")

        for slug, cat, signal, title, users, primary_user in high_risks:
            msg = f"*⚠️ Urgent — {cat}*: {signal} — {title}"
            print(f"\n  🚨 {signal}: {title[:60]}")

            for u in users:
                if u:
                    dm_script = os.path.join(HERMES_SCRIPTS_DIR, "send-category-dm.py")
                    if os.path.exists(dm_script):
                        cmd = [sys.executable, dm_script, u, cat, msg]
                        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                        if r.returncode == 0:
                            print(f"     ✓ DM sent to {u}")
                        else:
                            print(f"     ✗ DM failed for {u}: {r.stderr.strip()[:100]}")
                    else:
                        print(f"     ⚠ DM script not found at {dm_script} — skipping DM")
    else:
        print(f"\n  ✅ No HIGH risk items found")

    # ── Orphan prevention: link each unique email slug to email index hub ──
    unique_slugs = list(set(r[4] for r in results))
    if unique_slugs:
        try:
            sys.path.insert(0, HERMES_SCRIPTS_DIR)
            from brain_compliance_helper import link_to_index
            for slug in unique_slugs:
                link_to_index(slug, "email")
            print(f"\n  🔗 Linked {len(unique_slugs)} emails to email index hub")
        except ImportError:
            print(f"\n  ⚠ brain_compliance_helper not found — skipping orphan prevention")

    return counts, high_risks, len(gmail_groups)


if __name__ == "__main__":
    counts, high_risks, total = process_batch()

    print(f"\n---MACHINE_SUMMARY---")
    print(json.dumps({
        "total_threads": total,
        "projects": counts['project'],
        "deals": counts['deal'],
        "support": counts['support'],
        "hr": counts['hr'],
        "other": counts['other'],
        "high_risk_count": len(high_risks),
        "high_risk_items": [{"slug": h[0], "cat": h[1], "signal": h[2]} for h in high_risks],
    }))